#Creating python script
"""
Required script actions

Connect to 2 PAMS (over IP) - can hardcode the IP addresses

User selects QIS or QPS


Start stream on both units at the same time

Stream for 60 seconds

Power on both units at the same time

Export both traces as a CSV
If QPS use stats_to_CSV()


Stage 2
Merge the CSVs
    Prefix the columns with 1_xxx, 2_xxx
    Single time column

QPS post process - speak to Graham

Don't need microsecond alignment, but sub millisecond
"""
import time
import os
import pandas as pd


import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

#Path where stream will be saved - defaults to the current script path
stream_path = os.path.dirname(os.path.realpath(__file__))


def main():
    #Hardcode the addresses in this instance
    pam_1_address = "USB:QTL2843-02-002"
    #PLACEHOLDER IP Address
    pam_2_address = "TCP:10.0.9.204"

    #User selectable whether connection is done via QIS or via QPS
    #connection_list = ["QIS", "QPS"]

    #String, with the value either QIS or QPS
    #connection_type = listSelection(title="Connection: QIS or QPS", selectionList=connection_list, nice=True)

    #QPS is not currently working - remove option to use QPS
    connection_type = "QIS"

    #Use single instance of QIS
    if connection_type == "QIS":
        #If QIS is not already running
        if not isQisRunning():
            #Start Local QIS Instance
            startLocalQis()

        #Connects to the localhost QIS instance
        QisInterface()

        #Connects 2 pam devices to the same QIS Instance
        pam_1_device = get_quarch_device(connectionTarget=pam_1_address, ConType=connection_type)
        #Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
        pam_1_power_device = quarchPPM(pam_1_device)

        pam_2_device = get_quarch_device(connectionTarget=pam_2_address, ConType=connection_type)
        pam_2_power_device = quarchPPM(pam_2_device)

        print(pam_1_device.send_command("*idn?"))
        print(pam_2_device.send_command("*idn?"))

        time.sleep(1)

        file_name_pam_1 = "RawDataPam1.csv"
        file_name_pam_2 = "RawDataPam2.csv"

        print("Stream Running for 60 seconds")

        pam_1_power_device.start_stream(file_name=file_name_pam_1, stream_duration=60)
        pam_2_power_device.start_stream(file_name=file_name_pam_2, stream_duration=60)


    #Else - connection type is QPS, open 2 instances of QPS with a separate QIS backend
    else:
        #First Instance - default ports, but left for clarity
        startLocalQis()
        my_qps_1 = startLocalQps()

        #Creates and returns a quarchDevice instance
        pam_1_device = get_quarch_device(connectionTarget=pam_1_address, ConType=connection_type)
        print(pam_1_device.send_command("*idn?"))

        pam_1_device.open_connection()

        #Second instance - Ports are incremented by 1
        startLocalQis(args=['-port=9723','restport=9781'])
        my_qps_2 = startLocalQps(args=['-port=9823','-qisport=9723','-qisrestport=9781'])

        #Creates and returns a quarchDevice instance
        pam_2_device = get_quarch_device(connectionTarget=pam_2_address, ConType=connection_type)
        print(pam_2_device.send_command("*idn?"))

        pam_2_device.open_connection()


    time.sleep(60)

    print("Stream completed")

    time.sleep(5)

    csv_combiner("RawDataPam1.csv", "RawDataPam2.csv")

    import_csv_to_qps(pam_1_power_device)
    pam_1_power_device.close_connection()
    pam_2_power_device.close_connection()

    return None

def csv_combiner(csv_file_1, csv_file_2):
    #The name of the file to be outputted
    combined_csv_name = "CombinedData.csv"

    #Uses pandas - a data analysis and manipulation tool
    csv1 = pd.read_csv(csv_file_1)
    csv2 = pd.read_csv(csv_file_2)

    #Column name of the time column - This will be the same in both CSVs, and should not be changed
    shared_time_column = "Time uS"

    #Unresolved attribute is not an issue - runs fine
    csv1_prefix = csv1.add_prefix("1_").rename(columns={"1_" + shared_time_column: shared_time_column})
    csv2_prefix = csv2.add_prefix("2_").rename(columns={"2_" + shared_time_column: shared_time_column})

    merged_data = pd.merge(csv1_prefix, csv2_prefix, on=shared_time_column, how="outer")

    merged_data.to_csv(combined_csv_name, index=False)

    print("CSVs have been combined")
    return "CombinedData.csv"

def import_csv_to_qps(pam_to_upgrade):
    #Close connection - reopen it

    startLocalQps()
    myQpsInterface = QpsInterface()



    myQpsInterface.sendCommand("$stream import file=C:/Users/asteedman/Documents/Github/Application-Notes/Application_Notes/AN-034_Multi_AC_PAM_Streaming/CombinedData.csv")

if __name__ == "__main__":
    main()
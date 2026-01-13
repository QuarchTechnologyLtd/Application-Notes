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
    connection_list = ["QIS", "QPS"]

    #String, with the value either QIS or QPS
    connection_type = listSelection(title="Connection: QIS or QPS", selectionList=connection_list, nice=True)

    #Use single instance of QIS
    if connection_type == "QIS":
        #If QIS is not already running
        if not isQisRunning():
            #Start Local QIS Instance
            startLocalQis()

        #Connects to the localhost QIS instance
        myQisInterface = QisInterface()

        #Connects 2 pam devices to the same QIS Instance
        pam_1_device = get_quarch_device(connectionTarget=pam_1_address, ConType=connection_type)
        #Upgrades PAM to quarchPower class
        pam_1_power_device = quarchPPM(pam_1_device)

        pam_2_device = get_quarch_device(connectionTarget=pam_2_address, ConType=connection_type)
        pam_2_power_device = quarchPPM(pam_2_device)

        print(pam_1_device.send_command("*idn?"))
        print(pam_2_device.send_command("*idn?"))

        time.sleep(1)

        file_name_pam_1 = "RawDataPam1.csv"
        file_name_pam_2 = "RawDataPam2.csv"

        print("Stream Running for 60 seconds")

        pam_1_power_device.start_stream(file_name=file_name_pam_1, stream_duration=60,release_on_data=False)
        pam_2_power_device.start_stream(file_name=file_name_pam_2, stream_duration=60,release_on_data=False)


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


    #quarchStream - save_csv

    return None

def csv_manipulation(csv_file):
    print("ToDO")

if __name__ == "__main__":
    main()
"""AN-034
This Application Note uses 2 AC Power Analysis Modules to stream synchronously, with the user choosing to stream
over QIS or over QPS. Either option will export a CSV, which is then merged, and opened in QPS.

The data recorded is from the same source, but due to the high power requirements, 2 AC PAMs are required. Recommended
TCP PoE connection rather than USB.

Both PAM data streams can be viewed side by side. Connecting to both PAMs via TCP has a current lag of approximately
63 milliseconds, between one trace starting recording and the second trace starting recording.

This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Post processing of CSV data
-Importing CSV data into QPS to display

########### VERSION HISTORY ###########
13/01/2026 - Andrew Steedman - Created

########### REQUIREMENTS ##############

1 - Python (3.x recommended)
    https://www.python.org/downloads/
2 - Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3 - tkinter (Used for GUI)
    https://docs.python.org/3/library/tkinter.html#
4 - Control PC, with firewall permissions and admin rights

########### INSTRUCTIONS ##############

1 - Connect AC PAMs to the same LAN as control PC
2 - Connect AC PAMs to load
3 - Change the global variables: pam_1_address, pam_2_address, stream_length
4 - Run the script

Lag was 60ms with IEC recording first, 85ms with 3P recording first.

#TODO
Reduce this lag - Either through broadcasting over IP to start recording at the same time, or via multithreading and raising flags
Quarchpy QPS API change - enable the scripting of multiple instances, with a separate QIS backend
Automate the CSV imports into QPS - Manual import works as expected
"""
import time
import os
import pandas as pd #CSV manipulation
from tkinter import Tk #Used as a GUI
from tkinter.filedialog import askopenfilename #Used to open the CSV to reopen

import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

#USER TO CHANGE
# Hardcoded PAM Addresses
pam_1_address = "TCP:10.0.9.146"
pam_2_address = "TCP:10.0.9.204"

#Stream length in seconds - QIS call takes float parameter
stream_length = float(60)
#/USER TO CHANGE/

def main():
    print("Starting script")

    #TO UNCOMMENT
    """
    #User selectable whether connection is done via QIS or via QPS
    connection_list = ["QIS", "QPS"]

    #String, with the value either QIS or QPS
    connection_type = listSelection(title="Connection: QIS or QPS", selectionList=connection_list, nice=True)
    """
    #/TO UNCOMMENT/

    #QPS is not currently working - remove option to use QPS
    connection_type = "QIS"

    #TO UNCOMMENT
    """
    #Use single instance of QIS
    if connection_type == "QIS":
    """
    #/TO UNCOMMENT/

    #TO INDENT
    #If QIS is not already running
    if not isQisRunning():
        #Start Local QIS Instance
        startLocalQis()

    #Connects to the localhost QIS instance
    QisInterface()

    #Connects 1st pam device to the same QIS Instance
    pam_1_device = get_quarch_device(connectionTarget=pam_1_address, ConType=connection_type)
    #Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
    pam_1_power_device = quarchPPM(pam_1_device)

    #Connect the 2nd PAM device to same QIS Instance
    pam_2_device = get_quarch_device(connectionTarget=pam_2_address, ConType=connection_type)
    # Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
    pam_2_power_device = quarchPPM(pam_2_device)

    #Prints the identity of both
    print(pam_1_device.send_command("*idn?"))
    print(pam_2_device.send_command("*idn?"))

    #Creates the CSV files for both stream 1 and stream 2
    file_name_pam_1 = "RawDataPam1.csv"
    file_name_pam_2 = "RawDataPam2.csv"

    print("Stream Running for 60 seconds")

    #Waits 1 second before starting stream
    time.sleep(1)

    #Starts stream on both devices for 60 seconds - May change (broadcast, or multithread)
    pam_1_power_device.start_stream(file_name=file_name_pam_1, stream_duration=stream_length)
    pam_2_power_device.start_stream(file_name=file_name_pam_2, stream_duration=stream_length)


    #TO UNCOMMENT
    """
    #Quarchpy API is likely to change
    
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
    """
    # /TO UNCOMMENT/

    #Waits stream_length: Default before user modification is 60 seconds
    visual_sleep(stream_length)

    print("Stream completed")
    print("Combining CSV files")

    #Merges the CSVs with a shared time column, adds prefix to other columns in 1_ and 2_
    csv_combiner("RawDataPam1.csv", "RawDataPam2.csv")

    #Closes connections
    pam_1_power_device.close_connection()
    pam_2_power_device.close_connection()

    #PLACEHOLDER
    print("To view the traces in Quarch Power Studio, go to the location the script is stored")
    print("Open up QPS, re-connect to one of the PAMs")
    print("File -> Import -> From CSV -> New Recording")
    print("Select the CSV named CombinedData.csv")

    #TO UNCOMMENT
    """
    #Importing into QPS is not currently working - command not implemented?
    import_csv_to_qps()
    """
    # /TO UNCOMMENT/

    return None

def csv_combiner(csv_file_1, csv_file_2):
    """
    Merges CSVs exported, keeps shared time column, renames and adds 1_ and 2_ to the column headers
    Args:
        csv_file_1: The CSV export from PAM 1
        csv_file_2: The CSv export from PAM 2

    Returns CombinedData.csv: The merged CSV
    """

    #The name of the file to be outputted
    combined_csv_name = "CombinedData.csv"

    #Uses pandas - a data analysis and manipulation tool
    #Creates a dataframe of each csv
    csv1 = pd.read_csv(csv_file_1)
    csv2 = pd.read_csv(csv_file_2)

    #Column name of the time column - This will be the same in both CSVs, and should not be changed
    #Time uS may change according to sample time
    shared_time_column = "Time uS"

    #Adds the 1_ or 2_ prefix to each individual data frame, except the time column
    #Unresolved attribute is not an issue - runs fine
    csv1_prefix = csv1.add_prefix("1_").rename(columns={"1_" + shared_time_column: shared_time_column})
    csv2_prefix = csv2.add_prefix("2_").rename(columns={"2_" + shared_time_column: shared_time_column})

    #Merge the two data frames - format being
    #time, 1_B,1_C,..., 1_XXX, 2_B,2_C,...,2_XXX
    merged_data = pd.merge(csv1_prefix, csv2_prefix, on=shared_time_column, how="outer")

    #Changes the dataframe to CSV
    merged_data.to_csv(combined_csv_name, index=False)

    #Prints the filename
    print("CSVs have been combined - filename = " + combined_csv_name)
    #Returns the CSV - possibly unused?
    return "CombinedData.csv"

def import_csv_to_qps():
    """
    NOT WORKING

    Automate the QPS import of a CSV - Command is not currently implemented?
    Function is kept, not called
    Manual way is
    QPS -> File -> Import -> From CSV -> New Recording

    Works as expected

    Returns:

    """
    #Starts Local QPS instance
    startLocalQps()

    #Connects to localhost QPS Instance
    myLocalInterface = qpsInterface()

    #Connect PAM1 (again), explicitly QPS
    pam_1_device = get_quarch_device(connectionTarget=pam_1_address, ConType="QPS")

    #Upgrade PAM1 to a QPS device
    my_qps_pam = quarchQPS(pam_1_device)

    #Opens connection to PAM
    my_qps_pam.open_connection()

    print("Please open the CSV to be displayed")

    #Tk is a python GUI package
    #Creates object for gui
    root = Tk()
    #Removes main gui window
    root.withdraw()
    #Forces the window to the top
    root.attributes('-topmost', True)

    #Get the filepath from file explorer, csv only
    csv_path = askopenfilename(title="Open the combined CSV", filetypes=(("CSV files", "*.csv"),))

    #Prints the CSV full file path
    print("CSV path = " + csv_path)

    #Creates QPS command as string
    command = "$stream import file=\"" + csv_path + "\""

    #Sends command to the QPS Interface, and stores result
    cmd_result = myLocalInterface.sendCmdVerbose(command)

    print("Importing of CSV Values: " + cmd_result)


if __name__ == "__main__":
    main()
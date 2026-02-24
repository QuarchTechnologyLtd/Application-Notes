"""AN-034
This Application Note uses 2 AC Power Analysis Modules to stream synchronously, with the user choosing to stream
over QIS or over QPS. Either option will export a CSV, which is then merged, and opened in QPS.

The application this has been designed for is for a high power environment, where a single AC PAM does not have the
capability to measure the full load, so 2 AC PAMs are used. Both PAM data streams can be viewed side by side.

To reduce latency from one stream starting to the next stream starting, this script uses a compiled C file to spin
up 2 CPU cores, and keep them busy, until the start_stream command is called. This requires the use of a compiler -
GCC recommended. The two streams from both PAMs should start relatively synchronously.

In testing, the desync was typically less than 5ms, with most being less than 1ms between 1 stream starting and the
next stream starting. This is likely related to network latency.

This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Using multiple cores in parallel
-Combining multiple CSVs into a single CSV, with a shared column
-Manually importing CSVs into QPS for comparison.

########### VERSION HISTORY ###########
13/01/2026 - Andrew Steedman - Created
16/01/2026 - Stuart Boon - Multi-threading
20/01/2026 - Andrew Steedman - Working with QIS, and semi-automated

########### REQUIREMENTS ##############

1 - Python (3.x recommended)
    https://www.python.org/downloads/
2 - Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3 - GCC (GNU Compiler Collection) - See README.md
5- A multicore processor (2 minimum)

########### INSTRUCTIONS ##############

1 - Connect AC PAMs to the same LAN as control PC
2 - Connect AC PAMs to power
3 - Change the global variables: PAM_1_ADDRESS, PAM_2_ADDRESS, STREAM_LENGTH
4 - Run the script with admin permissions
"""
#Local files
import syncUtils
import syncComplexClasses

import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

#Included in default installation
import time
import os

#USER TO CHANGE - Constants, Should be static while program is running
# Hardcoded PAM Addresses
PAM_1_ADDRESS = "USB:QTL2312-01-477"
PAM_2_ADDRESS = "USB:QTL2312-01-035"

#Stream length in seconds - QIS call takes float parameter
STREAM_LENGTH = float(20)

#The rate at which to resample the stream - DC PAMs minimum is 4us, AC PAMs is 250us
STREAM_RESAMPLE_RATE = "1ms"

#/USER TO CHANGE/

#All in Current Working Directory
#Filename of the CSV output from PAM1
FILE_NAME_PAM_1 = "RawDataPam1.csv"

#Filename of the CSV output from PAM2
FILE_NAME_PAM_2 = "RawDataPam2.csv"

#The name of the file after the 2 pam streams have been combined
FILE_NAME_COMBINED = os.path.join(os.getcwd(),"CombinedPamData.csv")


def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    print("*****************************************")
    print("*****************************************\n")
    print("AN-034 - Multiple PAM Synchronous Stream")
    print("Connect the devices over IP on the same network")
    print("\n*****************************************")
    print("*****************************************")

    #Requires features added in 2.2.17
    requiredQuarchpyVersion("2.2.17")

    #e.g. Standard DC PAMs (QTL2312)
    #Asks if user is using a triggering cable
    print("Are you using PAMs connected by a triggering cable?")
    hardware_trigger = showYesNoDialog(title="Triggering cable?", message="Yes for triggering cable, no for software trigger")

    #Optional hardcode - uncomment either line to hardcode it
    #hardware_trigger = "Yes"
    #hardware_trigger = "No"

    if hardware_trigger == "Yes": #Using triggering cable
        #Asks user QIS or QPS
        optionList = "QIS,QPS"
        connection_type = user_interface.listSelection(title="QIS or QPS", message="Select QIS or QPS",selectionList=optionList, nice=True)

        #Optional hardcode - uncomment either line to hardcode it and comment in line above
        #connection_type = "QIS"
        #connection_type = "QPS"

        #If using QIS, call the setup function - response is different based on QIS or QPS
        if connection_type == "QIS":
            pam1, pam2, qis = launch_and_setup(connection_type)

        else: #QPS
            pam1, pam2, qps1, qps2 = launch_and_setup(connection_type)

        #Gets the serial number in the format XXXX-XX-XXX
        pam_1_name = "QTL" + pam1.sendCommand("*enclosure?")
        pam_2_name = "QTL" + pam2.sendCommand("*enclosure?")

        # Upgrades PAM to quarchPPM class
        pam_1_power_device = quarchPPM(pam1)
        pam_2_power_device = quarchPPM(pam2)

        #Resamples the PAMs so they are sampling at the same rate
        pam_1_power_device.send_command(f"stream mode resample {STREAM_RESAMPLE_RATE}")
        pam_2_power_device.send_command(f"stream mode resample {STREAM_RESAMPLE_RATE}")

        #Gives instructions of how to connect the PAM triggers
        print(f"Connect PAM 1 {pam_1_name} trigger out, to PAM 2 {pam_2_name} trigger in\n")
        showDialog(title="Select yes, when setup", message=f"Is it setup in this way?")

        print("\nConfiguring Trigger...\n")

        #Configure recording trigger on PAM2
        pam_2_power_device.send_command("RECord:RUN")
        pam_2_power_device.send_command("RECord:TRIGger:MODE EXTernal")

        #Gives time for it to be setup
        time.sleep(1)

        #Configure trigger out on pam 1
        pam_1_power_device.send_command("TRIGger:OUT:MODE RECORD")

        #Setups stream on PAM2, with the target CSV - waits on trigger
        pam_2_power_device.start_stream("RawDataPam2.csv")

        # Gives time for it to be setup
        time.sleep(1)

        print("Streaming...")

        #Starts stream on both devices
        pam_1_power_device.start_stream("RawDataPam1.csv", stream_duration=STREAM_LENGTH)

        #Waits stream_length
        time.sleep(STREAM_LENGTH)

        #Stop PAM2 after Stream Length - trigger only syncs the start
        pam_2_power_device.send_command("RECord:STOP")

        time.sleep(2)
        #Closes the connection 2 seconds after stream ended
        pam_2_power_device.close_connection()

    else: #Using software trigger (e.g. AC PAMs - both 3 phase and IEC PAMs)
        #Asking user if QIS or QPS
        optionList = "QIS,QPS"
        connection_type = user_interface.listSelection(title="QIS or QPS", message="Select QIS or QPS",selectionList=optionList, nice=True)

        #Optional hardcode, uncomment either line and comment in line above
        #connection_type = "QIS"
        #connection_type = "QPS"

        #Similar to switch case in other languages - reduces indents and easier to read
        match (connection_type, os.name):
            case ("QIS", "nt"): #QIS, Windows, C
                startLocalQis()
                syncStreamObj = syncComplexClasses.CWindows(FILE_NAME_PAM_1,FILE_NAME_PAM_2,STREAM_LENGTH, STREAM_RESAMPLE_RATE, PAM_1_ADDRESS, PAM_2_ADDRESS)

            case ("QIS", "posix"): #QIS, POSIX, C
                startLocalQis()
                syncStreamObj = syncComplexClasses.CPosix(FILE_NAME_PAM_1,FILE_NAME_PAM_2,STREAM_LENGTH, STREAM_RESAMPLE_RATE, PAM_1_ADDRESS, PAM_2_ADDRESS)

            case ("QPS", "nt"): #QPS, Windows, C
                syncStreamObj = syncComplexClasses.CWindows(FILE_NAME_PAM_1,FILE_NAME_PAM_2,STREAM_LENGTH, STREAM_RESAMPLE_RATE, PAM_1_ADDRESS, PAM_2_ADDRESS)

            case ("QPS", "posix"): #QPS, POSIX, C
                syncStreamObj = syncComplexClasses.CPosix(FILE_NAME_PAM_1,FILE_NAME_PAM_2,STREAM_LENGTH, STREAM_RESAMPLE_RATE, PAM_1_ADDRESS, PAM_2_ADDRESS)

            case _: #Catchall - OS is the only one that isn't binary - i.e. qis or qps, c or python
                print("OS not currently supported. Please use a Windows or POSIX system")
                raise OSError("Unsupported operating system")

        #startLocalQis()

        syncStreamObj.stream(connection_type)

    print("Stream completed\n")
    print("Combining CSV files...")

    #Merges the CSVs with a shared time column, adds prefix to other columns in 1_ and 2_
    combined_csv = syncUtils.csv_combiner(FILE_NAME_PAM_1, FILE_NAME_PAM_2)

    #PLACEHOLDER
    print("Opening QPS and reconnecting to a PAM to view the traces\n...\n")

    #Opens QPS, ready for user to manually import CSV
    if connection_type == "QPS":
        #Passes in the already open instance of QPS used for PAM 1
        syncUtils.view_csv_in_qps(qps1, combined_csv)
        #Close the 2nd QPS instance
        closeQps(port=9823)

    else: #If QIS was used, open a QPS instance
        syncUtils.view_csv_in_qps(combined_csv, PAM_1_ADDRESS)

    print("PAM1 traces are prefixed with 1_, PAM2 traces are prefixed with 2_")
    print("If running again, rename the QPS recording, and CSV")

    sys.exit(0)


def launch_and_setup(connection_type):
    if connection_type == "QPS":
        # QPS instance 1 is easy - use default ports
        qps1 = startLocalQps(startQPSMinimised=False)

        # Connects 1st pam device to the same QIS Instance - timeout of 20s timeout=str(20)
        pam1 = get_quarch_device(connectionTarget=PAM_1_ADDRESS, ConType=connection_type, qps_instance=qps1)

        pam_1_qps = quarchQPS(pam1)

        pam_1_qps.openConnection()

        #Create separate QIS backend
        #startLocalQis(port=9723,rest_port=9781)
        #Creates separate QPS launch, connected to second QIS instance
        qps2 = startLocalQps(startQPSMinimised=False,port=9823, qis_port=9723, qis_rest_port=9781)

        #Connects the 2nd PAM to the 2nd QIS
        pam2 = get_quarch_device(connectionTarget=PAM_2_ADDRESS, ConType=connection_type, qps_instance=qps2)

        pam_2_qps = quarchQPS(pam2)

        pam_2_qps.openConnection()

        #Returns the pams, and qps objects
        return pam_1_qps, pam_2_qps, qps1, qps2

    else:  # QIS
        # If QIS is not already running
        if isQisRunning():
            qis = QisInterface()
        else:
            # Start Local QIS Instance
            print("Starting QIS...")
            qis = startLocalQis()

        # Connects 1st pam device to the same QIS Instance
        pam1 = get_quarch_device(connectionTarget=PAM_1_ADDRESS, ConType=connection_type)

        pam2 = get_quarch_device(connectionTarget=PAM_2_ADDRESS, ConType=connection_type)
        return pam1, pam2, qis


if __name__ == "__main__":
    main()

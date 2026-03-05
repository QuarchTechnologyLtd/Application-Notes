"""AN-034
This Application Note uses 2 Power Analysis Modules to stream synchronously, over QIS.
This will export a CSV, which is then merged, and opened in QPS.

If using AC PAMs, suggested application is a singular high power requirement source, where one AC PAM is not enough to capture all power.
If using DC PAMs, suggested application is to measure the power used by different components of a single system. e.g. using a QTL2983 GPU PAM,
and a QTL3069 Gen6 EDSFF PAM, in the same system.

To reduce latency from one stream starting to the next stream starting, this script uses a compiled C file to spin
up 2 CPU cores, and keep them busy, until the start_stream command is called. This requires the use of a compiler -
GCC recommended. There is a check to not recompile, if the file is there

In testing, when connected over IP the desync was typically less than 5ms worst case scenario, with most being less than 1ms
between 1 stream starting and the next stream starting. This is likely related to network latency. USB is slower in testing

If you are running multiple times, rename the CSVs and saved QPS file, otherwise the CSVs will be overwritten, and automatic QPS import will fail.
In this script, there are various optional hardcodes - stream length, stream resample rate, number of pams, pam addresses, whether to display in QPS or not.
If running multiple times, it is suggested to hardcode these to speed up the time in between tests.

This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Using multiple cores in parallel
-Combining multiple CSVs into a single CSV, with a shared column
-Automatically importing CSVs into QPS for comparison.

########### VERSION HISTORY ###########
24/02/2026 - Stuart Boon - Multi-threading
05/03/2026 - Andrew Steedman - Separated simpler and complex versions

########### REQUIREMENTS ##############

1 - Python (3.x recommended)
    https://www.python.org/downloads/
2 - Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3 - GCC (GNU Compiler Collection) - See README.md
5- A multicore processor (minimum 2 - 1 per PAM used)

########### INSTRUCTIONS ##############

1 - Connect PAMs to the same LAN as control PC
2 - Connect PAMs to power
3 - Run the script with admin permissions
"""
#Local files
import syncUtils
import syncComplexClasses

#Quarchpy files
import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

import time
import os


def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    #logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    #quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    displayTable(["AN-034 - Multiple PAM Synchronous Stream Complex\n","Connect the devices over IP on the same network"], printToConsole=True, align="c")

    #Requires features added in 2.2.17
    requiredQuarchpyVersion("2.2.17")

    connection_type = "QIS"

    # Start QIS if not running
    if not isQisRunning():
        # myQis is the QIS Interface
        myQis = startLocalQis()
        keep_qis_running = False

    else:
        # Connect to the open instance of QIS
        myQis = QisInterface()
        keep_qis_running = True


    #Start of parameter selection - optional hardcodes are commented in
    #User selects stream length
    print("Please input the stream length in seconds. Leave blank for default of 60 seconds")
    # Takes user input
    stream_length_input = str(input("Please enter stream length in seconds: "))
    # Checks if blank
    if stream_length_input == "":
        # Sets to 60 seconds if left blank
        stream_length = float(60)
    else: #Some value has been entered
        try: #If stream_length_input is not a number, will fail
            if int(stream_length_input) > 0:
                # Otherwise, take the users input
                stream_length = float(stream_length_input)
            else:
                # Value entered is either 0, or negative
                print("Value entered is invalid - Using default of 60 seconds")
                # Uses default length
                stream_length = float(60)
        except ValueError: #Catches the error
            print("Value entered is invalid - Using default of 60 seconds")
            stream_length = float(60)
    print(f"Stream length selected is: {stream_length} seconds")

    #Optional Hardcode - comment in lines above, uncomment this
    #stream_length = float(60)

    #Sets Resample Rate
    #If both are DC PAMs, allow up to 4us sampling
    ac_pam = showYesNoDialog(title="PAM type?", message="Is at least 1 of the PAMs an AC PAM?")
    if ac_pam == "No":
        # Has higher resolution sampling available
        resample_rate_list = "4us,16us,100us,1ms,4ms,16ms,100ms,1s"

    # If at least one is not a DC PAM, allow up to 250us sampling - we want all PAMs to stream at the same resample rate
    else:
        resample_rate_list = "250us,1ms,4ms,16ms,100ms,1s"

    # Takes the user input
    resample_rate = listSelection(title="Select resample rate", message="Select resample rate",
                                  selectionList=resample_rate_list, nice=True)

    #Optional Hardcode - comment in lines above, uncomment this
    #resample_rate = "1ms"

    print("How many PAMs are you using?")
    #Quit is an option to match up indexing - 2 pams enter 2, 4 pams enter 4
    optionList = "Quit,2,3,4,5"
    #Takes user input
    pam_count = user_interface.listSelection(title="Select PAM", message="How many PAMs?",selectionList=optionList, nice=True)
    if pam_count == "Quit":
        exit(0)

    #Optional hardcode - uncomment this and comment in lines above
    #pam_count = "2"

    #Dictionary of PAM addresses and their file names
    pam_configs = []
    #For each PAM, append pam_configs
    for i in range(int(pam_count)):
        #Gets module list, with additional options
        selected_pam = myQis.get_qis_module_selection(additional_options=["Rescan", "All Con Types", "Ip Scan", "Quit"])

        if selected_pam == "Quit":
            exit(0)

        #Add the PAM address, and filename to pam_configs
        pam_configs.append({
            "address": selected_pam,
            "filename": f"RawDataPam{i+1}.csv"
        })

    #Uncomment this if wanting to hardcode, and comment in section above
    #pam_configs = [{"address": "USB:QTL2312-01-477", "filename": "RawDataPam1.csv"},
    #               {"address": "USB:QTL2312-01-035", "filename": "RawDataPam2.csv"},
    #               {"address": "TCP:10.0.8.95",      "filename": "RawDataPam3.csv"},
    #               {"address": "USB:QTL2312-01-001", "filename": "RawDataPam4.csv"},
    #               {"address": "TCP:10.0.8.95",      "filename": "RawDataPam5.csv"}]
    #END of stream parameter configuration

    #If Windows
    if os.name == "nt":
        #Creates the object
        syncStreamObj = syncComplexClasses.CWindows(pam_configs, stream_length, resample_rate)

    #If Linux
    elif os.name == "posix":
        #Creates the object
        syncStreamObj = syncComplexClasses.CPosix(pam_configs, stream_length, resample_rate)

    #If not Windows or Linux, state unsupported
    else:
        print("OS not currently supported. Please use a Windows or POSIX system")
        raise OSError("Unsupported operating system")

    #Start the stream
    syncStreamObj.stream(connection_type)

    print("Stream completed\n")
    print("Combining CSV files...")

    #Creates a filelist of the file names
    filelist = [pam["filename"] for pam in pam_configs]

    #Combine the CSVs with a shared time column
    combined_csv_path = syncUtils.csv_combiner(filelist)
    print(f"Combined CSV file can be found : {combined_csv_path}")

    #Stream is complete
    #Asks user if they want to combine data and display it in QPS
    display_in_qps = showYesNoDialog(title="Post-process?", message="Do you want to display the data in QPS?")

    #Optional Hardcode - uncomment one of these lines, comment in line above
    #display_in_qps = "Yes"
    #display_in_qps = "No"

    if display_in_qps == "Yes":
        #QPS will connect to PAM 1
        pam_address = pam_configs[0]["address"]
        #And then convert and open in QPS
        syncUtils.view_csv_in_qps(combined_csv_path, pam_address)

        #Iterates over PAM_Configs, from PAM 2 onwards
        for pam in pam_configs[1:]:
            # Gets address of the PAMs
            address = pam["address"]

            # Closes connection to PAMs
            myQis.send_command(f"close {address}")

    #If no, exit the script, provide filepath to the CSVs
    if display_in_qps == "No":
        #For each PAM, display the filepath, close the connection
        for pam in pam_configs:
            #Gets absolute path of the stream CSVs
            address = pam["address"]
            file = pam["filename"]
            path = os.path.abspath(file)

            #Display the absolute path of the stream CSVs
            print(f"PAM {pam} stream data can be found: {path}")

            #Closes connection to PAMs
            myQis.send_command(f"close {address}")

        #If QIS was already open, leave running.
        if not keep_qis_running:
            #Closes connection to QIS
            myQis.close_connection()

        print("Exiting...")

        exit(0)


if __name__ == "__main__":
    main()
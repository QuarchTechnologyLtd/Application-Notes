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

    #Display the title and instructions in a table - neater than print statements
    displayTable(["AN-034 - Multiple PAM Synchronous Stream Complex","Connect the devices over IP on the same network"], printToConsole=True, align="c")

    #Requires features added in 2.2.19
    requiredQuarchpyVersion("2.2.19")

    connection_type = "QIS"

    print("Launching QIS")

    # Start QIS if not running
    if not isQisRunning():
        # myQis is the QIS Interface
        myQis = startLocalQis()
        keep_qis_running = False

    else:
        # Connect to the open instance of QIS
        myQis = QisInterface()
        keep_qis_running = True

    print("Please input the stream length in seconds. Leave blank for default of 60 seconds")
    # Takes user input
    stream_length_input = str(input("Please enter stream length in seconds: "))
    #Optional hardcode - uncomment this and comment in the line above to hardcode the stream length - change line 71 to change the stream length
    #stream_length_input = ""

    #We check if the inputted value is black
    if stream_length_input == "":
        #If it is, we use the default of 60 seconds
        stream_length = 60

    else: #Some value has been entered
        try: #If stream_length_input is not a number, will fail

            if int(stream_length_input) > 0: #Check if the inputted value is positive
                #If it is positive, take the users input
                stream_length = int(stream_length_input)

            else:# Value entered is either 0, or negative
                print("Value entered is invalid - Using default of 60 seconds")
                # Uses default length
                stream_length = 60

        except ValueError: #Catches the error
            print("Value entered is invalid - Using default of 60 seconds")
            stream_length = 60

    print(f"Stream length selected is: {stream_length} seconds")

    #Optional Hardcode - comment in lines above, uncomment this
    #stream_length = 60

    print("How many PAMs are you using?")
    #Quit is an option to match up indexing - 2 pams enter 2, 4 pams enter 4
    optionList = "Quit,2,3,4,5"
    #Takes user input
    pam_count = user_interface.listSelection(title="Select PAM", message="How many PAMs?",selectionList=optionList, nice=True)
    if pam_count == "Quit":
        exit(0)

    #Optional hardcode - uncomment this and comment in lines above
    #pam_count = "5"

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
    #pam_configs = [{"address": "TCP:10.0.8.95", "filename": "RawDataPam1.csv"},
                   #{"address": "TCP:10.0.8.59", "filename": "RawDataPam2.csv"},
                   #{"address": "TCP:10.0.8.107",      "filename": "RawDataPam3.csv"},
                   #{"address": "TCP:10.0.8.109", "filename": "RawDataPam4.csv"},
                   #{"address": "TCP:10.0.8.110",      "filename": "RawDataPam5.csv"}]
    #END of stream parameter configuration

    model_list = [pam["address"].split(":")[-1].split("-")[0] for pam in pam_configs]
    print(model_list)
    all_dc_pams = all(model=="QTL2312" for model in model_list)
    print(all_dc_pams)
    if all_dc_pams:
        #This means we can resample at up to 4us. This is the same across both analog and digital channels
        allow_4us_sampling = True

    else:#At least one of the PAMs is not a DC PAM. Therefore, we will limit the resample rate to 125us.
        #This will be the same across PAMs, so a DC PAM and AC PAM would both sample at 125us.
        allow_4us_sampling = False

    # Takes user input for the resample rate
    resample_rate_input = str(input("Please enter resample rate in the format: 125us, 1ms, 1s: "))

    # This is a function to validate the inputted resample rate
    # If an invalid option is entered, it will use the default of 1ms
    resample_rate = syncUtils.validate_resample_rate(resample_rate_input, allow_4us_sampling)

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

    #Get the approximate time for the stream start, formatted into YYMMDD-HHMMSS
    stream_start_time_for_filename =time.strftime("%Y_%m_%d-%H_%M_%S")

    #Start the stream, and capture the array of start times
    stream_start_times_ns = syncStreamObj.stream(connection_type)

    print("Stream completed\n")
    print("Combining CSV files...")

    #Creates a filelist of the file names
    filelist = [pam["filename"] for pam in pam_configs]

    #Stream is complete
    #Asks user if they want to combine data and display it in QPS
    post_process = showYesNoDialog(title="Post-process?", message="Do you want to display the data in QPS?")

    #Optional Hardcode - uncomment one of these lines, comment in line above
    #post_process = "Yes"

    #If no, exit the script
    if post_process == "No":
        #Gets absolute path of the stream CSVs
        for file in filelist:
            path = os.path.abspath(file)
            print(f"PAM data can be found at: {path}")

        print("Closing connections...")

        #If we launched QIS in the script, we will close QIS in the script
        if not keep_qis_running:
            print("Closing QIS")
            closeQis()
        else:
            #If QIS was already running, leave it running, but close the device connection
            myQis.close_connection()

        print("Exiting...")

        #Exit the script
        sys.exit(0)

    if post_process == "Yes":
        print("Launching QPS to view the trace")

        #Get the address of the first PAM
        primary_pam = pam_configs[0]["address"]

        #Single function call. This will
        #A) Merge the CSVs and align the timestamps
        #B) Convert the CSV data into a QPS Recording
        #C) Open the QPS recording, and show either 100s worth of recording, or the stream length, whichever is less
        combined_csv_path = syncUtils.view_csv_in_qps(primary_pam, stream_length, stream_start_time_for_filename, filelist, stream_start_times_ns)

        if not keep_qis_running:
            print('Closing QIS...')
            closeQis()
        else:
            print("Leaving QIS open, closing device connections")
            myQis.close_connection()

        print("Exiting...")

        sys.exit(0)


if __name__ == "__main__":
    main()

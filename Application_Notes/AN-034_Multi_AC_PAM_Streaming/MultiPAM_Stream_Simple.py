"""
This script can be used to stream from 2 PAMs simultaneously. This uses standard python, streams over QIS, and has the option to use a hardware trigger.
There is an alternate version, which can be used for up to 5 PAMs, and has less delay between streams.
This demonstrates the use of the Quarchpy library, and how to control multiple units.
Using USB to connect the PAMs is possible.
This script works with both DC PAMs (QTL2312), and AC PAMs (e.g. QTL2582), or a combination of both.

This script has 2 ways of starting the streams.
Option 1 is using an MCX triggering cable between the PAMs. PAM 1 trigger out, connected to PAM 2 trigger in. This is the preferred option if DC PAMS (QTL2312) are used.
Option 2 is using a software trigger, uses 2 CPU cores. The CPU cores are kept busy, until a set time, after which the stream is started.
The PAM streams are executed on separate cores, which reduces the delay between stream 1 and stream 2 starting.
This is intended for modules that don't have triggering - most AC PAMs.

This will be heavily system dependent, but the delay between 1 stream starting and the next stream starting, using a hardware trigger,
is as little as 3ms apart, and using a software trigger, as little as 15.8ms apart. Starting the streams sequentially (the default option)
had delays of as little as 37ms.

The PAMs will stream for a user selectable length of time, and save the recording into a CSV each. After the streams are complete, the user has the option
to postprocess the data, and view the data in QPS.

This script is designed for use with PAMs, and variables are named as such, but it should be possible to use with PPMs. There are some comments indicating
where PPM setup can be done, and mid-stream commands can be run.

Suggested applications of this:
Measuring 2 devices concurrently: e.g. an SSD and a GPU
Measuring AC power where the host power is above the PAM's rating.

########### VERSION HISTORY ###########
03/03/2026 - Andrew Steedman - Released
08/05/2026 - Andrew Steedman - Uprev'd to add QoL features, including CSV time alignment

########### REQUIREMENTS ##############

1 - Python (3.x recommended)
    https://www.python.org/downloads/
2 - Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- A multicore processor (2 minimum)
4- syncUtils.py stored in the same directory as this script

########### INSTRUCTIONS ##############

1 - Set up the PAM Fixture
2 - Connect the PAMs to the PC
3 - Run the script
"""

import os
import sys
import time

import quarchpy
from quarchpy.device import quarchPPM, get_quarch_device
from quarchpy.qis import *
from quarchpy.qps import startLocalQps
from quarchpy.user_interface import showYesNoDialog, showDialog, visual_sleep, listSelection, displayTable
import syncUtils


def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    #logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    #Dislay the title and instructions using a quarchpy.user_interface function - neater than printing multiple lines
    displayTable(["AN-034 - Multiple PAM Synchronous Stream Simple","Connect the devices to the same host PC"],printToConsole=True, align="c")

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

    #If QIS is not already running, start QIS
    if not isQisRunning():
        print("Starting QIS...")
        #Start QIS, with myQis being the interface
        myQis = startLocalQis()
        #If we start QIS in script, close it after we are finished
        keep_qis_running = False
    else: #QIS already launched, myQis is the interface
        print("QIS already running.")
        myQis = QisInterface()
        #If QIS is already running, keep it running after we are finished
        keep_qis_running = True

    #Connection logic to the PAM. A list of Quarch modules found will be displayed for user selection.
    my_pam_1 =  myQis.GetQisModuleSelection(additionalOptions=['Rescan', 'All Con Types', 'Ip Scan','Quit'])
    print("PAM 1 is: " + my_pam_1 + "\n")
    #If quit is selected, close QIS and exit script
    if my_pam_1 == "Quit":
        closeQis()
        print("User selected quit")
        exit(0)

    my_pam_2 =  myQis.GetQisModuleSelection(additionalOptions=['Rescan', 'All Con Types', 'Ip Scan','Quit'])
    print("PAM 2 is: " + my_pam_1 + "\n")
    #If quit is selected, close QIS and exit script
    if my_pam_2 == "Quit":
        closeQis()
        print("User selected quit")
        exit(0)

    #The return from the module selection is a device ID string that we can use to connect to.
    #If you know the name of the module you would like to talk to, then comment out module selection and
    #hardcode the string using the serial number or IP address as shown below
    #my_pam_1 = "TCP:10.0.8.3"
    #my_pam_2 = "USB:QTL2312-01-477"

    #Connect to both modules. This connection will remain open if using a hardware trigger, but if we are using
    #a software trigger, this will be closed - we reconnect in each thread. We connect here to check the connections
    #are available, and the PAMs are responding.
    print('\nAttempting connection to ' + my_pam_1 + '...')
    #Create a Quarch Device with a timeout of 10 seconds
    my_pam_1_device = get_quarch_device(my_pam_1, ConType="QIS", timeout="10")

    #Sends command hello?
    pam_1_name = my_pam_1_device.send_command('hello?')

    #This is used to check whether we are using DC PAMs or AC PAMs. Will return e.g. 2312-01-477, 2582-01-001
    pam_1_enclosure = my_pam_1_device.send_command('*enclosure?')

    #If there's no response, raise an exception
    if pam_1_name is None:
        raise Exception("Failed to connect to " + my_pam_1 + "!")

    print('Attempting connection to ' + my_pam_2 + '...\n')
    # Create a Quarch Device with a timeout of 10 seconds
    my_pam_2_device = get_quarch_device(my_pam_2, ConType="QIS")

    #Sends command hello?
    pam_2_name = my_pam_2_device.send_command('hello?')

    # This is used to check whether we are using DC PAMs or AC PAMs
    pam_2_enclosure = my_pam_2_device.send_command('*enclosure?')

    # If there's no response, raise an exception
    if pam_2_name is None:
        raise Exception("Failed to connect to " + my_pam_2 + "!")

    #Print the names of the PAMs
    print("PAM 1 is: " + pam_1_name)
    print("PAM 2 is: " + pam_2_name + "\n")

    # Takes user input for the resample rate
    resample_rate_input = str(input("Please enter resample rate in the format: 125us, 1ms, 1s: "))

    #Check the first 4 letters of the string returned from the command *enclosure?
    if pam_1_enclosure[:4] == "2312" and pam_2_enclosure[:4] == "2312":
        #This means we can resample at up to 4us. This is the same across both analog and digital channels
        allow_4us_sampling = True
    else:#At least one of the PAMs is not a DC PAM. Therefore, we will limit the resample rate to 125us.
        #This will be the same across PAMs, so a DC PAM and AC PAM would both sample at 125us.
        allow_4us_sampling = False

    # This is a function to validate the inputted resample rate
    # If an invalid option is entered, it will use the default of 1ms
    resample_rate = syncUtils.validate_resample_rate(resample_rate_input, allow_4us_sampling)

    print(f"Resample rate of {resample_rate} selected")

    #Asks the user if they are using a hardware trigger
    hardware_trigger = showYesNoDialog(title="Are you using a triggering cable between the PAMs?", message="Are using a triggering cable between the PAMs?")

    #Optional Hardcode - Uncomment this and comment in line above - suggested to hardcode this for AC PAMs
    #hardware_trigger = "No"

    if hardware_trigger == "Yes":
        # Upgrades quarch device to quarchPPM - Power class with more features
        pam_1_power_device = quarchPPM(my_pam_1_device)
        pam_2_power_device = quarchPPM(my_pam_2_device)

        # Sets the stream resample rate to resample_rate (Default 1ms) across both devices
        pam_1_power_device.send_command(f"stream mode resample {resample_rate}")
        pam_2_power_device.send_command(f"stream mode resample {resample_rate}")

        #Provides instructions on how to connect the units
        print(f"Connect PAM 1 ({my_pam_1}) trigger out, to PAM 2 ({my_pam_2}) trigger in")
        #User presses enter when ready
        showDialog(title="Select yes, when setup", message=f"Is it setup in this way?")

        #This script is designed for PAMs, and variables are named accordingly. However, most of this logic should work with PPMs
        #Here is the best place to configure PPMs, before we start streaming.

        #Configures PAM2 to accept an input trigger to start recording
        pam_2_power_device.send_command("RECord:RUN")
        pam_2_power_device.send_command("RECord:TRIGger:MODE EXTernal")

        #Configures PAM1 to output a trigger record start
        pam_1_power_device.send_command("TRIGger:OUT:MODE RECORD")

        #Sleep for 1 second is to allow the triggering command to be set before streaming
        time.sleep(1)

        print("Trigger set-up")

        #Starts the stream, but waits for the PAM 1 trigger
        pam_2_power_device.start_stream("RawDataPam2.csv")

        #Delay is to allow PAM 2 to be waiting for trigger - without the delay PAM2 might not be ready
        time.sleep(1)

        #Starts stream on PAM 1, which will fire the trigger on PAM2, with a length of 60 seconds
        pam_1_power_device.start_stream("RawDataPam1.csv", stream_duration=stream_length)

        #OPTIONAL PPM Logic. For anything to run while we are recording, run here. e.g. run pattern

        #Set the stream start for the filename here
        timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")

        #This is called in the post_processing section. We check the difference in start time to align the data/
        #stream_start_times_ns is used for the software trigger. By setting both timestamps to the same, we don't have any difference to adjust for
        current_time_ns = time.time_ns()
        stream_start_times_ns = [current_time_ns, current_time_ns]

        print("Stream started")

        #Waits stream_length
        visual_sleep(stream_length)

        #Stop PAM2 after Stream Length - trigger only syncs the start
        pam_2_power_device.send_command("RECord:STOP")

        print("Stream completed")

        print("Closing connection to PAMs")

        #Sleep for 1 second to ensure the stream is completed before we close the connection
        time.sleep(1)
        #Closes connection to PAMs
        pam_1_power_device.close_connection()
        pam_2_power_device.close_connection()


    else: #Use a software trigger
        #Close the existing connections to the PAM. We will reconnect in each thread, but we close here to avoid a Pickling error
        my_pam_1_device.close_connection()
        my_pam_2_device.close_connection()

        #We create the timestamp for filenames here, so that the CSV and QPS recording will be timestamped with the start of the recording
        timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")

        #This is a quicker way of starting the stream compared to just starting the streams sequentially
        #Uses 2 CPU cores, that are kept busy, and the pam command to start streaming is waiting to jump in
        #Will fail on a single core PC
        #stream_start_times_ns is a list of the times the streams started at, in nanoseconds.
        stream_start_times_ns = syncUtils.spin_cpu_and_start_stream(my_pam_1, my_pam_2, resample_rate, stream_length)

    #Stream is complete
    #Asks user if they want to combine data and display it in QPS
    post_process = showYesNoDialog(title="Post-process?", message="Do you want to combine and display the data in QPS?")
    #Optional Hardcode - uncomment this and comment in the line above to hardcode opening
    #post_process = "Yes"

    #If no, exit the script
    if post_process == "No":
        #Gets absolute path of the stream CSVs
        path1 = os.path.abspath("RawDataPam1.csv")
        path2 = os.path.abspath("RawDataPam2.csv")

        #Display the absolute path of the stream CSVs to the user
        print(f"PAM 1 stream data can be found: {path1}")
        print(f"PAM 2 stream data can be found: {path2}")

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
        #Create a list of both CSVs to pass in.
        filelist = ["RawDataPam1.csv", "RawDataPam2.csv"]

        #Single function call. This will
        #A) Merge the CSVs and align the timestamps
        #B) Convert the CSV data into a QPS Recording
        #C) Open the QPS recording, and show either 100s worth of recording, or the stream length, whichever is less
        combined_csv_path = syncUtils.view_csv_in_qps(my_pam_1, stream_length, timestamp_stream_start, filelist, stream_start_times_ns)

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
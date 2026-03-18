"""
This is a relatively simple, user-friendly version, which uses standard python, streams over QIS, and has the option to use a hardware trigger.
This demonstrates the use of the Quarchpy library, and how to control multiple units.
Using USB to connect the PAMs is possible.
This script works with both DC PAMs (QTL2312), and AC PAMs (e.g. QTL2582), or a combination of both.

This script has 3 ways of starting the streams.
Option 1 is using an MCX triggering cable between the PAMs. PAM 1 trigger out, connected to PAM 2 trigger in
Option 2 is starting the PAM streams sequentially. This is the default software option.
Option 3 is using a software trigger, uses 2 CPU cores. The CPU cores are kept busy, until a set time, after which the stream is started.
The PAM streams are executed on separate cores, which reduces the delay between stream 1 and stream 2 starting.

This will be heavily system dependent, but the delay between 1 stream starting and the next stream starting, using a hardware trigger,
is as little as 3ms apart, and using a software trigger, as little as 15.8ms apart. Starting the streams sequentially (the default option)
had delays of as little as 37ms.

The PAMs will stream for a user selectable length of time, and save the recording into a CSV each. After the streams are complete, the user has the option
to automatically combine the CSVs, and import and display in QPS.

########### VERSION HISTORY ###########
03/03/2026 - Andrew Steedman - Released

########### REQUIREMENTS ##############

1 - Python (3.x recommended)
    https://www.python.org/downloads/
2 - Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- A multicore processor (2 minimum)

########### INSTRUCTIONS ##############

1 - Set up the PAM Fixture
2 - Connect the PAMs to the PC
3 - Run the script
"""

import multiprocessing
import os
import time
from datetime import datetime

import quarchpy
from quarchpy.device import quarchPPM, get_quarch_device
from quarchpy.qis import *
from quarchpy.qps import startLocalQps
from quarchpy.user_interface import showYesNoDialog, showDialog, visual_sleep, listSelection, displayTable
import syncUtils


def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    #import logging
    #logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    displayTable(["AN-034 - Multiple PAM Synchronous Stream Simple","Connect the devices to the same host PC"],printToConsole=True, align="c")

    print("Please input the stream length in seconds. Leave blank for default of 60 seconds")
    # Takes user input
    stream_length_input = str(input("Please enter stream length in seconds: "))
    # Checks if blank
    if stream_length_input == "":
        # Sets to 60 seconds if left blank
        stream_length = 60

    else: #Some value has been entered
        try: #If stream_length_input is not a number, will fail
            if int(stream_length_input) > 0:
                # Otherwise, take the users input
                stream_length = int(stream_length_input)
            else:
                # Value entered is either 0, or negative
                print("Value entered is invalid - Using default of 60 seconds")
                # Uses default length
                stream_length = 60
        except ValueError: #Catches the error
            print("Value entered is invalid - Using default of 60 seconds")
            stream_length = 60

    print(f"Stream length selected is: {stream_length} seconds")

    #If QIS is not already running
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


    # The return from the module selection is a device ID string that we can use to connect to.
    # If you know the name of the module you would like to talk to, then you can skip module selection and
    # hardcode the string using the serial number or IP address
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
    #hardcode the string using the serial number or IP address
    #my_pam_1 = "USB:QTL2312-01-477"
    #my_pam_2 = "TCP:10.0.8.95"

    #Connect to the PAMs as quarchDevices
    my_pam_1_device = get_quarch_device(my_pam_1, ConType="QIS")
    my_pam_2_device = get_quarch_device(my_pam_2, ConType="QIS")

    #This is done after the PAM connection, so we can check if AC PAMs, which have a max rate of 250us
    print("Default resample rate is 1ms.")
    #Asks the user if they want to change the resample rate
    select_resample = showYesNoDialog(title="Select resample rate", message="Do you want to change resample rate?")
    #If yes, display a list with valid options
    if select_resample == "Yes":
        #*enclosure? returns the format 2312-01-001, 2582-01-001 etc
        pam_1_name = my_pam_1_device.send_command("*enclosure?")
        pam_2_name = my_pam_2_device.send_command("*enclosure?")

        #Takes the first index - 2312, 2582 etc
        pam_1_type = pam_1_name.split("-")[0]
        pam_2_type = pam_2_name.split("-")[0]

        #If both are DC PAMs, allow up to 4us sampling
        if pam_1_type == "2312" and pam_2_type == "2312":
            #Has higher resolution sampling available
            resample_rate_list ="4us,16us,100us,1ms,4ms,16ms,100ms,1s"

        #If one is not a DC PAM, allow up to 250us sampling - we want both PAMs to stream at the same resample rate
        else:
            resample_rate_list="250us,1ms,4ms,16ms,100ms,1s"

        #Takes the user input
        resample_rate = listSelection(title="Select resample rate", message="Select resample rate", selectionList=resample_rate_list, nice=True)

    #Set default value of 1ms
    else:
        resample_rate = "1ms"

    print(f"Resample rate of {resample_rate} selected")

    #Upgrades quarch device to quarchPPM - Power class with more features
    pam_1_power_device = quarchPPM(my_pam_1_device)
    pam_2_power_device = quarchPPM(my_pam_2_device)

    #Sets the stream resample rate to resample_rate (Default 1ms) across both devices
    pam_1_power_device.send_command(f"stream mode resample {resample_rate}")
    pam_2_power_device.send_command(f"stream mode resample {resample_rate}")

    #Asks the user if they are using a hardware trigger
    hardware_trigger = showYesNoDialog(title="Are you using a triggering cable between the PAMs?", message="Are using a triggering cable between the PAMs?")
    if hardware_trigger == "Yes":
        #Provides instructions on how to connect the units
        print(f"Connect PAM 1 ({my_pam_1}) trigger out, to PAM 2 ({my_pam_2}) trigger in")
        #User presses enter when ready
        showDialog(title="Select yes, when setup", message=f"Is it setup in this way?")

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

        print("Stream started")

        #Waits stream_length
        visual_sleep(stream_length)

        #Stop PAM2 after Stream Length - trigger only syncs the start
        pam_2_power_device.send_command("RECord:STOP")

        print("Stream completed")

    else: #Use a software trigger
        #Simplest option - start them sequentially
        pam_1_power_device.start_stream("RawDataPam1.csv", stream_duration=stream_length)
        pam_2_power_device.start_stream("RawDataPam2.csv", stream_duration=stream_length)
        print("Streaming...")

        #Sleeps for stream length, and 3 extra seconds
        visual_sleep(stream_length+3)

        #This is a quicker way of starting the stream - Uses 2 CPU cores, that are kept busy, and the
        #pam command to start streaming is waiting to jump in - quicker but more complex
        #Uncomment this, and comment in the 4 lines above if wanting to use

        #syncUtils.spin_cpu_and_start_stream(my_pam_1, my_pam_2, resample_rate, stream_length)

    #Stream is complete
    #Asks user if they want to combine data and display it in QPS
    post_process = showYesNoDialog(title="Post-process?", message="Do you want to combine and display the data in QPS?")
    #If no, exit the script
    if post_process == "No":
        #Gets absolute path of the stream CSVs
        path1 = os.path.abspath("RawDataPam1.csv")
        path2 = os.path.abspath("RawDataPam2.csv")

        #Display the absolute path of the stream CSVs
        print(f"PAM 1 stream data can be found: {path1}")
        print(f"PAM 2 stream data can be found: {path2}")

        print("Closing connections...")

        #Closes connection to PAMs
        pam_1_power_device.close_connection()
        pam_2_power_device.close_connection()

        #If QIS was already open, leave running.
        if not keep_qis_running:
            #Closes connection to QIS
            myQis.close_connection()

        print("Exiting...")

        exit(0)
    if post_process == "Yes":
        #If yes, combine the 2 csvs into 1
        #Combines the CSVs with a shared time column
        filelist = ["RawDataPam1.csv", "RawDataPam2.csv"]
        combined_csv_path = syncUtils.csv_combiner(filelist)

        #And then convert and open in QPS
        syncUtils.view_csv_in_qps(combined_csv_path, my_pam_1)

        #Close PAM 2 connection - PAM1 is connected to QPS, so leave open
        pam_2_power_device.close_connection()


if __name__ == "__main__":
    main()

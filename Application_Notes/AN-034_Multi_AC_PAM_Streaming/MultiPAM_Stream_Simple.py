"""
This script is a simple way of streaming from 2 PAMs together. These can either be standard DC PAMs, or can be AC PAMs
This streams over QIS, then has the option to combine both datasets together, and view in QPS.

This is a simpler, more user-friendly way of operating multiple PAMs. If shorter delays are required, see MultiPAM_Stream_Complex.
Reducing the delay adds complexity. In testing, found that (on the same system)
The hardware trigger has a minimum delay of 3ms with a mean delay of 9ms
The multiprocessing here has a minimum delay of 15.8ms, with a mean delay of 23ms.
The sequential start has a minimum delay of 36.8ms with a mean delay of 65ms.

The PAM streams can either be started with the PAMs connected by a triggering cable,or a software trigger.
If using PAMs with a triggering cable, suggested to use it
For PAMs without a triggering cable (e.g. AC PAMs), you will need to use a software trigger.

This will configure both PAMs to have the same resample rate, stream for the same length. The stream runs, and 2 CSVs are recorded.
There is then an option to automatically merge the CSVs, convert the CSVs to QPS Recording, and then open the QPS recording, and view
the PAM data side by side.

########### VERSION HISTORY ###########
24/02/2026 - Andrew Steedman - Branched from MultiPAM_Stream_Complex.py

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
from quarchpy.user_interface import showYesNoDialog, showDialog, visual_sleep
import syncUtils

#Length of stream in seconds
STREAM_LENGTH = 60

#Resample rate
RESAMPLE_RATE = "1ms"

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    #logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    print("*****************************************")
    print("*****************************************\n")
    print("AN-034 - Multiple PAM Synchronous Stream Simple")
    print("Connect the devices to the same host PC")
    print("\n*****************************************")
    print("*****************************************")

    if not isQisRunning():
        print("Starting QIS...")
        myQis = startLocalQis()

    # The return from the module selection is a device ID string that we can use to connect to.
    # If you know the name of the module you would like to talk to, then you can skip module selection and
    # hardcode the string using the serial number or IP address
    my_pam_1 =  myQis.GetQisModuleSelection(additionalOptions=['Rescan', 'All Con Types', 'Ip Scan','Quit'])
    print("PAM 1 is: " + my_pam_1 + "\n")

    my_pam_2 =  myQis.GetQisModuleSelection(additionalOptions=['Rescan', 'All Con Types', 'Ip Scan','Quit'])
    print("PAM 2 is: " + my_pam_1 + "\n")

    # The return from the module selection is a device ID string that we can use to connect to.
    # If you know the name of the module you would like to talk to, then you can skip module selection and
    # hardcode the string using the serial number or IP address
    #my_pam_1 = "USB:QTL2312-01-477"
    #my_pam_2 = "TCP:10.0.8.95"

    # Upgrades the PAMs to PPM devices - more features
    my_pam_1_device = get_quarch_device(my_pam_1, ConType="QIS")
    my_pam_2_device = get_quarch_device(my_pam_2, ConType="QIS")

    #Upgrades quarch device to quarchPPM - Power product class with more features
    pam_1_power_device = quarchPPM(my_pam_1_device)
    pam_2_power_device = quarchPPM(my_pam_2_device)

    #Sets the stream resample rate to RESAMPLE_RATE (Default 1ms) across both devices
    pam_1_power_device.send_command(f"stream mode resample {RESAMPLE_RATE}")
    pam_2_power_device.send_command(f"stream mode resample {RESAMPLE_RATE}")

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

        time.sleep(1)

        print("Trigger set-up")

        #Setups stream on PAM2, with the target CSV - waits on trigger
        pam_2_power_device.start_stream("RawDataPam2.csv")

        time.sleep(1)

        #Starts stream on PAM 1, which will fire the trigger on PAM2, with a length of 60 seconds
        pam_1_power_device.start_stream("RawDataPam1.csv", stream_duration=STREAM_LENGTH)

        print("Stream started")

        #Waits stream_length
        visual_sleep(STREAM_LENGTH)

        #Stop PAM2 after Stream Length - trigger only syncs the start
        pam_2_power_device.send_command("RECord:STOP")

        print("Stream completed")

    else: #Use a software trigger
        #Simplest option - start them sequentially
        pam_1_power_device.start_stream("RawDataPam1.csv", stream_duration=STREAM_LENGTH)
        pam_2_power_device.start_stream("RawDataPam2.csv", stream_duration=STREAM_LENGTH)
        print("Streaming...")
        visual_sleep(STREAM_LENGTH+3)

        #This is a quicker way of starting the stream - Uses 2 CPU cores, that are kept busy, and the
        #pam command to start streaming is waiting to jump in - quicker but more complex
        #Uncomment this, and comment in the 2 lines above if wanting to use

        #SyncUtils.spin_cpu_and_start_stream(my_pam_1, my_pam_2, RESAMPLE_RATE, STREAM_LENGTH)

    #Stream is complete
    #Asks user if they want to combine data and display it in QPS
    post_process = showYesNoDialog(title="Post-process?", message="Do you want to combine and display the data in QPS?")
    #If no, exit the script
    if post_process == "No":
        exit(0)
    if post_process == "Yes":
        #If yes, combine the 2 csvs into 1
        #Combines the CSVs with a shared time column
        filelist = ["RawDataPam1.csv", "RawDataPam2.csv"]
        combined_csv_path = syncUtils.csv_combiner(filelist)

        #And then convert and open in QPS
        syncUtils.view_csv_in_qps(combined_csv_path, my_pam_1)


if __name__ == "__main__":
    main()
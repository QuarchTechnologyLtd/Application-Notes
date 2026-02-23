import multiprocessing
import os
import time
from datetime import datetime

import quarchpy
from quarchpy.device import quarchPPM
from quarchpy.qis import *
from quarchpy.qps import startLocalQps
from quarchpy.user_interface import showYesNoDialog, showDialog, visual_sleep
import SyncUtils


def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    #logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    print("*****************************************")
    print("*****************************************\n")
    print("AN-034 - Multiple PAM Synchronous Stream")
    print("Connect the devices over IP on the same network")
    print("\n*****************************************")
    print("*****************************************")

    if not isQisRunning():
        print("Starting QIS")
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
    # my_pam_1 = "USB:QTL2312-01-001"
    # my_pam_2 = "TCP:192.168.1.25"

    # Upgrades the PAMs to PPM devices - more features
    pam_1_power_device = quarchPPM(my_pam_1)
    pam_2_power_device = quarchPPM(my_pam_2)

    #Asks the user if they are using a hardware trigger
    hardware_trigger = showYesNoDialog(title="Are you using a triggering cable between the PAMs?", message="Yes if you are using a triggering cable between the PAMs")
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

        print("Trigger set-up")

        #Setups stream on PAM2, with the target CSV - waits on trigger
        pam_2_power_device.start_stream("RawDataPam2.csv")

        #Starts stream on PAM 1, which will fire the trigger on PAM2, with a length of 60 seconds
        pam_1_power_device.start_stream("RawDataPam1.csv", stream_duration=60)

        print("Stream started")

        #Waits stream_length
        visual_sleep(60)

        #Stop PAM2 after Stream Length - trigger only syncs the start
        pam_2_power_device.send_command("RECord:STOP")

        print("Stream completed")

    else: #Use a software trigger
        #Simplest option - start them sequentially - Highest delay
        my_pam_1.start_stream("RawDataPam1.csv", stream_duration=60)
        my_pam_2.start_stream("RawDataPam2.csv", stream_duration=60)

        #This is a quicker way of starting the stream - Uses 2 CPU cores, that are kept busy, and the
        #pam command to start streaming is waiting to jump in - significantly quicker
        #Uncomment this, and comment in the 2 lines above if wanting to use

        #spin_cpu_and_start_stream(pam_1_power_device, pam_2_power_device)

    #Stream is complete
    #Asks user if they want to combine data and display it in QPS
    post_process = showYesNoDialog(title="Post-process?", message="Do you want to combine and display the data in QPS?")
    #If no, exit the script
    if post_process == "No":
        exit(0)
    if post_process == "Yes":
        #If yes, combine the 2 csvs into 1
        #Combines the CSVs with a shared time column
        combined_csv = SyncUtils.csv_combiner("RawDataPam1.csv", "RawDataPam2.csv")

        #And then open in QPS
        SyncUtils.view_csv_in_qps(combined_csv)


def spin_cpu_and_start_stream(pam_1_power_device: quarchPPM, pam_2_power_device: quarchPPM):
    """
    Uses multiple CPU cores to keep busy, and then release at a set point, in effort to reduce the time needed to start stream

    :param pam_1_power_device: PAM1
    :param pam_2_power_device: PAM2

    Returns: None
    """
    # More complex but much quicker
    # Changes what clock is used depending on windows or posix
    clock_id = time.CLOCK_MONOTONIC if os.name == "POSIX" else None

    # Gets the current time in nanoseconds
    now = time.clock_gettime_ns(clock_id) if clock_id else time.time_ns()

    # 3 seconds in the future (in nanoseconds)
    target_ns = now + int(3 * 1e9)

    # Uses 1 core per PAM, keeps CPU busy until time starts
    #Passes in the PAM, file to save data to, and the time to spin until
    process1 = multiprocessing.Process(target=SyncUtils.spin_cpu_simple,
                                       args=(pam_1_power_device, "RawDataPam1.csv", target_ns))
    process2 = multiprocessing.Process(target=SyncUtils.spin_cpu_simple,
                                       args=(pam_2_power_device, "RawDataPam2.csv", target_ns))
    try:
        #Starts the process's activity
        process1.start()
        process2.start()

        #Blocks the main script until both processes are done
        process1.join()
        process2.join()

    #If user exits (e.g. Ctrl+C) safely close the processes)
    except KeyboardInterrupt:
        #Checks if alive
        if process1.is_alive():
            #Close the process
            process1.terminate()
        if process2.is_alive():
            process2.terminate()

        #Exit the script
        exit(0)


if __name__ == "__main__":
    main()
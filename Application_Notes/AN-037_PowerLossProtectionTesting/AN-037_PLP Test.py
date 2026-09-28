# Import other libraries used in the examples
import os
import time     # Used for sleep commands to add delays
import logging  # Optionally used to create a log to help with debugging

# Import the necessary components from the quarchpy library
import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.qps import *
from quarchpy.user_interface import *
from quarchpy.connection_specific.connection_QPS import QpsInterface

import pandas as pd #Used for finding when the drive drops off

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    requiredQuarchpyVersion("2.2.19")

    #Time to ramp over
    ramp_time = 5
    #Time we wait in between margining the rails for the drive to come back online
    power_up_time = 5

    print("Quarch application note example: AN-014 Triggering")
    print("---------------------------------------\n\n")

    #Checks if QPS is running on the local machine
    if not isQpsRunning():
    #If it is not already running, launch it
        print("Loading QPS..")
        my_qps = startLocalQps()
    #Else, if QPS is already running use that instance
    else:
        print("Using existing QPS..")
        #Connect to the existing instance
        my_qps = QpsInterface()

    # Module to work with
    print("\n-Requesting PPM selection")
    my_device_id = GetQpsModuleSelection(my_qps)

    #If you know the name of the module you would like to talk to, then comment out module selection and
    #hardcode the string using the serial number or IP address as shown below
    #my_device_id = "USB:QTL1999-06-127"
    #my_device_id = "TCP:10.0.8.100"

    # Create a Quarch device connected via QPS
    my_quarch_device = get_quarch_device(my_device_id, ConType="QPS")

    # Upgrade Quarch device to QPS device
    my_ppm = quarchQPS(my_quarch_device)
    #Open connection to the PPM
    my_ppm.open_connection()

    #Powers on PPM so drive can be detected
    my_ppm.send_command("RUN:POWer UP")

    #Returns the name of the PPM module
    print("Connected to: \n" + my_ppm.send_command("*IDN?"))

    #Checks if we have an intelligent fixture at 3V3
    conf_out = my_ppm.send_command("CONFig:OUTput:MODE?")

    #If we can't autodetect the fixture mode
    if conf_out == "NONE":
        print("Intelligent fixture not detected")
        #Asks the user to manually confirm if this is a 3V3 fixture
        fixture_3v3 = showYesNoDialog(title="",message="Is this a 3V3 fixture?")
        #If it is confirmed to be a 3V3 fixture
        if fixture_3v3 == "Yes":
            #Set the PPM to 3V3 mode
            my_ppm.send_command("CONFig:OUTput:MODE 3v3")
            print("3V3 mode set manually")

        else:#If this is a 5V fixture, exit the script as this is designed for 12V and 3V3
            print("This script is designed for PCIe devices with a 12V rail and a 3V3 rail, not a 5V rail")
            # Exit cleanly, close the PPM connection and QPS
            my_ppm.close_connection()
            closeQps()

            # Exit the script
            sys.exit(0)

    #Change the resampling rate to 100us
    my_ppm.send_command("stream mode resample 4us")

    #User selects test to perform

    #Create a folder called QPS Traces in the current working directory
    stream_path = os.path.join(os.getcwd(), "QPS_Traces")

    #Get the current time in the format YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")

    #Start stream
    my_stream = my_ppm.start_stream(os.path.join(stream_path, timestamp_stream_start))


    #Run the tests


    #Stop stream
    my_stream.stop_stream()

    # Exit cleanly, close the PPM connection and QPS
    my_ppm.close_connection()
    closeQps()

    #Exit the script
    sys.exit(0)

def voltage_margin(ppm, margin_12v, ramp_time_12v, margin_3v3, ramp_time_3v3, reset_time):
    """
    This function is to perform voltage margining to cause a brownout
    """
    #Sets the voltage channels to nominal, and clear any previous pattern
    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set rails to nominal
    ppm.send_command("SIGnal:12v:VOLTage 12000")
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    #If we are margining both rails
    if margin_12v and margin_3v3:
        # Wait 3 seconds before we start margining
        time.sleep(3)
        margin_both_rails(ppm, ramp_time_12v, ramp_time_3v3, reset_time)
    #Just 12V rail
    elif margin_12v:
        time.sleep(3)
        margin_12v_function(ppm, ramp_time_12v)
    #Just 3V3 rail
    elif margin_3v3:
        time.sleep(3)
        margin_3v3_function(ppm, ramp_time_3v3)

    print("Power rails reset to nominal, waiting for drive to come back online")
    visual_sleep(5)

def margin_12v_function(ppm, ramp_time):
    print("Margining 12V rail")

    # Load 12V Pattern
    # To ramp down -12V down to 0 over 5s
    ppm.send_command(f"SIGnal:12v:PATtern ADD {ramp_time}s -12000 i")

    # Wait 1 second for the pattern to be loaded
    time.sleep(1)

    # Run 12V pattern
    ppm.send_command("RUN:PATtern")

    # Pattern will run over ramp_time seconds (default 5), so after ramp_time + 2 second buffer) we will reset the rail to nominal
    visual_sleep(ramp_time + 2)
    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    # Set 12V to 12000mv (==12V)
    ppm.send_command("SIGnal:12v:VOLTage 12000")

    # We wait 1 second to ensure the PPM has reset
    time.sleep(1)

def margin_3v3_function(ppm, ramp_time):
    print("Margining 3V3 rail")

    # Load the 3V3 pattern
    ppm.sendCommand(f"SIGnal:3v3:PATtern ADD {ramp_time}s -3300 i")

    # Wait 1 second for the pattern to be loaded
    time.sleep(1)

    # Run the 3v3 pattern
    ppm.send_command("RUN:PATtern")

    # Pattern will run over ramp_time seconds, so after ramp_time + 2 second buffer we will reset the rail to nominal
    print("Margining 3V3 rail")
    visual_sleep(ramp_time + 2)

    # Clear any previous pattern
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set 3v3 to 3300mV
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    # We wait 1 second to ensure the PPM has reset
    time.sleep(1)

def margin_both_rails(ppm, ramp_time_12v, ramp_time_3v3, reset_time):
    print("Margining both rails")
    #Load the pattern for both 12V and 3V3
    ppm.send_command(f"SIGnal:12v:PATtern ADD {ramp_time_12v}s -12000 i")
    ppm.sendCommand(f"SIGnal:3v3:PATtern ADD {ramp_time_3v3}s -3300 i")

    time.sleep(1)

    ppm.send_command("RUN:PATtern")

    #Sleep for the higher of ramp_time + 2 seconds
    visual_sleep(max(ramp_time_12v,ramp_time_3v3) + 2)

    #Clear patterns
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")

    #Set rails back to nominal
    ppm.send_command("SIGnal:12v:VOLTage 12000")
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    # We wait 1 second to ensure the PPM has reset
    time.sleep(1)



if __name__== "__main__":
    main()
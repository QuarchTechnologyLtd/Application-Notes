"""
AN-014 - Application note demonstration the voltage margining with a PPM

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Runs a simple script for the PPM
- Capturing the power event using a data stream
- Pandas analysis to search for where the drive dropped off (Power is less than 50mW)

This is designed for PCIe CEM devices, and as such, the PCIe CEM spec is referenced, and is intended for a PCIe AIC fixture.
You can use the same host and control PC for this.

########### VERSION HISTORY ###########

21/05/2026 - Initial Version

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/


########### INSTRUCTIONS ###########

1- Install the required items above
2- Connect Power Injection Fixture, and the drive
3- Connect PPM to the PC
4- Run the script and follow the instructions on screen
5- Refer to AN-014 set-up section for an illustration

####################################
"""

# Import other libraries used in the examples
import os
import time     # Used for sleep commands to add delays
import logging  # Optionally used to create a log to help with debugging

# Import the necessary components from the quarchpy library
import quarchpy
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

    print("Quarch application note example: AN-014 Triggering")
    print("---------------------------------------\n\n")

    # Checks is QPS is running on the local machine
    if not isQpsRunning():
    #If it is not already running, launch it
        print("Loading QPS..")
        my_qps = startLocalQps(keepQisRunning=True)
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

    # Create a Quarch device connected via QPS
    my_quarch_device = get_quarch_device(my_device_id, ConType="QPS")

    # Upgrade Quarch device to QPS device
    my_qps_device = quarchQPS(my_quarch_device)
    #Open connection
    my_qps_device.open_connection()

    #Powers on PPM so drive can be detected
    my_qps_device.send_command("RUN:POWer UP")

    #Returns the name of the PPM module
    print("Connected to: \n" + my_qps_device.send_command("*IDN?"))

    #Checks if we have an intelligent fixture at 3V3
    conf_out = my_qps_device.send_command("CONFig:OUTput:MODE?")

    #If we can't autodetect the fixture mode
    if conf_out == "NONE":
        print("Intelligent fixture not detected")
        #Asks the user to manually confirm if this is a 3V3 fixture
        fixture_3v3 = showYesNoDialog(title="",message="Is this a 3V3 fixture?")
        #If it is confirmed to be a 3V3 fixture
        if fixture_3v3 == "Yes":
            #Set the PPM to 3V3 mode
            my_qps_device.send_command("CONFig:OUTput:MODE 3v3")
            print("3V3 mode set manually")

        else:#If this is a 5V fixture, exit the script as this is designed for 12V and 3V3
            print("This script is designed for PCIe devices with a 12V rail and a 3V3 rail, not a 5V rail")
            #Exit cleanly, close the PPM and QPS connection
            my_qps_device.close_connection()
            my_qps.closeConnection()
            sys.exit(0)

    #Change the resampling rate to 100us
    my_qps_device.send_command("stream mode resample 100us")

    #Enables pull down resistor on 3V3 channel - reduces floating
    my_qps_device.send_command("CONFig:OUT:3v3:PULLdown ON")

    #Sets the voltage channels to nominal, and clear any previous pattern
    reset_12v(my_qps_device)
    reset_3v3(my_qps_device)

    #Create a folder called QPS Traces in the current working directory
    stream_path = os.path.join(os.getcwd(), "QPS_Traces")

    #Get the current time in the format YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")

    #Start stream
    my_stream = my_qps_device.start_stream(os.path.join(stream_path, timestamp_stream_start))

    #Wait 5 seconds before we start margining
    time.sleep(5)

    print("Margining 12V rail")

    #Load 12V Pattern
    ramp_12v(my_qps_device)

    #Wait 1 second for the pattern to be loaded
    time.sleep(1)

    # Run 12V pattern
    my_qps_device.send_command("RUN:PATtern")

    #Pattern will run over 5 seconds, so after 7 seconds (2 second buffer) we will reset the rail to nominal
    visual_sleep(7)
    reset_12v(my_qps_device)

    #Wait 10 seconds for the drive to come back online.
    print("Power rail reset to nominal, waiting for drive to come back online")
    visual_sleep(10)

    #Load the 3V3 pattern
    ramp_3v3(my_qps_device)

    #Wait 1 second for the pattern to be loaded
    time.sleep(1)

    #Run the 3v3 pattern
    my_qps_device.send_command("RUN:PATtern")

    #Pattern will run over 5 seconds, so after 7 seconds (2 second buffer) we will reset the rail to nominal
    visual_sleep(7)
    reset_3v3(my_qps_device)

    #Stop stream
    my_stream.stop_stream()

    #Create the path of CSV
    csv_path = os.path.join(os.getcwd(), "stream_data.csv")

    #Save the data as a CSV, to the path we just made - used for pandas to calculate the data points
    my_stream.save_csv(csv_path)

    #Calls the function for pandas to check where the drive dropped offline
    drive_dropoff_12v, time_12v_dropoff, drive_dropoff_3v3, time_3v3_dropoff  = pandas_get_results(csv_path)

    response = None

    #Now, we will create the annotations in QPS for the voltage levels where we drop off
    while response != "OK":
        response = my_qps.sendCommand(f"$annotate {time_12v_dropoff} 12V Dropoff {drive_dropoff_12v}mV")
    while response != "OK":
        response = my_qps.sendCommand(f"$annotate {time_3v3_dropoff} 3V3 Dropoff {drive_dropoff_3v3}mV")

    print("QPS recording is now open, with annotations showing where the drive dropped off")
    print(f"\nWhen margining the 12V rail, the drive dropped off at {drive_dropoff_12v} mV")

    print(f"\nWhen margining the 3V3 rail, the drive dropped off at {drive_dropoff_3v3}")

    print("\nThe PCIe CEM specification Rev5, Table 4-1 provides the specifications for the power rail")
    print("The device must function as normal within the limits of the power rail")
    print("The 12V rail has a tolerance of 12V+/-8%. The lower limit of this is 11040mV")

    if drive_dropoff_12v < 11040:
        print("\nThe drive met the spec for the 12V rail")
    else:
        print("\nThe drive failed the specified tolerance for the 12V rail. It is suggested to re-run this test to confirm")

    print("\nThe 3V3 rail has a tolerance of 3.3V+/-9%. The lower limit of this is 3003mV")

    if drive_dropoff_3v3 < 3003:
        print("\nThe drive met the spec for the 3V3 rail")
    else:
        print("\nThe drive failed the specified tolerance for the 3V3 rail. It is suggested to re-run this test to confirm")

    print("Test complete, exiting script")

    # Exit cleanly, close the PPM and QPS connection
    my_qps_device.close_connection()
    my_qps.closeConnection()

    #Exit the script
    sys.exit(0)


def pandas_get_results(csv_path: str):
    """
    This opens the CSV that the stream data is saved to, scans through it to check for the first cell where the power is less than 1mW.
    We assume that any datapoint under 1mW means that the drive is idle.

    :params csv_path: The absolute path to the CSV that the stream data is exported to

    returns:
    voltage_12v_offline - the voltage of the 12V rail when the drive drops off
    time_12v_offline - the time of when the drive drops off
    voltage_3v3_offline - the voltage of the 3V3 rail when the drive drops off
    time_3v3_offline - the time of when the drive drops off
    """
    # Open the CSV as a pandas dataframe
    df = pd.read_csv(csv_path)

    # Get 12V voltage column
    col_12v_volt = df["12V voltage mV"]
    # Get 12V power column
    col_12v_power = df["12V power uW"]

    # Get 3V3 voltage column
    col_3v3_volt = df["3.3V voltage mV"]
    # Get 3V3 power column
    col_3v3_power = df["3.3V power uW"]

    #Get the time column
    col_time = df["Time uS"]

    # 1mW in uW. We will use this as the threshold of where the drive is off
    power_threshold = 1000

    # Scan through 12V power. Get the first cell where 12V power is under the threshold set
    rows_under_threshold = df[col_12v_power < power_threshold]

    # If we have some data that meets the criteria
    if not rows_under_threshold.empty:
        # Get the index of the first row meeting the threshold
        first_index = rows_under_threshold.index[0]

        #We check the index is more than 0, and adjust indexing by 1 to account for column names
        target_index = max(0, first_index - 1)

        # Store the 12v voltage when power meets the threshold
        voltage_12v_offline = col_12v_volt.loc[target_index]

        # Store the time when power meets the threshold
        time_12v_offline = col_time.loc[target_index]
        print("Found where drive dropped off")

    else:
        #If we don't have any rows matching the criteria, return None
        voltage_12v_offline = None
        time_12v_offline = None
        print(f"Warning: 12V power never dropped below 1mW.")

    #Scan through 3V3 power, store the rows where the threshold is met
    #We also lower the threshold to 100uW, as generally the 3V3 rail uses less power.
    power_threshold = 100

    #We check that the time is more than 22 seconds (stored in uS). This is the minimum time from the start of recording to margining the 3V3
    #This is to prevent a potential issue of where the 3v3 rail uses very little power, so we get false flags of the drive being offline before we margin the rail
    rows_under_threshold = df[(col_3v3_power < power_threshold) & (col_time > 22000000)]

    #If we have some data that meets the criteria
    if not rows_under_threshold.empty:
        #Get the index of the first row meeting the threshold
        first_index = rows_under_threshold.index[0]

        #We check the index is more than 0, and adjust indexing by 1 to account for column names
        target_index = max(0, first_index - 1)

        #Store the 3V3 voltage when power meets the threshold
        voltage_3v3_offline = col_3v3_volt.loc[target_index]

        #Store the time when power meets the threshold
        time_3v3_offline = col_time.loc[target_index]

        print("Found where drive dropped off")

    else:
        #If we don't have any rows matching the criteria, we will return None
        voltage_3v3_offline = None
        time_3v3_offline = None
        print(f"Warning: 3V3 power never dropped below 1mW.")

    return voltage_12v_offline, time_12v_offline, voltage_3v3_offline, time_3v3_offline

def reset_12v(my_ppm):
    """
    Clears any pattern and sets 12V channel to 12V
    :param my_ppm: PPM used in test
    :return: None
    """
    #Clear any previous pattern
    my_ppm.send_command("SIGnal:12v:PAT CLEAR")
    #Set 12V to 12000mv (==12V)
    my_ppm.send_command("SIGnal:12v:VOLTage 12000")

#Creates pattern with 12V on lower limit
def ramp_12v(my_ppm):
    """
    Creates a pattern for 12V to ramp down to 0 over 5000ms
    :param my_ppm: PPM used in test
    :return: None
    """
    #Pattern to ramp down -12V down to 0 over 5s
    my_ppm.send_command("SIGnal:12v:PATtern ADD 5s -12000 i")

#Clears any pattern and sets 3V3 channel to 3V3
def reset_3v3(my_ppm):
    """
    Clears any pattern and sets 3V3 channel to 3V3
    :param my_ppm: PPM used in test
    :return: None
    """
    #Clear any previous pattern
    my_ppm.send_command("SIGnal:3v3:PAT CLEAR")
    #Set 3v3 to 3300mV
    my_ppm.send_command("SIGnal:3v3:VOLTage 3300")


#Creates pattern with 3V3 ramping down to 0V
def ramp_3v3(my_ppm):
    """
    Creates a pattern for 3V3 to ramp down to 0 over 5s
    :param my_ppm: PPM used in test
    :return: None
    """
    reset_3v3(my_ppm)
    #Ramps down 3V3 to 0V over 5s
    my_ppm.sendCommand("SIGnal:3v3:PATtern ADD 5s -3300 i")


# Standard Python entry point. This ensures the main() function is called when the script is executed.
if __name__== "__main__":
    main()
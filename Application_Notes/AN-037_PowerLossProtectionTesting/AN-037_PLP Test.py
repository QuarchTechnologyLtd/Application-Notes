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

    #Test 1 - ramp around the threshold
    #Find the threshold of a brownout on both rails by margining each rail individually down to 0V over 5 seconds
    brownout_12v, brownout_3v3 = voltage_margin(my_ppm, 5000, 5000)

    #Now we have the thresholds, wait 5 seconds
    time.sleep(5)

    #Now we have the threshold



    # Exit cleanly, close the PPM connection and QPS
    my_ppm.close_connection()
    closeQps()

    #Exit the script
    sys.exit(0)

def ramp_at_brownout_threshold(ppm, brownout_threshold_12v, brownout_threshold_3v3):
    """
    We will use the PPM's patterns feature to ramp the voltage around the brownout threshold
    """
    #Start a stream, and start ramping PPM voltage.
    #Sets the voltage channels to nominal, and clear any previous pattern
    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set rails to nominal
    ppm.send_command("SIGnal:12v:VOLTage 12000")
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    #Create stream path in a folder called Threshold_Ramp_Test
    stream_path = os.path.join(os.getcwd(), "Threshold_Ramp_Test")
    #Get timestamp in YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")
    #Start stream and join the filepaths
    my_stream = ppm.start_stream(os.path.join(stream_path, timestamp_stream_start))

    #Starting value is 12V.
    #For example, say that brownout level 8V - We want to set voltage to 1V above threshold (9V), which in the pattern means a point of -3V
    # 12V - (brownout level - 1V) = 12V - (8V - 1V) = -3V
    ppm.send_command(f"SIGnal:12V:PAT ADD 20ms -{brownout_threshold_12v - 1000} i")
    #Pause for 5ms after we go to threshold + 1
    ppm.send_command(f"SIGnal:12V:PAT ADD 25ms 0 i")
    #Ramp to threshold -1V over 25ms
    ppm.send_command(f"SIGnal:12V:PAT ADD 50ms -{brownout_threshold_3v3 + 1000} i")
    #Expect PLP to have kicked in now. Wait 1 second before we reset the rail to 0 and then to 12V
    ppm.send_command(f"SIGnal:12V:PAT ADD 1s ")



    #Stop stream
    my_stream.stop_stream()


def voltage_margin(ppm,  ramp_time_12v, ramp_time_3v3):
    """
    This function is to perform voltage margining to cause a brownout.
    Also calls function to identify where the brownout threshold is
    """
    #Sets the voltage channels to nominal, and clear any previous pattern
    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set rails to nominal
    ppm.send_command("SIGnal:12v:VOLTage 12000")
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    #Create stream path in a folder called Brownout_Test
    stream_path = os.path.join(os.getcwd(), "Brownout_Test")
    #Get timestamp in YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")
    #Start stream and join the filepaths
    my_stream = ppm.start_stream(os.path.join(stream_path, timestamp_stream_start))

    #Run the tests
    time.sleep(3)
    margin_12v_function(ppm, ramp_time_12v)

    #Sleep 5 seconds before margining 3V3
    visual_sleep(5)

    margin_3v3_function(ppm, ramp_time_3v3)

    print("Power rails reset to nominal, waiting for drive to come back online")
    visual_sleep(10)

    #Stop stream
    my_stream.stop_stream()

    #Create the path of the CSV
    csv_path = os.path.join(os.getcwd(), "stream_data.csv")

    #Save stream data to the path we've just made
    my_stream.save_csv(csv_path)

    #Call the function to find the brownout threshold
    brownout_12v, brownout_3v3 = find_brownout_voltage(csv_path)

    return brownout_12v, brownout_3v3

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

def find_brownout_voltage(csv_path):
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

    #If we have some power data under the threshold
    if not rows_under_threshold.empty:
        # Get the index of the first row meeting the threshold
        first_index = rows_under_threshold.index[0]

        #We check the index is more than 0, and adjust indexing by 1 to account for column names
        target_index = max(0, first_index - 1)

        # Store the 12v voltage when power meets the threshold
        brownout_level_12v = col_12v_volt.loc[target_index]

    else:
        #If we don't have any rows matching the criteria, return None
        brownout_level_12v = None
        print(f"Warning: 12V power never dropped below 1mW.")

    # We check if 3V3 power is more than 1mW when we aren't margining (first 3 seconds)
    # If the power is less than 1mW, we cannot accurately determine where the drive drops off, if it drops off at all.
    # So we display a message explaining why we can't
    # Get the power cells where time is less than 3 seconds (in uS)
    idle_3v3_power = col_3v3_power[col_time <= 3000000]

    # Checks if mean 3V3 power in the first 3 seconds is less than 1mW.
    if idle_3v3_power.mean() <= power_threshold:
        print("\nThe 3V3 power never dropped below 1mW before we start margining.")
        print("We cannot accurately find where the drive drops off when margining the 3V3 rail")

        # Set the return variables to None
        brownout_level_3v3 = None

    else:  # The drive uses more than 1mW when idle, so we assume that we can find where the drive drops off
        # Get the cells where 3V3 power is under the threshold
        rows_under_threshold = df[(col_3v3_power < power_threshold)]

        # If we have some data that meets the criteria
        if not rows_under_threshold.empty:
            # Get the index of the first row meeting the threshold
            first_index = rows_under_threshold.index[0]

            # We check the index is more than 0, and adjust indexing by 1 to account for column names
            target_index = max(0, first_index - 1)

            # Store the 3V3 voltage when power meets the threshold
            brownout_level_3v3 = col_3v3_volt.loc[target_index]

        else:
            # If we don't have any rows matching the criteria, we will return 0
            brownout_level_3v3 = 0

            print(f"Warning: 3V3 power never dropped below 1mW.")

    # Return the voltage levels where we determine the drive dropped off
    return brownout_level_12v, brownout_level_3v3


if __name__== "__main__":
    main()
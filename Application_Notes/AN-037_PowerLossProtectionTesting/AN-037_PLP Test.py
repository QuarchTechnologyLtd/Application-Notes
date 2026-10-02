# Import other libraries used in the examples
import os
import time     # Used for sleep commands to add delays
import logging  # Optionally used to create a log to help with debugging
import tkinter  #Used for filepath selection for FIO loads
from tkinter import filedialog

# Import the necessary components from the quarchpy library
import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.qps import *
from quarchpy.user_interface import *
from quarchpy.connection_specific.connection_QPS import QpsInterface

import pandas as pd #Used for finding when the drive drops off

# This is how long we will wait for a drive to come back online after a test before we move on to the next test
# For NVMe drives this could probably be reduced, but to maximise compatibility default to 10 seconds
drive_reset_time = 10
#Length of the workloads
fio_write_time = "10"

# Store slew rates for crowbar testing here. Slew rates passed into the function are expected to be decimal values between 0 and 1.
# For ease of reading, we will store as *1000 so need to divide by 1000 before passing in. In effect, stored as mV/us which equals V/ms
crowbar_slew_rates = [
    [50, 500],
    [100, 300],
    [700, 200],
    [1000, 1000]]

# We use TK for the directory selection box, this code avoids additional TK GUI items being shown
root = tkinter.Tk()
tkFileDialog = filedialog
root.withdraw()



def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    #Check the user is running a relatively recent version of Quarchpy
    requiredQuarchpyVersion("2.2.23")

    #Displays the title as a list
    displayTable("AN-037 Power Loss Protection Tests", printToConsole=True, align="c")

    #Checks if QPS is running on the local machine
    if not isQpsRunning():
    #If it is not already running, launch it
        print("Launching QPS..")
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

    #Returns the name of the PPM module
    print("Connected to: \n" + my_ppm.send_command("*IDN?"))

    #Checks if we have an intelligent fixture at 3V3
    conf_out = my_ppm.send_command("CONFig:OUTput:MODE?")

    #If we can't autodetect the fixture mode
    if conf_out == "NONE" or conf_out == "DISABLED":
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

    #Powers on PPM so drive can be detected
    my_ppm.send_command("RUN:POWer UP")

    #Change the resampling rate to 4us - fastest we can sample on regular HD-PPM. For a MegaPPM, can change this to 1us
    my_ppm.send_command("stream mode resample 4us")

    print("\n>>> Select a folder for FIO Data:")
    # Request user to select the folder to use for FIO data
    try:
        testDirectory = tkFileDialog.askdirectory()
    except:
        testDirectory = input("Failed to open folder dialog, the enter the folder path for FIO to access\n>")

    if testDirectory == "":
        raise Exception("No directory selected")
    print("Selected : " + testDirectory)

    # FIO needs colons escaped when passing "directory" or "filename" look at FIO documentation online for more info.
    testDirectory = testDirectory.replace(":", "\:")  # escape colons from tkinter input.
    # testDirectory='D\\:/Copy stuff here/fioData:' #You could hardcode the path.

    #Test 1 - Ask the user if they know the threshold already. This will skip the test to find the threshold
    brownout_already_found = showYesNoDialog(title="Do you already know the brownout threshold for this drive?", message="Do you already know the brownout threshold for this drive?")
    if brownout_already_found == "Yes":
        brownout_12v = int(input("Please enter the brownout threshold for 12V in mV :"))
        brownout_3v3 = int(input("Please enter the brownout threshold for 3V3 in mV :"))
    else:
        #Threshold is not known
        print("Starting stream to find brownout threshold. This will be a separate stream to other testing")
        #Find the threshold of a brownout on both rails by margining each rail individually down to 0V over 5 seconds
        #This has its own separate stream because we need to export to CSV to find the threshold
        brownout_12v, brownout_3v3 = voltage_margin(my_ppm, 5000, 5000)

    #OPTIONAL - If you want to hardcode thresholds, comment out block of code above, and uncomment 2 lines below
    #brownout_12v = 8500
    #brownout_3v3 = 2600

    #Now we have the thresholds, wait 2 seconds before we start the stream
    time.sleep(2)
    print("Creating stream folders, and starting stream")

    configure_ramp_pattern = showYesNoDialog(title="Configure 12V ramp pattern?",message="Do you want to configure the ramp pattern? Selecting no will use script defaults")

    #Create stream path in a folder called Threshold_Ramp_Test
    stream_path = os.path.join(os.getcwd(), "Main_PLP_Tests")
    #Get timestamp in YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")
    #Start stream and join the filepaths
    my_stream = my_ppm.start_stream(os.path.join(stream_path, timestamp_stream_start))

    #Setup FIO load for later test
    fio_profiles = {
                    "write_idle" : {
                    "type": "idle",
                    "idle_seconds": fio_write_time},

                    "verify_idle": {
                    "type": "idle",
                    "idle_seconds": fio_write_time},

                    "write_4k" : {
                    "directory": "\"" + testDirectory + "\"",
                    "rw": "randwrite", #random write
                    "size": "1G",
                    "runtime": fio_write_time,
                    "direct" : "1", #Bypass OS RAM Cache
                    "sync" : "1", #Force drive to acknowledge each write
                    "verify": "crc32c",  # Verify the file load after each iteration of FIO write
                    "bs": "4k",
                    "time_based": "",  # This will force FIO to run for the time declared in runtime
                    "output": "testFile",  # Required output file, so we can parse it
                    "status-interval": "1",  # Update interval to add user data on the chart
                    "name": "4kRead"},

                    "verify_4k" : {
                    "directory": "\"" + testDirectory + "\"",
                    "rw": "read", #random write
                    "size": "1G",
                    "runtime": fio_write_time,
                    "direct": "1",
                    "bs": "4k",
                    "time_based": "",  # This will force FIO to run for the time declared in runtime
                    "output": "testFile",  # Required output file, so we can parse it
                    "status-interval": "1",  # Update interval to add user data on the chart
                    "verify": "crc32c", #Verify the file load after each iteration of FIO write
                    "name": "4kRead"},
    }

    #For each FIO load that we have (including an idle case)
    for fio_loads in fio_profiles:
        #Start FIO Load. There is an idle load so we can do

        #Start ramping around brownout threshold
        ramp_at_brownout_threshold(my_ppm, my_stream, brownout_12v, brownout_3v3, configure_ramp_pattern)

        #Sleep for 10 seconds while drive resets so we can be sure it is back online
        visual_sleep(drive_reset_time, title="Wait for drive to be online")

        #Run the crowbar tests
        run_crowbar_tests(my_ppm, my_stream, crowbar_slew_rates, brownout_12v, brownout_3v3)

    #Stop stream
    my_stream.stop_stream()

    # Exit cleanly, close the PPM connection and QPS
    my_ppm.close_connection()
    closeQps()

    #Exit the script
    sys.exit(0)

def apply_fio_load():
    pass

def run_crowbar_tests(ppm, stream, slew_rates, brownout_threshold_12v:int, brownout_threshold_3v3:int):
    """
    This function repeats a pattern of crowbars across both rails, both to ground, and down to brownout_threshold

    Parameters:
        ppm: PPM used in testing
        stream: Stream to be used in annotations
        slew_rates: List of slew rates used in the crowbar. Stored in mV/us = V/ms
        brownout_threshold_12v: Voltage on the 12V rail where the drive browns out
        brownout_threshold_3v3: Voltage on the 3v3 rail where the drive browns out
    """
    stream.add_annotation(title=f"Start of crowbar tests")

    #Assume we will crowbar one rail after the other, then change slew rates
    for rates in slew_rates:
        #Because the slew rates are stored as mV/us to read nicer, divide by 1000 to get V/us which is passed in to the function
        rate_down = rates[0] / 1000
        rate_up = rates[1] / 1000

        #Crowbar to ground
        crowbar_one_rail(ppm, "12V", rate_down, rate_up)
        stream.add_annotation(title="Crowbar test: 12V to Ground", extra_text=f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us.")
        visual_sleep(drive_reset_time, title="Crowbar 12V to Ground")

        crowbar_one_rail(ppm, "3V3", rate_down, rate_up)
        stream.add_annotation(title="Crowbar test: 3V3 to Ground", extra_text=f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us.")
        visual_sleep(drive_reset_time, title="Crowbar 3V3 to Ground")

        #Crowbar to brownout threshold
        crowbar_one_rail(ppm, "12V", rate_down, rate_up, brownout_threshold_12v)
        stream.add_annotation(title="Crowbar test: 12V to brownout",extra_text=f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us.")
        visual_sleep(drive_reset_time, title="Crowbar 12V down to brownout threshold")

        #Check we have a brownout_threshold for 3V3 before attempting to crowbar to brownout_threshold
        if brownout_threshold_3v3 != 0:
            crowbar_one_rail(ppm, "3V3", rate_down, rate_up)
            stream.add_annotation(title="Crowbar test: 3V3 to brownout",extra_text=f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us.")
            visual_sleep(drive_reset_time, title="Crowbar 3V3 down to brownout threshold")
        else:
            print("Skipping 3V3 crowbar down to brownout level as it wasn't found")

    stream.add_annotation(title=f"End of crowbar tests")

def crowbar_one_rail(ppm, rail:str, slew_rate_down:float, slew_rate_up:float, brownout_threshold:int = None):
    """
    This is a crowbar test to short a rail to ground or to brownout_threshold and back up very quickly. This is to simulate a screwdriver being dropped into the chassis
    We can vary the slew rates to see how fast PLP kicks in

    Parameters:
        ppm: PPM used in testing
        rail: Rail used in testing
        slew_rate_down: slew rate on the ramp down in V/us. e.g. entering 0.5 would be 0.5V/us. Max no load is 1V/us, so all must be decimals < 1
        slew_rate_up: slew rate on the ramp back up in V/us. e.g. entering 0.5 would be 0.5V/us. Max no load is 1V/us, so all must be decimals < 1
        brownout_threshold: If we want to crowbar to the brownout threshold instead of ground, pass the brownout threshold in
    """
    if rail.upper() == "12V":
        nominal_voltage = 12000
    elif rail.upper() == "3V3":
        nominal_voltage = 3300
    elif rail.upper() == "3V3_AUX":
        nominal_voltage = 3300
    else:
        print("Rail not recognised")
        nominal_voltage = None

    if slew_rate_down > 1.0:
        print("Slew rate down selected is faster than PPM can do with no load, setting 1V/us")
        slew_rate_down = 1.0

    if slew_rate_up > 1.0:
        print("Slew rate up selected is faster than PPM can do with no load, setting 1V/us")
        slew_rate_up = 1.0

    #Sets the voltage channel to nominal, and clear any previous pattern
    #Clear any previous pattern
    ppm.send_command(f"SIGnal:{rail}:PAT CLEAR")
    # Set rail to nominal
    ppm.send_command(f"SIGnal:{rail}:VOLTage {nominal_voltage}")
    #Enable the pulldown resistors so the voltage can fall much faster
    ppm.send_command(f"CONFig:OUTput:{rail}:PULLdown ON")

    #If we want to short to brownout_threshold, calculate the point on the pattern to be rail voltage - brownout threshold
    #So if 12V rail, and 8V rail, the point to fall to for patterns is -4000. Calculated here as a positive int, - is added in the command to the PPM
    if brownout_threshold is not None:
        voltage_to_fall = nominal_voltage - brownout_threshold
    else: # Crowbar to ground, so the rail voltage is what we need to drop
        voltage_to_fall = nominal_voltage

    #Calculate fall time. Convert nominal_voltage into Volts, multiplied by slew_rate.
    #e.g. if 12V crowbar to ground, with a slew rate of 0.5V/ms, fall_time = (12000/1000) * slew_rate = 12V / 0.5V/us = 24us
    fall_time_us = (voltage_to_fall / 1000) / slew_rate_down
    #Get fall_time and add "us" to the string so we can use in PPM command
    fall_time = str(fall_time_us) + "us"
    #Set point on rail to voltage_to_fall V (start at nominal, so need to go to -voltage_to_fall), fall_time seconds from the start of the pattern
    #Command will be similar to "SIGnal:12V:PATtern ADD 24us -12000 i"
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {fall_time} -{voltage_to_fall} i")

    #Calculate rise time
    rise_time_us = (voltage_to_fall / 1000) / slew_rate_up
    #Add the fall time and rise time together. Rise time must be later than fall time
    rise_time_us = rise_time_us + fall_time_us
    #Convert to string and add "us" for use in command
    rise_time = str(rise_time_us) + "us"
    #Set point on rail back to nominal. Start at nominal, so nominal has a pattern point of 0, rise_time after start of pattern
    #Command will be similar to "SIGnal:12V:PATtern ADD 60us 0 i"
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {rise_time} 0 i")

    #Sleep for 1 second after pattern is set
    time.sleep(1)

    #Run the pattern
    #ppm.send_command("RUN:PATtern")

    #Sleep for 1 second after the pattern is run. Assume most patterns are sub 100ms, with most likely being in us range.
    time.sleep(1)

def ramp_at_brownout_threshold(ppm, stream, brownout_threshold_12v:int, brownout_threshold_3v3:int, configure_ramp_pattern_yn:str):
    """
    We will use the PPM's patterns feature to ramp the voltage around the brownout threshold

    Parameters:
        ppm: PPM used in testing
        stream: Stream object used to place annotation
        brownout_threshold_12v: brownout threshold 12v
        brownout_threshold_3v3: brownout threshold 3v3
        configure_ramp_pattern_yn: configure 12v ramp pattern

    """
    #Sets the voltage channels to nominal, and clear any previous pattern
    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set rails to nominal
    ppm.send_command("SIGnal:12v:VOLTage 12000")
    ppm.send_command("SIGnal:3v3:VOLTage 3300")
    #Enable the pulldown resistors so the voltage can fall much faster
    ppm.send_command(f"CONFig:OUTput:12V:PULLdown ON")
    ppm.send_command(f"CONFig:OUTput:3V3:PULLdown ON")

    #Sleep for 1 second before we start creating the pattern
    time.sleep(1)

    #If user has selected to configure the pattern in the script, take the inputs
    if configure_ramp_pattern_yn == "Yes":
        threshold_jump_above_12v = int(input("Please enter the jump above brownout threshold for 12V in mV :"))
        threshold_jump_below_12v = int(input("Please enter the jump below brownout threshold for 12V in mV :"))
        timing_array_12v = input('Please enter the timing array for 12V in mV : \nStyle should be ["20ms", "25ms", "50ms", "75ms", "375ms"] :')
    else:
        #Use script default pattern
        #TODO - needs fine tuning
        threshold_jump_above_12v = 1000
        threshold_jump_below_12v = 700
        timing_array_12v = ["20ms", "25ms", "50ms", "75ms", "575ms"]

    #Create the pattern on 12V
    create_pattern_around_threshold(ppm, "12V", brownout_threshold_12v, threshold_jump_above_12v, threshold_jump_below_12v, timing_array_12v)

    #Checks if we have found brownout_threshold_3v3. If we've found brownout_threshold on 3V3 this will be non-zero
    if brownout_threshold_3v3 != 0:
        # If user has selected to configure the pattern in the script, take the inputs
        if configure_ramp_pattern_yn == "Yes":
            threshold_jump_above_3v3 = int(input("Please enter the jump above brownout threshold for 3V3 in mV :"))
            threshold_jump_below_3v3 = int(input("Please enter the jump below brownout threshold for 3V3 in mV :"))
            timing_array_3v3 = input('Please enter the timing array for 3V3 in mV : \nStyle should be ["20ms", "25ms", "50ms", "75ms", "375ms"] :')
        else:
            #Otherwise use script defaults
            #TODO - needs finetuning
            threshold_jump_above_3v3 = 400
            threshold_jump_below_3v3 = 200
            timing_array_3v3 = ["20ms", "25ms", "50ms", "75ms", "375ms"]

        create_pattern_around_threshold(ppm, "3V3", brownout_threshold_3v3, threshold_jump_above_3v3, threshold_jump_below_3v3, timing_array_3v3)

    #Create the annotation
    stream.add_annotation(title="Starting ramp around the brownout threshold")

    #ppm.send_command("RUN:PATtern")

    #General assumption - assume PPM pattern will be less than 2 seconds
    time.sleep(2)

    stream.add_annotation(title="Ending ramp around the brownout threshold")

    visual_sleep(drive_reset_time, title="Wait for drive to be online")

def create_pattern_around_threshold(ppm, rail, brownout_threshold:int, threshold_jump_above:int, threshold_jump_below:int, timing_array):
    """
    This is designed to create a pattern around a set threshold on a PPM.
    We want to ramp around the drive's brownout threshold. All points and voltage thresholds are configurable, but the overall pattern will remain the same

    The steps are designed as below
    1. We start at nominal voltage
    2. timing_array[0] seconds later, ramp down to brownout_threshold + threshold_jump_above
    3. Stay at (brownout_threshold + threshold_jump_above) for timing_array[1] seconds
    4. Ramp down to brownout_threshold timing_array[2] seconds after that - expect PLP to be on the edge of kicking in
    5. Ramp down to (brownout_threshold - threshold_jump_below) for timing_array[3] seconds - expect PLP to have kicked in
    6. Pause for timing_array[4] seconds
    7. Reset the rail to nominal

    For example. 12V rail, 8V is the brownout threshold, and we want to jump 1V up and down. timing_array = [20ms, 25ms, 50ms, 75ms, 575ms]
    1. Start at 12V
    2. 20ms later, ramp down to 9V
    3. Stay at 9V for a further 5ms (25ms total)
    4. Ramp down to 8V over 25ms (50ms total)
    5. Ramp down to 7V over 25ms (75ms total)
    6. Pause for 500ms at 7V
    7. 575ms after the start of the pattern, reset the 12V rail

    Parameters:
        ppm: The PPM to be used in test
        rail: Which voltage rail to margin
        brownout_threshold: The brownout threshold in mV
        threshold_jump_above: What level above brownout_threshold to jump
        threshold_jump_below: What level below brownout_threshold to jump
        timing_array: Array of timings in the format [Ams, Bms, Cms, Dms, Es]
    """
    if rail.upper() == "12V":
        nominal_voltage = 12000
    elif rail.upper() == "3V3":
        nominal_voltage = 3300
    elif rail.upper() == "3V3_AUX":
        nominal_voltage = 3300
    else:
        print("Rail not recognised")
        nominal_voltage = None

    #Step 2
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[0]} -{nominal_voltage - brownout_threshold + threshold_jump_above} i")
    #Step 3
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[1]} -{nominal_voltage - brownout_threshold + threshold_jump_above}")
    #Step 4
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[2]} -{nominal_voltage - brownout_threshold} i")
    #Step 5
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[3]} -{nominal_voltage - brownout_threshold - threshold_jump_below} i")
    #Step 6
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[4]}  -{nominal_voltage - brownout_threshold - threshold_jump_below}")
    #Step 7
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[4]} {nominal_voltage} i")

    print(f"Pattern on {rail} is created")
    #Once we've made the pattern, sleep for 1 second before we run the pattern to ensure its set
    time.sleep(1)

def voltage_margin(ppm,  ramp_time_12v:int, ramp_time_3v3:int):
    """
    This is essentially App Note 14 Voltage Margining. This function has its own stream because we need to export to CSV which can't be done real-time
    We export to CSV to find where the brownout threshold is.

    Parameters:
        ppm: The PPM to be used in test
        ramp_time_12v: The ramp_time_12v to be used in test
        ramp_time_3v3: The ramp_time_3v3 to be used in test

    Returns:
        brownout_12V: Brownout threshold for 12V rail
        brownout_3V3: Brownout threshold for 3V3 rail
    """
    #Sets the voltage channels to nominal, and clear any previous pattern
    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set rails to nominal
    ppm.send_command("SIGnal:12v:VOLTage 12000")
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    #Create stream path in a folder called Identify_Brownout_Level
    stream_path = os.path.join(os.getcwd(), "Identify_Brownout_Level")
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

    visual_sleep(drive_reset_time, title="Wait for drive to be online")

    #Stop stream
    my_stream.stop_stream()

    #Create the path of the CSV
    csv_path = os.path.join(os.getcwd(), "identify_brownout_level.csv")

    #Save stream data to the path we've just made
    my_stream.save_csv(csv_path)

    #Call the function to find the brownout threshold
    brownout_12v, brownout_3v3 = find_brownout_voltage(csv_path)

    return brownout_12v, brownout_3v3

def margin_12v_function(ppm, ramp_time:int):
    """
    Margin 12V down to 0V over ramp_time seconds
    Parameters:
        ppm: The PPM to be used in test
        ramp_time: The ramp_time to be used in test
    """
    print("Margining 12V rail")

    # Load 12V Pattern
    # To ramp down -12V down to 0 over 5s
    ppm.send_command(f"SIGnal:12v:PATtern ADD {ramp_time}s -12000 i")

    # Wait 1 second for the pattern to be loaded
    time.sleep(1)

    # Run 12V pattern
    #ppm.send_command("RUN:PATtern")

    # Pattern will run over ramp_time seconds (default 5), so after ramp_time + 2 second buffer) we will reset the rail to nominal
    visual_sleep(ramp_time + 2)
    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    # Set 12V to 12000mv (==12V)
    ppm.send_command("SIGnal:12v:VOLTage 12000")

    # We wait 1 second to ensure the PPM has reset
    time.sleep(1)

def margin_3v3_function(ppm, ramp_time:int):
    """
    Margin 12V down to 0V over ramp_time seconds
    Parameters:
        ppm: The PPM to be used in test
        ramp_time: The ramp_time to be used in test
    """
    print("Margining 3V3 rail")

    # Load the 3V3 pattern
    ppm.sendCommand(f"SIGnal:3v3:PATtern ADD {ramp_time}s -3300 i")

    # Wait 1 second for the pattern to be loaded
    time.sleep(1)

    # Run the 3v3 pattern
    #ppm.send_command("RUN:PATtern")

    # Pattern will run over ramp_time seconds, so after ramp_time + 2 second buffer we will reset the rail to nominal
    print("Margining 3V3 rail")
    visual_sleep(ramp_time + 2)

    # Clear any previous pattern
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set 3v3 to 3300mV
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    # We wait 1 second to ensure the PPM has reset
    time.sleep(1)

def find_brownout_voltage(csv_path):
    """Finds the voltage where the power rail reaches 0
    Parameters: CSV path of stream data
    Returns:
        brownout_12v, brownout_3v3: Brownout levels as integer millivolt values
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
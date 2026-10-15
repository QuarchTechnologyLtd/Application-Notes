"""
This is the main script for PLP tests. This holds most of the controls of the PPM, that may be useful to your own scripting.
fio_functions.py contains the relevant sections of AN-014 to find the brownout threshold as well as the direct commands to run the FIO operations and verify the FIO operations

We start by finding the threshold of where the drive will brownout, unless this is already known
Then, we start to ramp the voltage around the brownout threshold, to get PLP on the verge of kicking in.
Then, we crowbar the rails, both down to ground, and down to it's brownout threshold.

The aim of these tests is to cause PLP to kick in.
We perform these tests under idle, as well as under load, to check that we don't corrupt data in transit, and that the drive remaps correctly.
After each test we verify the data to check for data loss, and at the end give an overall pass/fail scenario
The ideal case is no data loss, and the drive remaps correctly after sudden power loss. This would show that the hardware and FW implementation of PLP is likely sufficient.

The parameters of the tests are configurable, and should be changed over different test runs to give a wide variety of tests.
This includes the timings of patterns, the steps in the pattern, and slew rates in the pattern.

fio_configs.json holds the FIO loads and verifies used to write data and then verify data from the drive

Note: The script must be run from a separate drive other than the DUT, as we expect the DUT to drop off

Requirements:
    Software:
        Python 3.14 or later
        Quarchpy v2.2.23 or later
        Pandas (in fio_functions.py)
        FIO - must be added to the path

    Hardware:
        Local control PC - either Windows or Linux
        Hot-pluggable system
        Enterprise drive with PLP implemented
        Quarch HD-PPM Plus (QTL1999, QTL1995) or MegaPPM (QTL3358) connected to the host PC via USB or LAN
        Relevant power Injection fixture
"""

# Import other libraries used in the examples
import os
import sys
import re
import subprocess
import time     # Used for sleep commands to add delays
import logging  # Optionally used to create a log to help with debugging
import tkinter  #Used for filepath selection for FIO loads
from tkinter import filedialog
import json #Used to store the FIO loads in a separate JSON file

import fio_functions #Stores FIO functions so mostly quarchpy control in this main script

# Import the necessary components from the quarchpy library
import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.qps import *
from quarchpy.user_interface import *
from quarchpy.connection_specific.connection_QPS import QpsInterface

# This is how long we will wait for a drive to come back online after a test before we move on to the next test
# For NVMe drives this could probably be reduced, but to maximise compatibility default to 20 seconds
drive_reset_time = 5

# Store slew rates for crowbar testing here. Slew rates passed into the function are expected to be decimal values between 0 and 1.
# For ease of reading, we will store as *1000 so need to divide by 1000 before passing in. In effect, stored as mV/us or V/ms
#[slew_down, slew_up]
crowbar_slew_rates = [
    [50, 50],
    [100, 100]
    # [700, 200],
    # [1000, 1000]
]

#Store the thresholds we jump above and below the threshold here. Stored in millivolts
#[jump_above_12v, jump_below_12v, jump_above_3v3, jump_below_3v3]
ramp_test_configurations = [
    [1000, 700, 400, 200],  # Test 1
    [800, 500, 300, 150]   # Test 2
    # [1200, 900, 500, 300],   # Test 3
    # [1500, 300, 100, 500]
]

# We use TK for the directory selection box, this code avoids additional TK GUI items being shown
root = tkinter.Tk()
root.attributes("-topmost", True) #Put the tab to the front of the screen
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
    print("This script must be run from a drive other than the DUT")

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

    my_ppm.send_command("CONFig:DEFault STATE")

    #Checks if we have an intelligent fixture at 3V3
    conf_out = my_ppm.send_command("CONFig:OUTput:MODE?")
    time.sleep(1)
    #If we can't autodetect the fixture mode
    if conf_out == "NONE" or conf_out == "DISABLED":
        print("Intelligent fixture not detected")
        #Asks the user to manually confirm if this is a 3V3 fixture
        fixture_3v3 = showYesNoDialog(title="",message="Is this a 3V3 fixture?")
        #If it is confirmed to be a 3V3 fixture
        if fixture_3v3 == "Yes":
            #Set the PPM to 3V3 mode
            my_ppm.send_command("CONFig:OUTput:MODE 3v3")
            time.sleep(2)
            print("3V3 mode set manually")

        else:#If this is a 5V fixture, exit the script as this is designed for 12V and 3V3
            print("This script is designed for PCIe devices with a 12V rail and a 3V3 rail, not a 5V rail")
            # Exit cleanly, close the PPM connection and QPS
            my_ppm.close_connection()
            closeQps()

            # Exit the script
            sys.exit(0)

    time.sleep(1)

    #Powers on PPM so drive can be detected
    response = my_ppm.send_command("RUN:POWer UP")
    print(f"RUN Power up command {response}")

    my_ppm.send_command("stream mode resample 16us")

    #Instead of using a standard directory, we need to target the drive path, because the drive will be dropping off and rebooting
    print("\n>>> Select the target drive or mount point for FIO Data:")

    #Optional hardcode. Uncomment this, and comment in block below to hardcode the drive path
    #selected_drive_path =  "D:/"

    #Request user to select the folder to use for FIO data
    try:
        selected_drive_path = tkFileDialog.askdirectory(parent=root, title="Select drive or mount point for FIO Data")
    except Exception as e:
        selected_drive_path = input(f"Failed to open folder dialog\nException: {e}\n, please enter the drive path (e.g. D:\\ for FIO to access\n>")

    if selected_drive_path == "":
        raise Exception("No drive selected")
    print("Selected : " + selected_drive_path)

    #Explicitly cast it as a string
    selected_drive_path = str(selected_drive_path)

    # Get timestamp in YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")
    #Create a timestamped folder for our FIO loads so that we target a new file every time. Otherwise FIO can reuse the same file and not perform any load
    folder_name = f"fio_tests{timestamp_stream_start}"

    #If Windows
    if os.name == "nt":
        #Get just the drive letter
        drive_path = os.path.splitdrive(selected_drive_path)[0]

        #If getting the drive letter has failed for any reason, raise exception
        if not drive_path:
            raise Exception(f"Could not determine drive letter from {selected_drive_path}")

        #Create D:\fio_tests. os.sep adds \\ for Windows
        test_directory = os.path.join(drive_path + os.sep, folder_name)
    #If Linux
    else:
        test_directory = os.path.join(selected_drive_path, folder_name)

    #If the filepath doesn't already exist
    if not os.path.exists(test_directory):
        #Make it
        os.makedirs(test_directory)

    #Create an escaped path
    if os.name == "nt":
        fio_directory = test_directory.replace(":", "\\:")
    else:
        fio_directory = test_directory

    #Attempt to open fio_configs.json storing the FIO loads both write and verify
    try:
        with open("fio_configs.json", "r") as f:
            #Cast it to a variable
            fio_profiles = json.load(f)
    except FileNotFoundError:
        print("Error: fio_configs.json not found")
        sys.exit(1)

    #Create a list and add the idle workloads
    fio_run_sequence = [
        {"is_loaded": False,
        "profile_name": "Idle",
        "write": fio_profiles["idle_config"]["write"],
        "verify": fio_profiles["idle_config"]["verify"]
    }]

    #Add the loaded workloads
    for load_profile in fio_profiles["loaded_configs"]:
        fio_run_sequence.append({
            "is_loaded": True,
            "profile_name": load_profile["name"],
            "write": load_profile["write"],
            "verify": load_profile["verify"]
        })

    #Test 1 - Ask the user if they know the threshold already. If known, this will skip the test to find the threshold
    brownout_already_found = showYesNoDialog(title="Do you already know the brownout threshold for this drive?", message="Do you already know the brownout threshold for this drive?")
    if brownout_already_found == "Yes":
        brownout_12v = int(input("Please enter the brownout threshold for 12V in mV :"))
        brownout_3v3 = int(input("Please enter the brownout threshold for 3V3 in mV :"))
    else:
        #Threshold is not known
        print("Starting stream to find brownout threshold. This will be a separate stream to other testing")
        #Find the threshold of a brownout on both rails by margining each rail individually down to 0V over 5 seconds
        #This has its own separate stream because we need to export to CSV to find the threshold
        brownout_12v, brownout_3v3 = fio_functions.voltage_margin(my_ppm, 5, 5, drive_reset_time)

    #OPTIONAL - If you want to hardcode thresholds, comment out block of code above, and uncomment 2 lines below
    # brownout_12v = 8500
    # brownout_3v3 = 2600

    #Now we have the thresholds, wait 2 seconds before we start the stream
    time.sleep(2)
    print("Creating stream folders, and starting stream")

    #Create stream path in a folder called Main_PLP_Tests in the current working directory
    stream_path = os.path.join(os.getcwd(), "Main_PLP_Tests")

    #Start stream and join the filepaths
    my_stream = my_ppm.start_stream(os.path.join(stream_path, timestamp_stream_start))

    #Start ramping around brownout threshold
    ramp_results = run_ramp_tests(my_ppm, my_stream, brownout_12v, brownout_3v3, ramp_test_configurations, test_directory, fio_run_sequence)

    #Pause in between tests
    visual_sleep(drive_reset_time, title="Switching tests, changing from ramp test to crowbar")

    #Run the crowbar tests
    crowbar_results = run_crowbar_tests(my_ppm, my_stream, crowbar_slew_rates, brownout_12v, brownout_3v3, test_directory, fio_run_sequence)

    #Sleep after the last test
    time.sleep(5)

    #Stop stream
    my_stream.stop_stream()

    # Exit cleanly, close the PPM connection, leave QPS recording open for viewing
    my_ppm.close_connection()

    #Combine the results from both tests
    all_results = ramp_results + crowbar_results
    #Start by setting overall pass to true
    overall_pass = True
    #Create an empty list to store failed tests
    failed_tests = []

    #For each test result we have
    for test_name, passed in all_results:
        #If we've passed, log status as PASS
        status = "PASS" if passed else "FAIL"
        #If one test has failed, logged the whole test as failed
        if not passed:
            overall_pass = False
            failed_tests.append(test_name)

    if overall_pass:
        print("\n***********************************************************************************")
        print("\nAll tests passed!")
        print("It is likely that your PLP implementation is sufficient to protect data integrity!")
        print("Consider re-running with different slew rates, parameters, and brownout thresholds\n")
        print("***********************************************************************************")

    else:
        #If one test or more has failed, print the details of the failure
        print("\n***********************************************************************************")
        print("\nTEST FAILED!")
        for failed_test in failed_tests:
            print(f"  - {failed_test}")
        print("It is likely that your PLP implementation is not wholly successful in this test")
        print("Consider re-running this test to confirm this\n")
        print("***********************************************************************************")

    #When QPS is closed, the script will close
    sys.exit(0)

def run_crowbar_tests(ppm, stream, slew_rates, brownout_threshold_12v:int, brownout_threshold_3v3:int, test_directory, run_sequence):
    """
    This function repeats a pattern of crowbars across both rails, both to ground, and down to brownout_threshold

    Parameters:
        ppm: PPM used in testing
        stream: Stream to be used in annotations
        slew_rates: List of slew rates used in the crowbar. Stored in mV/us = V/ms
        brownout_threshold_12v: Voltage on the 12V rail where the drive browns out
        brownout_threshold_3v3: Voltage on the 3v3 rail where the drive browns out
        test_directory: Drive path
        run_sequence: FIO loads loaded from an external JSON

    """
    stream.add_annotation(title=f"Start of crowbar tests")
    #Empty list to store test results
    test_results = []

    #Wrapper function inside to add the annotation
    def crowbar_with_annotation(ppm, rail, slew_down, slew_up, brownout, title, extra_text):
        stream.add_annotation(title=title, extra_text=extra_text)
        crowbar_one_rail(ppm, rail, slew_down, slew_up, brownout)

    #Assume we will crowbar one rail after the other, then change slew rates
    for rates in slew_rates:
        #Because the slew rates are stored as mV/us to read nicer, divide by 1000 to get V/us which is passed in to the function
        rate_down = rates[0] / 1000
        rate_up = rates[1] / 1000

        #For each idle case and loads
        for run_details in run_sequence:
            #Boolean - false if idle
            is_loaded = run_details["is_loaded"]
            #Get the profile name
            profile_name = run_details["profile_name"]
            #Get the write and verify arguments
            fio_write = run_details["write"]
            fio_verify = run_details["verify"]

            visual_sleep(drive_reset_time, title="Wait for drive to be stable")

            #Create the title
            test_1 = f"Crowbar_12V_to_GND_{profile_name}"
            result_1 = fio_functions.run_test_with_fio_load(
                test_1,test_directory, fio_write, fio_verify, is_loaded,
                crowbar_with_annotation, profile_name,
                ppm, "12V", rate_down, rate_up, None, f"Crowbar_12v_to_Ground_{profile_name}",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )
            test_results.append((test_1, result_1))

            visual_sleep(drive_reset_time, title="Wait for drive to be stable")

            test_2 =  f"Crowbar_3V3_GND_{profile_name}"
            result_2 = fio_functions.run_test_with_fio_load(
                test_2 ,test_directory, fio_write, fio_verify, is_loaded,
                crowbar_with_annotation, profile_name,
                ppm, "3V3", rate_down, rate_up, None, f"Crowbar_3v3_to_Ground_{profile_name}",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )
            test_results.append((test_2, result_2))

            visual_sleep(drive_reset_time, title="Wait for drive to be stable")

            test_3 = f"Crowbar_12V_Brownout_{profile_name}"
            result_3 = fio_functions.run_test_with_fio_load(
                test_3,test_directory, fio_write, fio_verify, is_loaded,
                crowbar_with_annotation, profile_name,
                ppm, "12V", rate_down, rate_up, brownout_threshold_12v, f"Crowbar_12v_to_Brownout_{profile_name}",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )
            test_results.append((test_3, result_3))

            visual_sleep(drive_reset_time, title="Wait for drive to be stable")

        #Check we have a brownout_threshold for 3V3 before attempting to crowbar to brownout_threshold
        if brownout_threshold_3v3 != 0:
            test_4 = f"Crowbar_3V3_Brownout_{profile_name}"
            result_4 = fio_functions.run_test_with_fio_load(
                test_4,test_directory, fio_write, fio_verify, is_loaded,
                crowbar_with_annotation, profile_name,
                ppm, "3V3", rate_down, rate_up, brownout_threshold_3v3, f"Crowbar_3v3_to_Brownout_{profile_name}",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )
            test_results.append((test_4, result_4))

            visual_sleep(drive_reset_time, title="Wait for drive to be stable")
        else:
            print("Skipping 3V3 crowbar down to brownout level as it wasn't found")

    stream.add_annotation(title=f"End of crowbar tests")
    return test_results

def crowbar_one_rail(ppm, rail:str, slew_rate_down:float, slew_rate_up:float, brownout_threshold:int = None):
    """
    This is a crowbar test to short a rail to ground or to brownout_threshold and back up very quickly. This is to simulate a screwdriver being dropped into the chassis or similar
    We can vary the slew rates to see how fast PLP kicks in. The rate set is unlikely to be exactly what is seen because the capacitance of each drive is different and will affect it.

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

    #Check that the slew rates are not faster than what we can do
    #We specify 1V/us with no load, in practice the slew rates are going to be much slower
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
    #So if 12V rail, and 8V brownout, the point to fall to for patterns is -4000. Calculated here as a positive int, - is added in the command to the PPM
    if brownout_threshold is not None:
        voltage_to_fall = nominal_voltage - brownout_threshold
    else: # Crowbar to ground, so the rail voltage is what we need to drop
        voltage_to_fall = nominal_voltage

    #Calculate fall time. Convert nominal_voltage into Volts, multiplied by slew_rate.
    #e.g. if 12V crowbar to ground, with a slew rate of 0.5V/ms, fall_time = (12000/1000) * slew_rate = 12V / 0.5V/us = 24us
    fall_time_us = (voltage_to_fall / 1000) / slew_rate_down
    #Round to integer and convert to string and add "us" for use in command
    fall_time = str(round(fall_time_us)) + "us"
    #Set point on rail to voltage_to_fall V (start at nominal, so need to go to -voltage_to_fall), fall_time seconds from the start of the pattern
    #Command will be similar to "SIGnal:12V:PATtern ADD 24us -12000 i"
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {fall_time} -{voltage_to_fall} i")

    #Calculate rise time
    rise_time_us = (voltage_to_fall / 1000) / slew_rate_up
    #Add the fall time and rise time together. Rise time must be later than fall time
    rise_time_us = rise_time_us + fall_time_us
    #Round to integer and convert to string and add "us" for use in command
    rise_time = str(round(rise_time_us)) + "us"
    #Set point on rail back to nominal. Start at nominal, so nominal has a pattern point of 0, rise_time after start of pattern
    #Command will be similar to "SIGnal:12V:PATtern ADD 60us 0 i"
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {rise_time} 0 i")

    visual_sleep(drive_reset_time, title="Wait for drive to be stable")

    #Sleep for 1 second after pattern is set
    time.sleep(1)

    #Run the pattern
    ppm.send_command("RUN:PATtern 1")

    #Sleep for 1 second after the pattern is run. Assume most patterns are sub 100ms, with most likely being in us range.
    time.sleep(1)

    ppm.send_command("SIGnal:12V:PATtern CLEAR")
    ppm.send_command("SIGnal:3V3:PATtern CLEAR")

def run_ramp_tests(ppm, stream, brownout_12v, brownout_3v3, ramp_configurations, test_directory, run_sequence):
    """
    Wrapper function to run ramp test around brownout thresholds
    """
    stream.add_annotation(title="Start of ramp tests")
    #Initialise an empty list for storing test results
    test_results = []
    for config in ramp_configurations:
        #Assign the jumps in the array to variables
        jump_above_12v = config[0]
        jump_below_12v = config[1]
        jump_above_3v3 = config[2]
        jump_below_3v3 = config[3]

        #For each FIO write/verify load
        for run_details in run_sequence:
            #Get the parameters
            is_loaded = run_details["is_loaded"]
            profile_name = run_details["profile_name"]
            fio_write = run_details["write"]
            fio_verify = run_details["verify"]

            test_name = f"Ramp_12V_A{jump_above_12v}_B{jump_below_12v}_{profile_name}"

            # Create the annotation
            print(stream.add_annotation(title=f"Starting ramp {profile_name}"))

            passed = fio_functions.run_test_with_fio_load(
                f"Ramp_Test_{profile_name}", test_directory, fio_write, fio_verify, is_loaded, ramp_at_brownout_threshold, profile_name,
                ppm, brownout_12v, brownout_3v3, jump_above_12v, jump_below_12v, jump_above_3v3, jump_below_3v3
            )

            #Append the test results to the list
            test_results.append((test_name, passed))

    stream.add_annotation(title="End of ramp tests")
    return test_results

def ramp_at_brownout_threshold(ppm, brownout_threshold_12v:int, brownout_threshold_3v3:int, jump_above_12v:int, jump_below_12v:int, jump_above_3v3:int, jump_below_3v3:int):
    """
    We will use the PPM's patterns feature to ramp the voltage around the brownout threshold

    Parameters:
        ppm: PPM used in testing
        brownout_threshold_12v: brownout threshold 12v
        brownout_threshold_3v3: brownout threshold 3v3
        jump_above_12v: threshold above 12v brownout to jump up
        jump_below_12v: threshold below 12v brownout to jump down
        jump_above_3v3: threshold above 3v3 brownout to jump up
        jump_below_3v3: threshold below 3v3 brownout to jump down
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

    timing_array_12v = ["20ms", "25ms", "50ms", "75ms", "575ms"]

    #Create the pattern on 12V
    create_pattern_around_threshold(ppm, "12V", brownout_threshold_12v, jump_above_12v, jump_below_12v, timing_array_12v)

    #Checks if we have found brownout_threshold_3v3. If we've found brownout_threshold on 3V3 this will be non-zero
    if brownout_threshold_3v3 != 0:
        timing_array_3v3 = ["20ms", "25ms", "50ms", "75ms", "375ms"]
        create_pattern_around_threshold(ppm, "3V3", brownout_threshold_3v3, jump_above_3v3, jump_below_3v3, timing_array_3v3)

    #Sleep for 1 second after annotation
    time.sleep(1)

    ppm.send_command("RUN:PATtern 1")

    #General assumption - assume PPM pattern will be less than 2 seconds
    time.sleep(5)

    #Reset the rails to nominal
    ppm.send_command("SIGnal:12V:VOLTage 12000")
    ppm.send_command("SIGnal:3V3:VOLTage 3300")

    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")

    visual_sleep(drive_reset_time, title="Wait for drive to be stable")

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
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[4]} 0 i")

    #Once we've made the pattern, sleep for 1 second before we run the pattern to ensure its set
    time.sleep(1)

if __name__== "__main__":
    main()
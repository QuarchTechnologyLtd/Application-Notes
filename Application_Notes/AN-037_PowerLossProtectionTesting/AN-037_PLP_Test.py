"""
AN-037 - Application Note testing PLP
Overview

This test is designed to test PLP implementation on enterprise SSDs with a Quarch Programmable Power Module.

This is the main script for PLP tests. This holds most of the controls of the PPM, that may be useful to your own scripting.
fio_functions.py contains the relevant sections of AN-014 to find the brownout threshold as well as the direct commands to run the FIO operations and verify the FIO operations

We start by finding the threshold of where the drive will brownout, unless this is already known. This is essentially AN-014 Voltage Margining.
Then, we start to ramp the voltage around the brownout threshold, to get PLP on the verge of kicking in.
Then, we crowbar the rails, both down to ground, and down to it's brownout threshold.

Our default patterns are in milliseconds, although microsecond range could be used, so we stream at 64us which gives sufficient resolution and should be able to stream on all PCs.
The PPM can slew upwards at 1V/us without a load, but with a drive connected the true slew rates are likely to be much slower, due to the capacitance of the drive.

With default configurations, the test will last for approximately 35 minutes

The aim of these tests is to cause PLP to kick in.
We perform these tests under idle, as well as under load, to check that we don't corrupt data in transit, and that the drive remaps correctly.
After each test we verify the data to check for data loss, and at the end give an overall pass/fail scenario

The ideal result is no data loss, and the drive remaps correctly after sudden power loss. This would show that the hardware and FW implementation of PLP is likely sufficient.

The parameters of the tests are configurable, and should be changed over different test runs to give a wide variety of tests.
These are stored as global variables so they are easy to spot and modify.

fio_configs.json holds the FIO loads and verifies used to write data and then verify data from the drive
The FIO load is designed for a Gen5 x4 link, but can be changed for different link widths and speeds

Note: The script must be run from a separate drive other than the DUT, as we expect the DUT to drop off
This script is developed for and tested on Linux only. Linux OS is much more tolerant to hotplugs compared to Windows, and drive paths are easier

########### VERSION HISTORY ###########
04/11/2026 - Andrew Steedman - First Release

########### REQUIREMENTS ###########
    Software:
        Python 3.14 or later
        Quarchpy v2.2.23 or later
        Pandas (used in fio_functions.py)
        FIO - must be added to the path

    Hardware:
        Quarch HD-PPM Plus (QTL1999, QTL1995) or MegaPPM (QTL3358) connected to the host PC via USB or LAN
        Linux PC - host PC is also control PC.
        Hot-pluggable system
        Enterprise drive with PLP
        Relevant power Injection fixture

########### INSTRUCTIONS ###########
1. Connect Power Injection Fixture to PPM
2. Connect Power Injection Fixture to drive
3. Connect Power Injection Fixture to Host
4. Power on the PPM
5. Power on the host
6. Ensure the drive shows under lsblk
7. Run AN-037_PLP_Test.py with administrator rights
"""

# Import other libraries used in the examples
import os
import sys
import re
import subprocess
import time     # Used for sleep commands to add delays
import logging  # Optionally used to create a log to help with debugging
import json     # Used to store the FIO loads in a separate JSON file
import csv      # Used to write any failed test data into a CSV

import fio_functions #Stores FIO functions so mostly quarchpy control in this main script

# Import the necessary components from the quarchpy library
import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.qps import *
from quarchpy.user_interface import *
from quarchpy.connection_specific.connection_QPS import QpsInterface

# This is how long we will wait for a drive to come back online after a test before we move on to the next test
# This could be increased or decreased depending on your specific drive
drive_reset_time = 10

# Store slew rates for crowbar testing here in mV/us. Slew rates passed into the function are expected to be decimal values between 0 and 1 so V/us.
#Higher number is faster, maximum is 1000 because PPM fastest no load slew rate is 1V/us
#[slew_down, slew_up]
crowbar_slew_rates = [
    [900, 10], #Fast down, slow up
    [20, 900] #Slow down, fast up
]

#Store the thresholds we jump above and below the threshold here. Stored in millivolts
#[jump_above_12v, jump_below_12v, jump_above_3v3, jump_below_3v3]
ramp_test_configurations = [
    [700, 2500, 400, 200],  # Test 1
    [800, 500, 300, 150],   # Test 2
    [2000, 2500, 600, 400]  # Test 3
]

#Ramp test timings
# This is time from the start of the pattern, so step 2 must be more than step 1 etc
#[12V timings], [3V3 timings]
ramp_test_timings = [
    (["25ms", "95ms", "120ms", "150ms", "575ms"], ["10ms", "35ms", "70ms", "80ms", "275ms"]),
    (["5ms", "10ms", "30ms", "50ms", "400ms"], ["100ms", "135ms", "170ms", "180ms", "575ms"])
]

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    #Check the user is running a relatively recent version of Quarchpy
    requiredQuarchpyVersion("2.2.23")

    if os.name == "nt":
        print("Windows is not supported on this App Note.")
        print("Windows is a lot less tolerant to Hot Plugs, even with a host-card/hot pluggable platform therefore it is not recommended")
        sys.exit(0)

    #Displays the title as a list
    displayTable("AN-037 Power Loss Protection Tests", printToConsole=True, align="c")
    print("********************* Instructions *********************")
    print("\nThis script must be run from a drive other than the DUT")
    print("The DUT and host must be hot-pluggable")
    print("The drive must be found under lsblk\n")

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
    #my_device_id = "TCP::QTL1999-06-127"
    #my_device_id = "TCP::10.0.8.100"

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
    time.sleep(1)
    #If we can't autodetect the fixture mode
    if conf_out == "NONE" or conf_out == "DISABLED":
        print("\nIntelligent fixture not detected")
        #Asks the user to manually confirm if this is a 3V3 fixture
        fixture_3v3 = showYesNoDialog(title="",message="Is this a 3V3 fixture?")
        #If it is confirmed to be a 3V3 fixture
        if fixture_3v3 == "Yes":
            #Set the PPM to 3V3 mode
            my_ppm.send_command("CONFig:OUTput:MODE 3v3")
            time.sleep(2)
            print("3V3 mode set manually")

        else:#If this is a 5V fixture, exit the script as this is designed for 12V and 3V3
            print("ERROR: This script is designed for PCIe devices with a 12V rail and a 3V3 rail, not a 5V rail")
            print("Exiting script...")
            # Exit cleanly, close the PPM connection and QPS
            my_ppm.close_connection()
            closeQps()

            # Exit the script
            sys.exit(0)

    #If auto-detected as a 5V fixture
    elif conf_out == "5V":
        print("\nERROR: 5V fixture auto-detected, exiting script")
        print("This script is designed for PCIe devices with a 12V rail and a 3V3 rail, not a 5V rail")
        print("Exiting script...")
        # Exit cleanly, close the PPM connection and QPS
        my_ppm.close_connection()
        closeQps()

        sys.exit(0)

    time.sleep(1)

    #Powers on PPM so drive can be detected
    if my_ppm.send_command("RUN:POWer?") == "DOWN":
        my_ppm.send_command("RUN:POWer UP")
        #Wait drive_reset_time before we start to look for the drive so we can be sure the drive is on line
        visual_sleep(drive_reset_time, title="Wait for drive to become online")
        time.sleep(drive_reset_time)

    #Set sample rate to 64us. You could use a faster sample rate, but this is a long stream so there is a lot of data
    #Default patterns are in millisecond range, so this is sufficient
    my_ppm.send_command("stream mode resample 64us")

    #Calls the drive selection function
    raw_device_path = select_nvme_target()

    #If no drive is selected, raise an Exception
    if not raw_device_path:
        raise Exception("No device path selected")

    # Get timestamp in YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")
    #Create a timestamped folder for our FIO loads so that we target a new file every time. Otherwise FIO can reuse the same file and not perform any load
    stream_path = os.path.join(os.getcwd(), f"Main_PLP_Tests_{timestamp_stream_start}")
    test_directory = os.path.join(stream_path, "fio_debug_files")

    #If the filepath doesn't already exist
    if not os.path.exists(test_directory):
        #Make the filepath
        os.makedirs(test_directory)

    #Attempt to open fio_configs.json storing the FIO loads both write and verify
    try:
        with open("fio_configs.json", "r") as f:
            #Cast it to a variable
            fio_profiles = json.load(f)
    except FileNotFoundError:
        print("Error: fio_configs.json not found")
        sys.exit(1)

    #Inject the drive path for idle workloads
    fio_profiles["idle_config"]["write"]["filename"] = raw_device_path
    fio_profiles["idle_config"]["verify"]["filename"] = raw_device_path

    # Initialise the sequence of FIO loads
    fio_run_sequence = [
        {"is_loaded": False,
         "profile_name": "Idle",
         "write": fio_profiles["idle_config"]["write"],
         "verify": fio_profiles["idle_config"]["verify"]
         }]

    # For each write operation we have
    for load_profile in fio_profiles["loaded_configs"]:
        # Inject the device path into each loaded workload
        load_profile["write"]["filename"] = raw_device_path
        load_profile["verify"]["filename"] = raw_device_path

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

    # #OPTIONAL - If you want to hardcode brownout thresholds, comment out block of code above, and uncomment 2 lines below
    #brownout_12v = 8500
    #brownout_3v3 = 0

    #Now we have the thresholds, wait 2 seconds before we start the stream
    time.sleep(2)
    print("Creating main stream folders, and starting stream...")

    #Calculate the number of tests there are to run so we can print this
    number_of_ramp_tests = len(ramp_test_configurations) * len(ramp_test_timings) * len(fio_run_sequence)

    #Multiply by 4 as we have 4 crowbar tests
    number_of_crowbar_tests = len(crowbar_slew_rates) * len(fio_run_sequence) * 4
    total_number_of_tests = number_of_ramp_tests + number_of_crowbar_tests
    test_counter = [1, total_number_of_tests]

    #Create stream path in a folder called Main_PLP_Tests_YY_MM_DD_HH_MM_SS in the current working directory
    stream_path = os.path.join(os.getcwd(), f"Main_PLP_Tests_{timestamp_stream_start}")

    #Start stream and join the filepaths
    my_stream = my_ppm.start_stream(os.path.join(stream_path, timestamp_stream_start))

    #Sleep for 5 seconds before we start testing
    time.sleep(5)

    #Start ramping around brownout threshold
    ramp_results = run_ramp_tests(my_ppm, my_stream, brownout_12v, brownout_3v3, ramp_test_configurations, ramp_test_timings, test_directory, fio_run_sequence, test_counter)

    #Pause in between tests
    visual_sleep(drive_reset_time, title="Changing tests, changing from ramp test to crowbar")

    #Run the crowbar tests
    crowbar_results = run_crowbar_tests(my_ppm, my_stream, crowbar_slew_rates, brownout_12v, brownout_3v3, test_directory, fio_run_sequence, test_counter)

    #Sleep after the last test so we don't cut off data too early
    time.sleep(5)

    print("Test Complete, summarising results...")

    #Stop stream
    my_stream.stop_stream()

    # Exit cleanly, close the PPM connection, leave QPS recording open for viewing
    my_ppm.close_connection()

    # Combine the results from both tests
    all_results = ramp_results + crowbar_results
    # Start by setting overall pass to true
    overall_pass = True
    # Create an empty list to store failed tests
    failed_tests = []

    for result in all_results:
        #Store the data in result as variables
        test_name, passed, kb_lost, parameters = result

        # If one test has failed, log the whole test as failed
        if not passed:
            overall_pass = False
            # Display the KB lost
            if kb_lost is not None and kb_lost > 0:
                failed_tests.append(f"{test_name} ({kb_lost:.1f} KB lost)")
            # If we failed but don't have a kb lost, print the general error
            else:
                failed_tests.append(f"{test_name} Failed: Data loss detected")

    #Print an overall pass/fail status
    if overall_pass:
        print("\n***********************************************************************************")
        print("\nAll tests passed!")
        print("It is likely that your PLP implementation is sufficient to protect data integrity!")
        print("Consider re-running with different slew rates, parameters, and brownout thresholds\n")
        print("***********************************************************************************")

    else:
        #If we have any failed tests, we will save the details of the failure into a CSV for the user to look at
        #Save test name, KB lost, and the test parameters into a timestamped csv
        results_csv_path = os.path.join(stream_path, f"CSV_Failed_Tests_{timestamp_stream_start}.csv")
        #Open the CSV
        with open(results_csv_path, mode="w", newline="") as csvfile:

            writer = csv.writer(csvfile)
            #Write the CSV titles
            writer.writerow(["Test Name", "Block Size", "Status", "KB Lost", "Parameters"])

            #For each result
            for result in all_results:
                test_name, passed, kb_lost, parameters = result
                status = "PASSED" if passed else "FAILED"

                #Get the load block size so we can save it to its own column
                if "Load_" in test_name:
                    block_size = test_name.split("_")[-1]
                else:
                    block_size = "N/A"

                writer.writerow([test_name, block_size, status, kb_lost, parameters])

        # If one test or more has failed, print the details of the failure
        print("\n***********************************************************************************")
        print("\nTEST FAILED!\n")
        for failed_test in failed_tests:
            print(f"{failed_test}")

        print(f"\nTest details and parameters saved to CSV file: {os.path.abspath(results_csv_path)}\n")
        print("It is likely that your PLP implementation is not wholly successful in this test")
        print("Consider re-running this test with the same parameters to confirm this\n")
        print("***********************************************************************************")

    #When QPS is closed, the script will close
    sys.exit(0)

def select_nvme_target():
    """Gets the NVMe drives on a system, get the specific unique ID, and display it to the user, and user selects the drive
    We need the specific unique ID as there is a chance that if /dev/nvme1 is selected, it can remount as e.g. /dev/nvme2

    Returns: Drive selected in the path format
    """
    #Get the list of drives found on the system
    by_id_dir = "/dev/disk/by-id/"
    #If this path doesn't exist, raise an error
    if not os.path.exists(by_id_dir):
        print("Error: /dev/disk/by-id/ directory not found")
        sys.exit(1)
    #Create an empty list of drives
    drives = []

    #For each drive found in /dev/disk/by-id/
    for link_name in os.listdir(by_id_dir):
        #For every actual drive, and not partition
        if link_name.startswith("nvme-") and "-part" not in link_name:
            #Get the full path
            full_path = os.path.join(by_id_dir, link_name)
            #Returns true if the path is an existing entry that is a symbolic link
            if os.path.islink(full_path):
                short_name = os.path.basename(os.readlink(full_path))
                #If this is the original drive, and not a duplicate entry
                if short_name.startswith("nvme") and not link_name.startswith("nvme-eui."):
                    #Get the Model and Size using lsblk (list partitions)
                    try:
                        lsblk_cmd = ["lsblk", "-d", "-n", "-o", "NAME,MODEL,SIZE", f"/dev/{short_name}"]
                        info = subprocess.check_output(lsblk_cmd, text=True).strip()
                    except subprocess.CalledProcessError:
                        info = f"{short_name} not found"

                    #If this is not a duplicate
                    if not any(drive['short_name'] == short_name for drive in drives):
                        #Append it to the list of drives
                        drives.append({"short_name": short_name,
                                       "persistent_path" : full_path,
                                       "display_info": info})
    if not drives:
        print("No NVMe drives found")
        sys.exit(1)

    #Separate the dictionary of drives into a comma separated string
    selection_string = ",".join([drive["display_info"] for drive in drives])

    #Take the users input in a list selection
    selected_drive = listSelection(title="", message="Please select the DUT", selectionList=selection_string, nice=True)
    print("\nIf the desired drive is not showing, reboot the host PC. The PPM is now powered up so the drive should show")

    #Get the persistent path from the list_selection choice
    path_map = {d['display_info']: d['persistent_path'] for d in drives}

    #If the path exists
    if selected_drive in path_map:
        #Get the full path
        actual_path = path_map[selected_drive]
    else:
        print("ERROR: Drive selected is not in path map.")
        sys.exit(1)

    print(f"Selected NVMe drive: {selected_drive}")
    return actual_path

def run_crowbar_tests(ppm, stream, slew_rates, brownout_threshold_12v:int, brownout_threshold_3v3:int, test_directory, run_sequence, test_counter):
    """
    This function repeats a pattern of crowbars across both rails, both to ground, and down to brownout_threshold

    Parameters:
        ppm: PPM used in testing
        stream: Stream to be used in annotations
        slew_rates: List of slew rates used in the crowbar. Stored in mV/us = V/ms
        brownout_threshold_12v: Voltage on the 12V rail where the drive browns out
        brownout_threshold_3v3: Voltage on the 3v3 rail where the drive browns out
        test_directory: Drive path
        run_sequence: FIO loads from an external JSON
        test_counter: Counter of test runs for printing to console
    """
    stream.add_annotation(title=f"Start of crowbar tests")
    #Empty list to store test results
    test_results = []

    #Wrapper function inside to add the annotation
    def crowbar_with_annotation(ppm, rail, slew_down, slew_up, brownout, title, extra_text):
        stream.add_annotation(title=(f"Test {test_counter[0]}/{test_counter[1]}:" + title), extra_text=extra_text)
        crowbar_one_rail(ppm, rail, slew_down, slew_up, brownout)

    #Assume we will crowbar one rail after the other, then change slew rates
    for rates in slew_rates:
        #Because the slew rates are stored as mV/us to read nicer, divide by 1000 to get V/us which is passed in to the function
        rate_down = rates[0] / 1000
        print(f"Slew rate down: {rate_down}")
        rate_up = rates[1] / 1000
        print(f"Slew rate up: {rate_up}")

        #For each idle case and loads
        for run_details in run_sequence:
            #Boolean - false if idle
            is_loaded = run_details["is_loaded"]
            #Get the profile name
            profile_name = run_details["profile_name"]
            #Get the write and verify arguments
            fio_write = run_details["write"]
            fio_verify = run_details["verify"]

            test_parameters = f"Slew down: {rate_down}, Slew up: {rate_up}"

            #Test 1
            base_test_1 = f"Crowbar_12V_to_GND_{profile_name}"
            # Display the test number
            display_test_1 = f"Test {test_counter[0]}/{test_counter[1]}: {base_test_1}"
            print(display_test_1)
            # Increment the counter
            test_counter[0] += 1

            #Test 1 - Call the FIO load, pass in the test parameters
            result_1, kb_lost1 = fio_functions.run_test_with_fio_load(
                base_test_1, test_directory, fio_write, fio_verify, is_loaded,
                crowbar_with_annotation, profile_name,
                ppm, "12V", rate_down, rate_up, None, f"Crowbar_12v_to_Ground_{profile_name}",
                f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )
            #Save the results of the test to a list
            test_results.append(
                (display_test_1, result_1, kb_lost1, test_parameters))

            #Test 2
            base_test_2 = f"Crowbar_3V3_GND_{profile_name}"
            display_test_2 = f"Test {test_counter[0]}/{test_counter[1]}: {base_test_2}"
            print(display_test_2)
            test_counter[0] += 1

            #Test 2
            result_2, kb_lost2 = fio_functions.run_test_with_fio_load(
                base_test_2, test_directory, fio_write, fio_verify, is_loaded,
                crowbar_with_annotation, profile_name,
                ppm, "3V3", rate_down, rate_up, None, f"Crowbar_3v3_to_Ground_{profile_name}",
                f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )
            test_results.append((display_test_2, result_2, kb_lost2, test_parameters))

            #Test 3
            base_test_3 = f"Crowbar_12V_Brownout_{profile_name}"
            display_test_3 = f"Test {test_counter[0]}/{test_counter[1]}: {base_test_3}"
            print(display_test_3)
            test_counter[0] += 1

            #Test 3
            result_3, kb_lost3 = fio_functions.run_test_with_fio_load(
                base_test_3, test_directory, fio_write, fio_verify, is_loaded,
                crowbar_with_annotation, profile_name,
                ppm, "12V", rate_down, rate_up, brownout_threshold_12v, f"Crowbar_12v_to_Brownout_{profile_name}",
                f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )

            test_results.append((display_test_3, result_3, kb_lost3, test_parameters))

            #Check that 3V3 brownout threshold is non zero
            if brownout_threshold_3v3 != 0:
                #Test 4
                base_test_4 = f"Crowbar_3V3_Brownout_{profile_name}"
                display_test_4 = f"Test {test_counter[0]}/{test_counter[1]}: {base_test_4}"
                print(display_test_4)
                test_counter[0] += 1

                result_4, kb_lost4 = fio_functions.run_test_with_fio_load(
                    base_test_4, test_directory, fio_write, fio_verify, is_loaded,
                    crowbar_with_annotation, profile_name,
                    ppm, "3V3", rate_down, rate_up, brownout_threshold_3v3, f"Crowbar_3v3_to_Brownout_{profile_name}",
                    f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
                )
                test_results.append((display_test_4, result_4, kb_lost4, test_parameters))
            else:
                print("Skipping 3V3 brownout crowbar test as threshold wasn't found")

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

    #Sleep for FIO command to build
    time.sleep(5)

    #Check that the slew rates are not faster than what we can do
    #We specify 1V/us upwards with no load, in practice the slew rates are going to be much slower due to the capacitance of the drive
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

    #Sleep for 1 second after pattern is set
    time.sleep(1)

    #Run the pattern
    ppm.send_command("RUN:PATtern 1")

    #Sleep for 1 second after the pattern is run. Assume most patterns are sub 100ms, with most likely being in us range.
    time.sleep(1)

    #Wait for the drive to come back online
    visual_sleep(drive_reset_time, title="Wait for drive to be stable")

    ppm.send_command("SIGnal:12V:PATtern CLEAR")
    ppm.send_command("SIGnal:3V3:PATtern CLEAR")

def run_ramp_tests(ppm, stream, brownout_12v, brownout_3v3, ramp_configurations, timing_array, test_directory,  run_sequence, test_counter):
    """
    Wrapper function to run ramp test around brownout thresholds

    Parameters:
        ppm: PPM used in testing
        stream: Stream object used to place annotations
        brownout_12v: Brownout 12V
        brownout_3v3: Brownout 3V3
        ramp_configurations: voltage above or below thresholds to jump
        timing_array: timing array of the pattern
        test_directory: FIO target
        run_sequence: list of FIO configs
        test_counter: test counter
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

        #For each timing we have
        for timings in timing_array:
            timings_12v, timings_3v3 = timings

            #For each FIO write/verify load
            for run_details in run_sequence:
                #Get the parameters
                is_loaded = run_details["is_loaded"]
                profile_name = run_details["profile_name"]
                fio_write = run_details["write"]
                fio_verify = run_details["verify"]

                #Print the test name and counter to console
                test_name = f"Test {test_counter[0]}/{test_counter[1]}: Ramp_12V_A{jump_above_12v}_B{jump_below_12v}_{profile_name}"
                print(test_name)

                # Create the annotation
                stream.add_annotation(title=f"Test {test_counter[0]}/{test_counter[1]}: Starting ramp {profile_name}")
                #Increment the counter
                test_counter[0] += 1

                #Run the FIO load with the test parameters
                passed, kb_lost = fio_functions.run_test_with_fio_load(
                    f"Ramp_Test_{profile_name}", test_directory, fio_write, fio_verify, is_loaded, ramp_at_brownout_threshold, profile_name,
                    ppm, brownout_12v, brownout_3v3, jump_above_12v, jump_below_12v, jump_above_3v3, jump_below_3v3, timings_12v, timings_3v3
                )

                test_parameters = f"12V Jumps: +{jump_above_12v}mV/-{jump_below_12v}mV | 3V3 Jumps: +{jump_above_3v3}mV/-{jump_below_3v3}mV"

                #Append the test results to the list
                test_results.append((test_name, passed, kb_lost, test_parameters))

    stream.add_annotation(title="End of ramp tests")
    return test_results

def ramp_at_brownout_threshold(
        ppm, brownout_threshold_12v:int, brownout_threshold_3v3:int,
        jump_above_12v:int, jump_below_12v:int, jump_above_3v3:int,
        jump_below_3v3:int, timing_array_12v:list, timing_array_3v3:list):
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
        timing_array_12v: Array of timings for the 12V rail
        timing_array_3v3: Array of timings for the 3V3 rail
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

    #Create the pattern on 12V
    create_pattern_around_threshold(ppm, "12V", brownout_threshold_12v, jump_above_12v, jump_below_12v, timing_array_12v)

    #Checks if we have found brownout_threshold_3v3. If we've found brownout_threshold on 3V3 this will be non-zero
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
    Add or remove steps as you prefer, timing_array index must match the test steps as shown

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

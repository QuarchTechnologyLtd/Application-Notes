"""
Separate file to store functions related directly to FIO, so the main file can be kept for Quarchpy functions
This includes most of the FIO functions as we aren't using Quarchpy.FIO because it's blocking
Also includes AN-014 Voltage Margining as it has it's own separate app note so it's less important to be visible
"""

import os
import time
import subprocess
import re

import pandas as pd
from quarchpy.user_interface import visual_sleep

def wait_and_poll_drive_remount(target_directory, drive_reset_time=10):
    """
    Polls drive presence at 1Hz, for up to drive_reset_time, default is 10s.
    Parameters:
        target_directory (str): Folder located on the drive
        drive_reset_time (int): Timeout in seconds for the drive to come back online
    """
    print("Waiting for drive to be remounted")
    start_time = time.time()
    while True:
        #Check if the path exists
        if os.path.exists(target_directory):
            print("Drive has remounted, progressing to next step")
            time.sleep(1)
            return True
        if (time.time() - start_time) > drive_reset_time:
            print(f"TIMEOUT: Drive did not remount within {drive_reset_time} seconds")
            return False
        #Sleep so we don't poll too fast
        time.sleep(1)

def parse_fio_verify(fio_verify_output_str, block_size, test_name, load_name):
    """
    Take in the output from FIO verify operation, and parse it looking for errors
    Parameters:
        fio_verify_output_str: Console output from FIO verify operation
        block_size: Block size for the operation so we can calculate how many kilobytes have been lost.
        test_name: Name of the test for printing to console
        load_name: Name of the FIO load for printing to console
    """
    # Use regex to split the number and the unit (e.g., "4k" -> "4" and "k", "1M" -> "1" and "M")
    size_match = re.match(r'^(\d+)([a-zA-Z]*)$', str(block_size).strip())
    #If we're able to split it
    if size_match:
        #Assign the number to group 1 and cast as an integer
        block_size_num = int(size_match.group(1))
        #Assign the multiplier in upper case
        multiplier = size_match.group(2).upper()

        #Compare the first index of the multiplier to calculate the multiplier we need. e.g. KB would enter this statement
        if multiplier[0] == "K":
            #Keep the block size in KB as itself
            block_size_kb = block_size_num
        #If Megabyte block size, then multiply by 1024
        elif multiplier[0] == "M":
            block_size_kb = block_size_num * 1024
        #If Gigabyte block size
        elif multiplier[0] == "G":
            block_size_kb = block_size_num * 1024 * 1024
        #If no multiplier divide by 1024 to get KB
        elif multiplier[0] == "B" or multiplier[0] == "":
            block_size_kb = block_size_num / 1024
        else:
            print(f"[{test_name}] Unrecognized unit '{multiplier}' in block size '{block_size}'. Defaulting to KB.")
            block_size_kb = block_size_num

    else:
        print(f"Invalid block size format {block_size}")
        block_size_kb = 0

    # Use regex to find the 'errors: total=X' line
    match = re.search(r"errors\s*:\s*total=(\d+)", fio_verify_output_str)

    #If there is an errors: total line
    if match:
        #Get the error count
        total_errors = int(match.group(1))
        #Multiply by the block size
        data_lost_kb = total_errors * block_size_kb

        #If we've found errors, and they are more than 0
        if total_errors > 0:
            print(f"PLP FAILED on {test_name}: Drive lost {data_lost_kb} KB of data.\n")
            return data_lost_kb
        #This means that errors: total=0 is in the output string, so no errors detected
        else:
            print(f"PLP PASSED on {test_name}: No errors detected.\n")
            return 0
    #If there's no errors: total line, we can't detect if there are actually errors
    else:
        print(f"PLP PASSED on {test_name}: No errors detected.\n")
        return 0

def run_test_with_fio_load(test_name, test_directory, fio_write_load, verify_write, is_loaded, plp_test, load_name, *plp_test_arguments):
    """
    Executes a single complete PLP cycle
    Apply FIO load
    Start PLP test
    Wait for drive to re-appear
    Verify load
    Parameters:
        test_name: Name of the test
        test_directory: Directory for FIO load
        fio_write_load: FIO write load
        verify_write: Verify load
        is_loaded: Boolean. False if idle, true if under load
        load_name: Name of the FIO load for printing console and annotations
        plp_test: Crowbar or ramp
    """

    #Start by running the FIO load passed in
    #Format the string for use on command line
    cmd_name = f"--name={test_name.replace(' ', '_')}"
    cmd_write = ["fio", cmd_name]

    # For each key value pair in fio_write_load
    for k, v in fio_write_load.items():
        # Append --key if value is empty, otherwise append --key=value
        cmd_write.append(f"--{k}" if v == "" else f"--{k}={v}")

    # Force FIO to write its console output directly to a text file locally
    cmd_write.append(f"--output=fio_debug_{test_name.replace(' ', '_')}.txt")

    if is_loaded:
        fio_write = subprocess.Popen(cmd_write, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=test_directory)
        #Sleep 2 seconds to build the FIO command
        time.sleep(2)

    else:
        #If this is an idle test load, we will start by writing a small file before we perform the test to verify it
        print(f"{load_name} Writing small file prior to idle tests")
        subprocess.run(cmd_write, capture_output=True)

    print(f"{load_name} Starting PLP Test...\b")
    plp_test(*plp_test_arguments)

    if is_loaded:
        #This will wait here until the drive drops off and FIO stops
        fio_write.communicate()
        print(f"{test_name} Drive dropped off, FIO load ended")

    #Wait for the drive to come back on line by polling it
    if not wait_and_poll_drive_remount(test_directory):
        print("FAILED: Drive did not remount in time")
        return False

    #Once the drive is back online, we start the verify workload
    cmd_verify = ["fio", cmd_name]
    for k, v in verify_write.items():
        cmd_verify.append(f"--{k}" if v == "" else f"--{k}={v}")

    print("Verifying drive data to check for data loss")
    result = subprocess.run(cmd_verify, capture_output=True, text=True, cwd=test_directory)

    # Parse results, pass in the block size to calculate how many kb lost
    kb_lost = parse_fio_verify(result.stdout, fio_write_load["bs"], test_name, load_name)

    #After we verify, wait for the drive to return to idle
    visual_sleep(10, title="Wait for drive to be stable")

    #If kb_lost is 0, return True.
    return kb_lost == 0

def voltage_margin(ppm, ramp_time_12v:int, ramp_time_3v3:int, drive_reset_time=10):
    """
    This is essentially App Note 14 Voltage Margining. This function has its own stream because we need to export to CSV which can't be done real-time
    We export to CSV to find where the brownout threshold is.
    Stored in a separate file because this is already detailed on AN-014

    Parameters:
        ppm: The PPM to be used in test
        ramp_time_12v: The ramp_time_12v to be used in test
        ramp_time_3v3: The ramp_time_3v3 to be used in test
        drive_reset_time: Timeout for drive to come back online

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

    # Clear any previous pattern
    ppm.send_command("SIGnal:12v:PAT CLEAR")
    # Set 12V to 12000mv (==12V)
    ppm.send_command("SIGnal:12v:VOLTage 12000")

    # Load 12V Pattern
    # To ramp down -12V down to 0 over 5s
    ppm.send_command(f"SIGnal:12v:PATtern ADD {ramp_time}s -11998 i")

    # Wait 1 second for the pattern to be loaded
    time.sleep(1)

    # Run 12V pattern
    ppm.send_command("RUN:PATtern 1")

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

    # Clear any previous pattern
    ppm.send_command("SIGnal:3v3:PAT CLEAR")
    # Set 3v3 to 3300mV
    ppm.send_command("SIGnal:3v3:VOLTage 3300")

    # Load the 3V3 pattern
    ppm.send_command(f"SIGnal:3v3:PATtern ADD {ramp_time}s -3300 i")

    # Wait 1 second for the pattern to be loaded
    time.sleep(1)

    # Run the 3v3 pattern
    ppm.send_command("RUN:PATtern 1")

    # Pattern will run over ramp_time seconds, so after ramp_time + 2 second buffer we will reset the rail to nominal
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
        brownout_level_12v = int(input("Could not detect the threshold of where the drive dropped off. Please enter the 12V threshold in millivolts : \n"))

    # We check if 3V3 power is more than 1mW when we aren't margining (first 3 seconds). This is an arbitrary threshold so could be changed
    # If the power is less than 1mW, we cannot accurately determine where the drive drops off, if it drops off at all.
    # So we display a message explaining why we can't
    # Get the power cells where time is less than 3 seconds (in uS)
    idle_3v3_power = col_3v3_power[col_time <= 3000000]

    # Checks if mean 3V3 power in the first 3 seconds is less than 1mW.
    if idle_3v3_power.mean() <= power_threshold:
        print("\nThe 3V3 power never dropped below 1mW before we start margining.")
        print("We cannot accurately find where the drive drops off when margining the 3V3 rail")

        # Set the return variables to None
        brownout_level_3v3 = int(input("Could not detect the brownout threshold. Please enter the 3V3 threshold in millivolts : \n"))

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
            brownout_level_3v3 = int(input("Could not detect the brownout threshold. Please enter the 3V3 threshold in millivolts : \n"))

            print(f"Warning: 3V3 power never dropped below 1mW.")

    # Return the voltage levels where we determine the drive dropped off
    return brownout_level_12v, brownout_level_3v3
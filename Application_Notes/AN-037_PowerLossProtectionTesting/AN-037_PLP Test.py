# Import other libraries used in the examples
import os
import sys
import re
import subprocess
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
# For NVMe drives this could probably be reduced, but to maximise compatibility default to 20 seconds
drive_reset_time = 5
#Length of the workloads
fio_write_time = "5"

# Store slew rates for crowbar testing here. Slew rates passed into the function are expected to be decimal values between 0 and 1.
# For ease of reading, we will store as *1000 so need to divide by 1000 before passing in. In effect, stored as mV/us or V/ms
#[slew_down, slew_up]
crowbar_slew_rates = [
    [50, 50],
    [100, 100],
    [700, 200],
    [1000, 1000]]

#Store the thresholds we jump above and below the threshold here. Stored in millivolts
#[jump_above_12v, jump_below_12v, jump_above_3v3, jump_below_3v3]
ramp_test_configurations = [
    [1000, 700, 400, 200],  # Test 1
    [800, 500, 300, 150],   # Test 2
    [1200, 900, 500, 300],   # Test 3
    [1500, 300, 100, 500]
]


# We use TK for the directory selection box, this code avoids additional TK GUI items being shown
root = tkinter.Tk()
root.attributes("-topmost", True)
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
    #my_device_id = GetQpsModuleSelection(my_qps)

    #If you know the name of the module you would like to talk to, then comment out module selection and
    #hardcode the string using the serial number or IP address as shown below
    my_device_id = "USB:QTL1999-06-127"
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

    #Change the resampling rate to 4us - fastest we can sample on regular HD-PPM. For a MegaPPM, change this to 1us
    my_ppm.send_command("stream mode resample 4us")

    #Instead of using a standard directory, we need to target the drive path, because the drive will be dropping off and rebooting
    print("\n>>> Select the target drive or mount point for FIO Data:")
    selected_drive_path =  "D:/"
    # Request user to select the folder to use for FIO data
    # try:
    #     selected_drive_path = tkFileDialog.askdirectory(parent=root, title="Select drive or mount point for FIO Data")
    # except Exception as e:
    #     selected_drive_path = input(f"Failed to open folder dialog\nException: {e}\n, please enter the drive path (e.g. D:\\ for FIO to access\n>")

    if selected_drive_path == "":
        raise Exception("No drive selected")
    print("Selected : " + selected_drive_path)

    #Explicitly cast it as a string
    selected_drive_path = str(selected_drive_path)

    #If Windows
    if os.name == "nt":
        #Get just the drive letter
        drive_path = os.path.splitdrive(selected_drive_path)[0]

        #If getting the drive letter has failed for any reason, raise exception
        if not drive_path:
            raise Exception(f"Could not determine drive letter from {selected_drive_path}")

        #Create D:\fio_tests. os.sep adds \\ for Windows
        test_directory = os.path.join(drive_path + os.sep, "fio_tests")
    #If Linux
    else:
        test_directory = os.path.join(selected_drive_path, "fio_tests")

    # FIO needs colons escaped when passing "directory" or "filename" look at FIO documentation online for more info.
    fio_directory = test_directory.replace(":", "\:")  # escape colons from tkinter input.
    # drive_path='D\\:/Copy stuff here/fioData:' #You could hardcode the path.

    # #Test 1 - Ask the user if they know the threshold already. If known, this will skip the test to find the threshold
    # brownout_already_found = showYesNoDialog(title="Do you already know the brownout threshold for this drive?", message="Do you already know the brownout threshold for this drive?")
    # if brownout_already_found == "Yes":
    #     brownout_12v = int(input("Please enter the brownout threshold for 12V in mV :"))
    #     brownout_3v3 = int(input("Please enter the brownout threshold for 3V3 in mV :"))
    # else:
    #     #Threshold is not known
    #     print("Starting stream to find brownout threshold. This will be a separate stream to other testing")
    #     #Find the threshold of a brownout on both rails by margining each rail individually down to 0V over 5 seconds
    #     #This has its own separate stream because we need to export to CSV to find the threshold
    #     brownout_12v, brownout_3v3 = voltage_margin(my_ppm, 5000, 5000)

    #OPTIONAL - If you want to hardcode thresholds, comment out block of code above, and uncomment 2 lines below
    brownout_12v = 8500
    brownout_3v3 = 2600

    #Ask the user if they want to configure the ramp pattern or use the script defaults
    #configure_ramp_pattern = showYesNoDialog(title="Configure 12V ramp pattern?",message="Do you want to configure the ramp pattern? Selecting no will use script defaults")
    configure_ramp_pattern = "No"

    #Now we have the thresholds, wait 2 seconds before we start the stream
    time.sleep(2)
    print("Creating stream folders, and starting stream")

    #Create stream path in a folder called Main_PLP_Tests in the current working directory
    stream_path = os.path.join(os.getcwd(), "Main_PLP_Tests")
    #Get timestamp in YYMMDD-HHMMSS
    timestamp_stream_start = time.strftime("%Y_%m_%d-%H_%M_%S")
    #Start stream and join the filepaths
    my_stream = my_ppm.start_stream(os.path.join(stream_path, timestamp_stream_start))

    fio_write_config = {
        "directory": fio_directory,
        "filename": "test.dat",
        "rw": "randwrite",
        "size": "100M",
        "runtime": fio_write_time,
        "direct" : "1",
        "sync" : "1",
        "verify": "crc32c",
        "bs": "4k",
        "time_based": "",
        "do_verify": "0",
        "verify_state_save": "1",  # CRITICAL for PLP
        "thread": "1"
    }

    fio_verify_config = {
        "directory": fio_directory,
        "filename": "test.dat",
        "rw": "randread",
        "size": "100M",
        "direct": "1",
        "bs": "4k",
        "verify": "crc32c",
        "verify_state_load": "1",  # CRITICAL for PLP
        "verify_fatal": "0",
        "continue_on_error": "verify",  # Force full block count
        "thread": "1"
    }

    #Start ramping around brownout threshold
    for ramp_config in ramp_test_configurations:
        run_ramp_test(my_ppm, my_stream, brownout_12v, brownout_3v3, ramp_config[0], ramp_config[1], ramp_config[2], ramp_config[3], test_directory, fio_write_config, fio_verify_config)
        # Pause in between tests
        visual_sleep(drive_reset_time, title="Wait for drive to be stable")

    #Pause in between tests
    visual_sleep(drive_reset_time, title="Wait for drive to be online")

    #Run the crowbar tests
    run_crowbar_tests(my_ppm, my_stream, crowbar_slew_rates, brownout_12v, brownout_3v3, test_directory, fio_write_config, fio_verify_config)

    #Sleep after the last test
    time.sleep(5)

    #Stop stream
    my_stream.stop_stream()

    # Exit cleanly, close the PPM connection, leave QPS recording open
    my_ppm.close_connection()

    #Exit the script
    sys.exit(0)

def wait_and_poll_drive_remount(target_directory):
    """
    Polls drive presence at 1Hz, for up to drive_reset_time, default is 20s.
    Parameters:
        target_directory (str): Folder located on the drive
    """
    print("Waiting for drive to be remounted")
    start_time = time.time()
    while True:
        #Check if the path exists
        if os.path.exists(target_directory):
            print("Drive has remounted")
            time.sleep(1)
            return True
        if (time.time() - start_time) > drive_reset_time:
            print(f"TIMEOUT: Drive did not remount within {drive_reset_time} seconds")
            return False
        #Sleep so we don't poll too fast
        time.sleep(1)

def run_test_with_fio_load(test_name, test_directory, fio_write_load, verify_write, plp_test, *plp_test_arguments):
    """
    Executes a single complete PLP cycle
    Apply FIO load
    Start PLP test
    Wait for drive to re-appear
    Verify load
    """

    #Start by running the FIO load passed in
    #Format the string for use on command line
    cmd_write = ["fio", f"--name={test_name.replace(' ', '_')}"]
    #For each key value pair in fio_write_load
    for k, v in fio_write_load.items():
        #Append --key if value is empty, otherwise append --key=value
        cmd_write.append(f"--{k}" if v == "" else f"--{k}={v}")

    print("Starting FIO Write Workload...")
    #Run the command to start the FIO load
    fio_write = subprocess.Popen(cmd_write, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # Give FIO time to build up the IO queue

    #Run the PLP test with the arguments passed in
    print(f"Running PLP Test: {test_name}")
    plp_test(*plp_test_arguments)

    #At some point the drive will drop off, so we wait
    fio_write.communicate()
    print("Drive dropped off, ending load.")

    #Wait for the drive to come back on line by polling it
    if not wait_and_poll_drive_remount(test_directory):
        print("Skipping verify phase because drive is inaccessible.")
        return

    #Once the drive is back online, we start the verify workload
    cmd_verify = ["fio", f"--name={test_name.replace(' ', '_')}"]
    for k, v in verify_write.items():
        cmd_verify.append(f"--{k}" if v == "" else f"--{k}={v}")

    print("Verifying drive data to check for data loss")
    result = subprocess.run(cmd_verify, capture_output=True, text=True)

    # Parse results, pass in the block size to calculate how many kb lost
    parse_fio_verify(result.stdout, fio_write_load["bs"], test_name)

def parse_fio_verify(fio_verify_output_str, block_size, test_name):
    """
    Take in the output from FIO verify operation, and parse it looking for errors
    Parameters:
        fio_verify_output_str: Console output from FIO verify operation
        block_size: Block size for the operation so we can calculate how many kilobytes have been lost.
        test_name: Name of the test for printing to console
    """
    if block_size.upper() == "4K":
        block_size_num = 4
    elif block_size.upper() == "16k":
        block_size_num = 16
    else:
        print("Invalid block size")
        block_size_num = None

    # Use regex to find the 'errors: total=X' line
    match = re.search(r"errors\s*:\s*total=(\d+)", fio_verify_output_str)

    #If there is an errors: total line
    if match:
        #Get the error count
        total_errors = int(match.group(1))
        #Multiply by the block size
        data_lost_kb = total_errors * block_size_num

        #If we've found errors, and they are more than 0
        if total_errors > 0:
            print(f"PLP FAILED on {test_name}: Drive lost {total_errors} blocks ({data_lost_kb} KB of data).")
            return data_lost_kb
        #This means that errors: total=0 is in the output string, so no errors detected
        else:
            print(f"PLP PASSED on {test_name}: No errors detected.")
            return 0
    #If there's no errors: total line, we can't detect if there are actually errors
    else:
        print(f"PLP PASSED on {test_name}: No errors detected.")
        return 0

def run_crowbar_tests(ppm, stream, slew_rates, brownout_threshold_12v:int, brownout_threshold_3v3:int, test_directory, fio_write, fio_verify):
    """
    This function repeats a pattern of crowbars across both rails, both to ground, and down to brownout_threshold

    Parameters:
        ppm: PPM used in testing
        stream: Stream to be used in annotations
        slew_rates: List of slew rates used in the crowbar. Stored in mV/us = V/ms
        brownout_threshold_12v: Voltage on the 12V rail where the drive browns out
        brownout_threshold_3v3: Voltage on the 3v3 rail where the drive browns out
        test_directory: Drive path
        fio_write: FIO Write operation
        fio_verify: FIO Verify operation

    """
    stream.add_annotation(title=f"Start of crowbar tests")

    #Wrapper function inside to add the annotation
    def crowbar_with_annotation(ppm, rail, slew_down, slew_up, brownout, title, extra_text):
        crowbar_one_rail(ppm, rail, slew_down, slew_up, brownout)
        stream.add_annotation(title=title, extra_text=extra_text)

    #Assume we will crowbar one rail after the other, then change slew rates
    for rates in slew_rates:
        #Because the slew rates are stored as mV/us to read nicer, divide by 1000 to get V/us which is passed in to the function
        rate_down = rates[0] / 1000
        rate_up = rates[1] / 1000

        run_test_with_fio_load(
            f"Crowbar_12V_GND_D{rates[0]}_U{rates[1]}",test_directory, fio_write, fio_verify,
            crowbar_with_annotation,
            ppm, "12V", rate_down, rate_up, None, "Crowbar_12v_Ground_Load",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
        )

        run_test_with_fio_load(
            f"Crowbar_3V3_GND_D{rates[0]}_U{rates[1]}",test_directory, fio_write, fio_verify,
            crowbar_with_annotation,
            ppm, "3V3", rate_down, rate_up, None, "Crowbar_3v3_Ground_Load",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
        )

        run_test_with_fio_load(
            f"Crowbar_12V_Brownout_D{rates[0]}_U{rates[1]}",test_directory, fio_write, fio_verify,
            crowbar_with_annotation,
            ppm, "12V", rate_down, rate_up, brownout_threshold_12v, "Crowbar_12v_Brownout_Load",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
        )

        #Check we have a brownout_threshold for 3V3 before attempting to crowbar to brownout_threshold
        if brownout_threshold_3v3 != 0:
            run_test_with_fio_load(
                f"Crowbar_3V3_Brownout_D{rates[0]}_U{rates[1]}",test_directory, fio_write, fio_verify,
                crowbar_with_annotation,
                ppm, "3V3", rate_down, rate_up, brownout_threshold_3v3, "Crowbar_3v3_Brownout_Load",f"Slew rate down: {rates[0]}mV/us.\n Slew rate up: {rates[1]}mV/us."
            )
        else:
            print("Skipping 3V3 crowbar down to brownout level as it wasn't found")

    stream.add_annotation(title=f"End of crowbar tests")

def crowbar_one_rail(ppm, rail:str, slew_rate_down:float, slew_rate_up:float, brownout_threshold:int = None):
    """
    This is a crowbar test to short a rail to ground or to brownout_threshold and back up very quickly. This is to simulate a screwdriver being dropped into the chassis or similar
    We can vary the slew rates to see how fast PLP kicks in. The rate set is unlikely to be exactly what is seen because the load of each drive is different and will affect it.

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

    ppm.send_command("SIGnal:12V:PATtern CLEAR")
    ppm.send_command("SIGnal:3V3:PATtern CLEAR")

def run_ramp_test(ppm, stream, brownout_12v, brownout_3v3, jump_above_12v, jump_below_12v, jump_above_3v3, jump_below_3v3, test_directory, write_config, verify_config):
    """
    Wrapper function to run ramp test around brownout thresholds
    """
    test_name = f"Ramp_Brownout_12V_A{jump_above_12v}_B{jump_below_12v}"

    run_test_with_fio_load(
        test_name, test_directory, write_config, verify_config, ramp_at_brownout_threshold,
        ppm, stream, brownout_12v, brownout_3v3, jump_above_12v, jump_below_12v, jump_above_3v3, jump_below_3v3
    )

def ramp_at_brownout_threshold(ppm, stream, brownout_threshold_12v:int, brownout_threshold_3v3:int, jump_above_12v:int, jump_below_12v:int, jump_above_3v3:int, jump_below_3v3:int):
    """
    We will use the PPM's patterns feature to ramp the voltage around the brownout threshold

    Parameters:
        ppm: PPM used in testing
        stream: Stream object used to place annotation
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

    #Sleep for 1 second while pattern is created
    time.sleep(1)

    #Create the annotation
    stream.add_annotation(title="Starting ramp around the brownout threshold")
    #Sleep for 1 second after annotation
    time.sleep(1)

    ppm.send_command("RUN:PATtern 1")

    #General assumption - assume PPM pattern will be less than 2 seconds
    time.sleep(2)

    stream.add_annotation(title="Ending ramp around the brownout threshold")

    #Reset the rails to nominal
    ppm.send_command("SIGnal:12V:VOLTage 12000")
    ppm.send_command("SIGnal:3V3:VOLTage 3300")

    ppm.send_command("SIGnal:12v:PAT CLEAR")
    ppm.send_command("SIGnal:3v3:PAT CLEAR")

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
    ppm.send_command(f"SIGnal:{rail}:PATtern ADD {timing_array[4]} 0 i")

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
    ppm.send_command("RUN:PATtern")

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
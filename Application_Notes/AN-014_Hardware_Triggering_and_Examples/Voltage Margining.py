"""
AN-014 - Application note demonstration the voltage margining with a PPM

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Runs a simple script for the PPM
- Capturing the power event using a data stream


########### VERSION HISTORY ###########

06/01/2025 - Andrew S - operation review, and changes made

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- QuarchQCS Python package - No licence needed, using library funcs
    https://pypi.org/project/quarchqcs/
3- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/
5- If using Windows 11 install WMIC
    Windows Settings > Search "WMIC" and install
6- If using Linux install LS SCSI and SmartCTL


########### INSTRUCTIONS ###########

1- Install the required items above
2- Connect Power Injection Fixture, and the drive
3- Connect PPM to control PC
4- Connect Power cables to PPM
5- Run the script and follow the instructions on screen
6- Refer to AN-014 set-up section for an illustration

####################################
"""

# Import other libraries used in the examples
import os
import subprocess
import datetime
import time     # Used for sleep commands to add delays
import logging  # Optionally used to create a log to help with debugging
import re          #Used for REGEX

#Used to only get digits of the output of ppm meas volt 12v/3v3?
REGEX_PATTERN = r"\D+"

# Import the necessary components from the quarchpy library
#from quarchpy.connection_specific.connection_QIS import QisInterface
# '.device' provides connection and control of modules
import quarchpy
from quarchpy.device import *
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.user_interface import *
from QuarchpyQCS.hostInformation import HostInformation
from QuarchpyQCS.Drive_wrapper import  *

#Local file where the python script is stored
base_directory = str(os.path.dirname(os.path.realpath(__file__)))

#Names a folder for outputs of script to go
data_folder_name = "VoltageMarginingOutputs"

#Specifies datapath explicitly in the local folder where script is stored
data_path = os.path.join(base_directory, data_folder_name)

#Creates the directory for output data, dont overwrite if already exists
os.makedirs(data_path, exist_ok=True)

#StreamPath is where the QPS Trace is stored.
#Stored within the local folder
stream_path = os.path.join(data_path, "QPS Trace")

#Log file path is used for logging
#E.G. logFile_25-12-03-12-00-00.txt
#Explicitly local time
log_file_path = os.path.join(data_path, "logFile_" + time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + " .txt")

#Calls HostInformation constructor - used for drive polling
my_host_info = HostInformation()


def main():
    #Sets up logging file - has both QIS logs, and script logs
    logging.basicConfig(filename=log_file_path, level=logging.DEBUG,
                        format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
                        datefmt="%H:%M:%S")

    #Checks if user has administrative rights
    admin_os_check()

    print("Quarch application note example: AN-014 Triggering")
    print("---------------------------------------\n\n")

    #Starts QPS
    print("Loading QPS")
    log_write("Loading QPS")

    # Checks is QPS is running on the localhost
    if not isQpsRunning():
    # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps(keepQisRunning=True)
        log_write("QPS Already running")

    # Open an interface to local QPS
    my_qps = qpsInterface()

    # Module to work with
    print("\n-Requesting PPM selection")
    my_device_id = GetQpsModuleSelection(my_qps)
    log_write("User selected PPM")

    # Create a Quarch device connected via QPS
    my_quarch_device = get_quarch_device(my_device_id, ConType="QPS")
    log_write("PPM connected to QPS\n")

    #Powers on PIF so drive can be detected
    my_quarch_device.send_command("RUN:POWer UP")

    #Drive Connection
    #Uses QCS class to retrieve list of all drives
    wrapped_drive_list = my_host_info.return_wrapped_drives()
    log_write("Drive list retrieved")

    #Calls function to format the list into a readable view
    formatted_drive_list = format_drive_list(wrapped_drive_list)

    selected_drive = None
    #Runs until user selects a drive or hits rescan
    while selected_drive is None or selected_drive in "Rescan":
        #Gets the input from the user, adds a few tidied up options
        selected_drive = listSelection(selectionList=formatted_drive_list, nice=True,
                                      additionalOptions=["Rescan", "Quit"], tableHeaders=["Drive"], align="c")

        #listOfDrives = my_host_info.return_wrapped_drives()
        formatted_drive_list = format_drive_list(wrapped_drive_list)

    log_write("Drive selected")

    #Removes unnecessary info
    selected_drive = selected_drive.split(":-")

    #Returns DriveWrapper object
    my_drive = my_host_info.get_wrapped_drive_from_choice(selected_drive[0])
    print("Drive Selected is :", selected_drive[0])

    #Boolean dependent on whether the selected drive is present
    drive_presence = poll_drive(my_drive)

    # Upgrade Quarch device to QPS device
    my_qps_device = quarchQPS(my_quarch_device)
    my_qps_device.open_connection()
    log_write("Upgraded Quarch device to QPS device")

    #Returns the name of the PPM module
    print(my_qps_device.send_command("*IDN?"))
    log_write(my_qps_device.send_command("*IDN?"))

    #Checks if 3V3 or 5V - Fixture_3V3 is true if 3V3, False if 5V
    conf_out = my_qps_device.send_command("CONFig:OUTput:MODE?")

    if conf_out == "3V3":
        fixture_3v3 = True
    elif conf_out =="5V":
        fixture_3v3 = False
    else:
        #Calls a function to manually set the fixture mode
        fixture_3v3 = manually_set_fixture_mode()

    #Change the resampling rate to 100us - adjust with testing.
    my_qps_device.send_command("stream mode resample 100us")

    #Enables pull down resistor on 5V/3V3 channel - reduces floating
    my_qps_device.send_command("CONFig:OUT:5v:PULLdown ON")
    log_write("Pull-down resistor enabled")

    #Powers up PPM
    my_qps_device.send_command("RUN:POWer UP")
    log_write("PPM Powered Up")

    #Creates filename for QPS stream to be stored - year month day, hours minutes seconds
    file_name = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

    #Creates stream object and starts streaming
    my_stream = my_qps_device.start_stream(stream_path + "\\" + file_name)

    #Create a synthetic channel for drive presence
    my_stream.create_channel("DrivePresence", "Digital", "", False)
    log_write("Drive Presence channel added")
    my_stream.add_data_point("DrivePresence", "Digital", drive_presence)

    log_write("Stream started")

    #Sets the voltage channels to nominal
    reset12v_nominal(my_qps_device)
    reset_3v3_5v_nominal(my_qps_device,fixture_3v3)

    print("Margining 12V rail")

    #Load 12V Pattern
    ppm12v_lower(my_qps_device)
    log_write("12V Pattern loaded")

    #Gets the voltage on the 12v channel in mv
    #returned in the format xxxx mV as a string
    #REGEXPATTERN removes any non-numeric character, and is typecast to an integer
    volt12v = my_qps_device.send_command("MEASure:VOLTage 12v?")
    volt12vint = int(re.sub(REGEX_PATTERN, '', volt12v))

    #Creates variables used to store the voltage level when drive browns out
    brownout_12v = 0
    brownout_3v3_5v = 0

    # Run 12V pattern
    my_qps_device.send_command("RUN:PATtern")
    my_stream.add_annotation("12V Ramp Down Start")
    log_write("Running Pattern")

    #While 12V rail is more than 150mV - often noise at ground, and drive is detected
    while volt12vint > 150 and drive_presence == True:
        #Polls drive
        drive_presence = poll_drive(my_drive)

        volt12v = my_qps_device.send_command("MEASure:VOLTage 12v?")
        volt12vint = int(re.sub(REGEX_PATTERN, '', volt12v))

        if not drive_presence:
            print("\nDrive no longer detected - brownout occurred when the 12V rail was " + volt12v)
            brownout_12v = volt12vint
            my_stream.add_annotation("Drive Brownout")

    log_write("12V Brownout at " + str(brownout_12v) + "mV")
    log_write("12V Margining complete\n")

    reset12v_nominal(my_qps_device)

    print("12V Margining complete, rail reset, margining 3V3/5V")

    print("Waiting for drive to come back online")
    #Waits for drive to come back online
    time.sleep(10)

    #Load 3V3 pattern
    ppm_3v3_5v_lower(my_qps_device, fixture_3v3)
    log_write("3V3/5V Pattern loaded")

    volt_3v3_5v = my_qps_device.send_command("MEASure:VOLTage 3v3?")
    volt_3v3_5v_int = int(re.sub(REGEX_PATTERN, '', volt_3v3_5v))

    #Run Pattern
    my_qps_device.send_command("RUN:PATtern")
    log_write("Running Pattern")
    my_stream.add_annotation("3V3/5V Ramp Down Start")

    while volt_3v3_5v_int > 150 and drive_presence == True:
        #Polls drive
        drive_presence = poll_drive(my_drive)

        volt_3v3_5v = my_qps_device.send_command("MEASure:VOLTage 3v3?")
        volt_3v3_5v_int = int(re.sub(REGEX_PATTERN, '', volt_3v3_5v))

        if not drive_presence:
            if fixture_3v3:
                print("\nDrive no longer detected - brownout occurred when the 3V3 rail was " + volt_3v3_5v)
            elif not fixture_3v3:
                print("\nDrive no longer detected - brownout occurred when the 5V rail was " + volt_3v3_5v)
            brownout_3v3_5v = volt_3v3_5v_int
            my_stream.add_annotation("Drive Brownout")

    log_write("3V3/5V Brownout at " + str(brownout_3v3_5v) + "mV")
    log_write("3V3 Margining complete\n")

    # Add a delay to allow time for the host to power on, the trigger to fire,
    # and the stream to complete.
    time.sleep(1)

    #Reset rails back to nominal
    reset_3v3_5v_nominal(my_qps_device, fixture_3v3)
    reset12v_nominal(my_qps_device)

    time.sleep(2)
    my_stream.stop_stream()
    log_write("Stream stopped")

    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    my_qps_device.close_connection()
    log_write("Closed connection, test complete")

    print_results(brownout_12v, brownout_3v3_5v, fixture_3v3)

    exit_script(my_qps_device,None)
    log_write("Exiting script")

    return None

def log_write(log_string):
    """"
    Appends log_string to log file - useful for debugging

    :param log_string: The string to log

    :return: None
    """
    #Writes the string log_string to log file and prints new line
    with open(log_file_path, "a") as logFile:
        logFile.write(log_string + "\n")

#Checking if user is admin
def admin_os_check():
    """
    Checks what OS the user is running, and whether the user has admin privileges
    Calls additional checks depending on OS for required packages

    :return: None
    """

    #If windows
    if os.name == "nt":
        log_write("OS: Windows")
        try:
            #Only admin users have access to the temp file
            #Will throw an error if a non-admin attempts access
            os.listdir(os.sep.join([os.environ.get("SystemRoot","C:\\windows"),"temp"]))
            log_write("User has admin privileges")

            # Checks WMIC installation - Used for drive detection
            check_wmic_installation()
            return True
        except:
            #Raises error if user does not have admin perms
            raise PermissionError("Admin privileges required")

    #If Linux
    elif os.name == "posix":
        log_write("OS: Linux")

        #Checks if LS SCSI is installed - Lists SCSI devices in the command-line
        check_lsscsi_installation()

        #Checks if SmartCTL is installed - On-drive Self-Monitoring, Analysis, Reporting Technology System
        check_smartctl_installation()

        #If admin, uid will return as 0
        if os.getuid() == 0:
            log_write("User has admin privileges")
            return True
        #Otherwise throw a permission error
        else:
            raise PermissionError("Admin privileges required")

    #If not Windows or Linux - raise a system error
    else:
        raise SystemError("Unsupported operating system for this module: %s" % (os.name,))

def check_wmic_installation():
    """
    Checks whether WMIC is installed
    WMIC is a package part of Windows - Windows Management Instrumentation Command-line
    #Deprecated tool, but used for checking drive presence

    :return None:
    """
    try:
        subprocess.run(["wmic","diskdrive"], capture_output=True, text=True)
        log_write("WMIC installed correctly")
    except FileNotFoundError as e:
        #Gives instructions how to install
        print("\n*****************\nPlease install the WMIC package")
        print("Windows -> Settings -> System -> Optional Features -> View Features ")
        print("See Available Features -> Search WMIC -> Tickbox -> Add")
        print("Once installed, please run script again\n***************\n")
        raise e

def check_lsscsi_installation():
    """
    Called if using Linux
    Checks whether LSSCSI is installed
    LSSCSI is a command-line utility used to list information about SCSI devices
    SCSI - Small Computer System Interface
    Used to check what drives are available

    :return:
    """
    try:
        subprocess.run(["lsscsi"], capture_output=True, text=True)
        log_write("LSSCSI installed correctly")
    except FileNotFoundError as e:
        print("\n*****************\nPlease install the LSSCSI package")
        print("If Debian/Ubuntu")
        print("sudo apt-get install lsscsi")
        print("If Fedora")
        print("sudo dnf install lsscsi")
        print("Or use your favourite package installer")
        print("Once installed, please run script again\n***************\n")
        raise e

def check_smartctl_installation():
    """
    Called if OS is Linux
    Checks whether SmartCTL is installed
    Command line utility for controlling and monitoring on-drive built-in system
    Self Monitoring Analysis and Reporting Technology (SMART)

    :return:
    """
    try:
        subprocess.run(["smartctl"], capture_output=True, text=True)
        log_write("SmartCTL installed correctly")
    except FileNotFoundError as e:
        print("\n*****************\nPlease install the SmartCTL package")
        print("https://github.com/smartmontools/smartmontools/tree/main")
        print("Once installed, please run script again\n***************\n")
        raise e


def poll_drive(wrapped_device):
    """
    Helper function of QuarchQCS's is_wrapped_drive_present()
    This polls as fast as possible

    Polls whether the drive passed in is present or not
    Used to detect when the drive browns out

    :param wrapped_device: The drive to be polled and checked
    :return: True if drive is present, False if not
    """

    #Stops the program searching through every system command for drives, if only 1 is in use
    drive_type = wrapped_device.drive_type

    #Returns a list of wrapped drives
    device_list = my_host_info.return_wrapped_drives(drive_type)

    for item in device_list:
        #Double check as switches may have same identifier but different description
        if wrapped_device.identifier_str == item.identifier_str:
            if wrapped_device.description == item.description:
                return True
    log_write("Drive is not present")
    return False


def reset12v_nominal(my_ppm):
    """
    Clears any pattern and sets 12V channel to 12V
    :param my_ppm: PPM used in test
    :return: None
    """
    my_ppm.send_command("SIGnal:12v:PATtern CLEAR")
    my_ppm.send_command("SIGnal:12v:VOLTage 12000")

#Creates pattern with 12V on lower limit
def ppm12v_lower(my_ppm):
    """
    Resets the 12V channel, then creates a pattern for 12V to ramp down to 0 over 500ms
    :param my_ppm: PPM used in test
    :return: None
    """
    reset12v_nominal(my_ppm)

    #Pattern to ramp down -12V down to 0 over 100ms
    my_ppm.send_command("SIGnal:12v:PATtern ADD 5s -12000 i")

#Clears any pattern and sets 3V3/5V channel to 3V3/5V
def reset_3v3_5v_nominal(my_ppm,fixture_3v3):
    """
    Clears any pattern and sets 3V3 channel to 3V3 or 5V channel to 5V
    :param my_ppm: PPM used in test
    :param fixture_3v3: Boolean: True if the fixture is 3V3, false if 5V
    :return: None
    """
    #If fixture_3v3 is true, it is a 3v3 fixture
    if fixture_3v3:
        my_ppm.send_command("SIGnal:3v3:PAT CLEAR")
        my_ppm.send_command("SIGnal:3v3:VOLTage 3300")
    #If fixture_3v3 is false it is a 5V fixture
    elif not fixture_3v3:
        my_ppm.send_command("SIGnal:5v:PATtern CLEAR")
        my_ppm.send_command("SIGnal:5v:VOLTage 5000")

#Creates pattern with 3V3/5V ramping down to 0V
def ppm_3v3_5v_lower(my_ppm,fixture_3v3):
    """
    Creates a pattern for 3V3 to ramp down to 0 over 200ms, or 5V to ramp down to 0 over 200ms

    :param my_ppm: PPM used in test
    :param fixture_3v3: Boolean: True if the fixture is 3V3, false if 5V
    :return: None
    """
    reset_3v3_5v_nominal(my_ppm,fixture_3v3)
    #Ramps down 3V3 to 0V over 200ms
    if fixture_3v3:
        my_ppm.sendCommand("SIGnal:3v3:PATtern ADD 5s -3300 i")
    #Ramps down 5V over 200ms
    elif not fixture_3v3:
        my_ppm.sendCommand("SIGnal:5v:PATtern ADD 5s -5000 i")

def manually_set_fixture_mode():
    """
    If using a dumb fixture, or fixture cannot be detected, user selects 3V3 or 5V
    Returns True if 3V3, False if 5V
    """
    print("Fixture mode not automatically detected")
    print("Please select 3V3 or 5V")
    fixture_options = ["3V3", "5V"]

    fixture_mode = listSelection(title="Fixture Mode: 3V3 or 5V", selectionList=fixture_options, nice=True)

    if fixture_mode == "3V3":
        return True
    else:
        return False

#Shows drive identifier and drive description for each drive found
#Otherwise just drive addresses
def format_drive_list(wrapped_drive_list):
    """
    Tidies up drive list into a readable format showing drive identifier and description

    :param wrapped_drive_list: Drive list to be formatted
    :return formatted_drive_list: List of drives that have been formatted
    """
    #Creates empty list for drives that have already been formatted
    formatted_drive_list = []

    #For each drive found
    for drive in wrapped_drive_list:
        #Show only drive identifier and description
        formatted_drive_list.append("{0} :- {1}".format(drive.identifier_str, drive.description))
    #Returns the formatted drive list
    return formatted_drive_list

def print_results(level_12v_brownout, level_3v3_5v_brownout,fixture_3v3):
    """
    Used to display results - displays what voltage level the drive browned out at, and whether it met the spec
    :param level_12v_brownout: The 12v rail voltage (in mV) of when the drive lost comms
    :param level_3v3_5v_brownout: The 3v3/5V voltage (in mV) of when the drive lost comms
    :param fixture_3v3: Boolean: True if the fixture is 3V3, false if 5V
    :return:
    """
    print("\nPCIe CEM Spec dictates that the 12V rail has a tolerance of 12V+5%-8% (11040mV < 12000mV < 12600mV)")
    print("The drive had a brown out when the 12V rail reached ", level_12v_brownout, " mV")
    if level_12v_brownout < 11040:
        print("The drive met the PCIe CEM Spec for the 12V rail\n")
        log_write("Drive met PCIe CEM Spec for the 12V rail\n")
        passed12v = True
    else:
        print("The drive failed the PCIe CEM Spec for the 12V rail\n")
        log_write("Drive failed the PCIe CEM Spec for the 12V rail\n")
        passed12v = False

    passed3v3 = None
    if fixture_3v3:
        print("\nPCIe CEM Spec dictates that the 3V3 rail has a tolerance of 3V3+5%-6% (3102mV < 3300mV < 3465mV)")
        print("The drive had a brown out when the 3V3 rail reached " ,level_3v3_5v_brownout, " mV")
        if level_3v3_5v_brownout < 3102:
            print("The drive met the PCIe CEM Spec for the 3V3 rail\n")
            log_write("Drive met the PCIe CEM Spec for the 3V3 rail\n")
            passed3v3 = True
        else:
            print("The drive failed the PCIe CEM Spec for the 3V3 rail\n")
            log_write("Drive failed the PCIe CEM Spec for the 3V3 rail\n")
            passed3v3 = False

    if (passed12v == True) and (passed3v3 == True):
        print("\nThe drive meets the PCIe CEM Spec with respect to power\n")

#Exits script cleanly, and closes the connection to the device
def exit_script(my_device, err=None):
    """
    Exit script cleanly, ensuring module is reset to default state
    and no connection to module is left open.

    :param my_device: quarchDevice obj - Module wrapper for selected module.
    :param err : String (optional) - Display an error to user before exiting the script.
    """
    my_device.send_command("CONFig:DEFault STATE")
    my_device.close_connection()
    if err:
        logging.error(err)
    quit()

# Standard Python entry point. This ensures the main() function is called when the script is executed.
if __name__== "__main__":
    main()
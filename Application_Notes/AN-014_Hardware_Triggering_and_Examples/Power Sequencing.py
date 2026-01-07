"""
AN-014 - Application note demonstration of power sequencing using a breaker and PAM
The PAM is used to verify that the operation is working as intended

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Runs a simple script for the breaker and PAM
- Takes user input using Quarchpy's userInterface
- Configures a breaker to add user configurable delays
- And sets the breaker to trigger on a user selectable power rail (3V3 or 12V)
- Uses a PAM to verify the operation is working as expected

The commands sent to the device are in the format
RUN:POWer UP
The commands are based on SCPI control system, but not all SCPI has been implemented
Commands are not case-sensitive. Most commands will have short forms - e.g. POWer shortens to POW

########### VERSION HISTORY ###########

06/01/2025 -  Andrew S - operation review, and changes made

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
2- Connect PCIe Module that supports triggering
3- Connect PAM and Quarch Interface Unit with USB to control PC
4- Connect Power cables to PAM and Quarch Interface Unit
5- Run the script and follow the instructions on screen
6- Refer to AN-014 set-up section for an illustration

####################################

This script was written and tested using a QTL2910 AIC PAM Fixture, and a QTL2358 AIC Breaker,
with a Host Card as the PCIe device

This script uses both a breaker and a PAM. This script is to check whether a PCIe based device meets the PCIe CEM spec,
in regard to power sequencing
Section 4.4 of the PCIe CEM specification states

There is no specific requirement for power supply sequencing of the power supply rails, whether
delivered by the system board or cables. They may come up or go down in any order
"""

# Import necessary libraries used in the examples
import os
import time     # Used for sleep commands to add delays
import logging  # Used for logging - mainly for debugging but log file is created automatically
import re       #REGEX, used for stripping and validating inputs

#Imports Quarchpy, and the device and QPS part
import quarchpy
from quarchpy.device import *
from quarchpy.qps import *
from quarchpy.user_interface import *

#Local file where the python script is stored
base_directory = str(os.path.dirname(os.path.realpath(__file__)))

#Names a folder for output of script to go
data_folder_name = "PowerSequencingOutputs"

#Specifies datapath in the local folder where script is stored
data_path = os.path.join(base_directory, data_folder_name)

#Creates the directory for output data
os.makedirs(data_path, exist_ok=True)

#StreamPath is where the QPS Trace is stored.
#Stored within the local folder
stream_path = os.path.join(data_path, "QPS Trace")

#Log file path is used for logging
#Explicitly stated to be in same path as the python script
#File name is logFile_YYYY-MM-DD-HH-mm-SS.txt, in localtime
log_file_path = os.path.join(data_path, "logFile_" + time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + " .txt")

#Leaves only numeric characters, strips all non-numeric characters
REGEX_PATTERN = r"\D+"

def main():
    #Starts logging - Has both QIS logs, and script logs
    logging.basicConfig(filename=log_file_path, level=logging.DEBUG,
                        format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
                        datefmt="%H:%M:%S")

    print("Quarch application note example: AN-014 Power Sequencing")
    print("---------------------------------------\n\n")

    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print("Connect to Breaker. Scanning for Devices...\n")
    log_write("Connecting to breaker")
    device_list = scanDevices('all', favouriteOnly=True)

    #Takes the users input from command line
    module_str = userSelectDevice(device_list, additionalOptions = ["Rescan","All Conn Types","Quit"], nice=True)

    #If user has to quit, quit and close nicely
    if module_str == "quit":
        log_write("User selected quit")
        return 0

    # Create a device using the module connection string returned from the selection
    print("\n\nConnecting to the selected device")
    breaker_device = get_quarch_device(module_str)

    #Logging the breaker identity
    log_write("Connected to breaker: Breaker identity")
    log_write(breaker_device.send_command("*idn?"))

    # Print the device name after the selection to confirm connection
    print("Module Name:")
    print(breaker_device.send_command("hello?"))

    # Sets the module to its default state
    breaker_device.send_command("CONFig:DEFault STATE")
    log_write("Breaker set to default state")

    #Powers down the breaker
    breaker_device.send_command("RUN:POWer DOWN")
    log_write("Breaker powered down")

    #Configure what power rail the breaker is triggered off
    user_select_power_rail_trig(breaker_device)

    #Calls the user selected delay function
    print("Please enter the delays in ms for the power up sequence")

    delay1_up, delay2_up, delay3_up = user_select_delays()
    log_write("Power up delays selected: "+ delay1_up +"ms " + delay2_up +"ms " + delay3_up+"ms")

    print("\nPlease enter the delays in ms for the power down sequence")
    delay1_down, delay2_down, delay3_down = user_select_delays()
    log_write("Power down delays selected: " + delay1_down + "ms " + delay2_down + "ms " + delay3_down + "ms")

    #Configures breaker with delays of 25, 50 and 75ms
    breaker_config_sequence(breaker_device, delay1_up, delay2_up, delay3_up)
    log_write("Breaker power up configured")

    #Close the connection to the breaker for the time being
    breaker_device.close_connection()
    log_write("Closed breaker connection")


    print("-Starting QPS")
    # Checks if QPS is already running, and starts it if it isn't
    if not isQpsRunning():
        log_write("Starting QPS")
        # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps(keepQisRunning=True)

    # Open an interface to local QPS - used for communicating with it
    my_qps = qpsInterface()
    log_write("QPS Interface opened")

    print("\n-Requesting PAM selection")
    #Asks user to select the PAM to be used
    my_device_id = GetQpsModuleSelection(my_qps)
    log_write("Requesting PAM selection")

    # Create a Quarch device connected via QPS
    my_quarch_device = get_quarch_device(my_device_id, ConType="QPS")
    log_write("PAM connected")

    # Upgrade Quarch device to QPS device
    pam_device = quarchQPS(my_quarch_device)
    log_write("Quarch device upgraded to QPS device")

    #Opens connection to the PAM
    pam_device.open_connection()
    log_write("PAM connection opened")

    #Logs the PAM identity
    log_write("Connected to PAM. PAM identity:")
    log_write(pam_device.send_command("*idn?"))

    #Averaging window of 4us for digital signals
    #Check default stream rate
    #pam_device.send_command("RECord:AVEraging:GROup 1 8")

    #Powers the pam up
    pam_device.send_command("RUN:POWer up")

    # Creates the stream folder, named YY-MM-DD_HH_MM_SS
    file_name = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

    #Started the stream
    my_stream = pam_device.start_stream(stream_path + "\\" + file_name)
    log_write("Stream started")

    #Opens connection to the breaker
    breaker_device.open_connection()

    #Powers up the breaker - This starts the sequence of delays on the power up
    breaker_device.send_command("RUN:POWer up")
    log_write("Breaker powered up, sequence started")

    #Gives some time for the drive to be recognised, and the stream to record
    time.sleep(5)

    #Breaker configured for power down - delays of 100ms, 75ms and 50ms
    breaker_config_sequence(my_quarch_device, delay1_down, delay2_down, delay3_down)
    log_write("Breaker power down configured")

    #Waits 1s before running the pattern
    time.sleep(1)
    breaker_device.send_command("RUN:POWer down")

    #Gives time to record before ending stream
    time.sleep(5)

    #Stops streaming
    my_stream.stop_stream()
    log_write("Stream completed")

    #Close connection to the breaker and PAM - streaming finished
    breaker_device.close_connection()
    log_write("Breaker connection closed")
    pam_device.close_connection()
    log_write("PAM connection closed")

    #Test finished
    print("Test completed")
    print("Change the delays, and the power rail that is triggered off, and check if the spec is met")

    print("\nThe PCI Express Card Electromechanical Specification, Revision 6, Section 4.4 states")
    print("\nThere is no specific requirement for power supply sequencing of the power supply rails, whether")
    print("delivered by the system board or cables. They may come up or go down in any order. ")

    print("Change the order of the power rails going up, and see if the device still comes online")

    log_write("Test completed")

    exit_script(pam_device, breaker_device, None)
    log_write("Exiting script")

    return None

def user_select_delays():
    """
    Used to input delays in milliseconds from the user.
    Delay 1 is for 12V_POWER, Delay 2 is for 3V3_POWER, Delay 3 is for 3V3_AUX
    Inputs are stripped of any non-numeric characters

    :return str delay1, delay2, delay3:  Delays in ms to assign to power rails
    """
    print("Please enter the delay for the 12V rail in ms")
    delay1_input = str(input("Delay 1: "))
    delay1 = re.sub(REGEX_PATTERN, '', delay1_input)

    print("Please enter the delay for the 3V3 rail in ms")
    delay2_input = str(input("Delay 2: "))
    delay2 = re.sub(REGEX_PATTERN, '', delay2_input)

    print("Please enter the delay for the 3V3_AUX rail in ms")
    delay3_input = str(input("Delay 3: "))
    delay3 = re.sub(REGEX_PATTERN, '', delay3_input)

    print("\nDelays selected are")
    print("12V delay :" + delay1 + "ms")
    print("3V3 delay :" + delay2 + "ms")
    print("3V3_AUX delay :" + delay3 + "ms\n")

    return [delay1,delay2,delay3]

#Configures the breaker
#PCIe CEM standard has no specific requirement on power supply sequencing
#Therefore any order of 12V, 3V3 or 3V3_Aux power up or power down is permissible
def breaker_config_sequence(my_breaker, delay1, delay2, delay3):
    """
    Used to configure the breaker delays on power rails
    Written for PCIe based devices, so 12V and 3V3, with an optional 3V3Aux - hence 3 delays

    :param my_breaker: The breaker to be configured
    :param delay1: The delay in milliseconds to be assigned to 12V_POWER
    :param delay2: The delay in milliseconds to be assigned to 3V3_POWER
    :param delay3: The delay in milliseconds to be assigned to 3V3_AUX
    :return None:
    """

    my_breaker.open_connection()
    #Delays are in milliseconds
    my_breaker.send_command("SOURce:1 DELAY " + delay1)
    my_breaker.send_command("SOURce:2 DELAY " + delay2)
    my_breaker.send_command("SOURce:3 DELAY " + delay3)
    log_write("Source delays have been set")

    # Assigns source 1 delay to 12V power, source 2 delay to 3V3 power, source 3 delay to 3V3 aux
    my_breaker.send_command("SIGnal:12V_POWER:SOURce 1")
    my_breaker.send_command("SIGnal:3V3_POWER:SOURce 2")
    my_breaker.send_command("SIGnal:3V3_AUX:SOURce 3")
    log_write("Signals have been assigned delays")

def user_select_power_rail_trig(my_breaker):
    """
    Configures the breaker to trigger from either 3V3 or 12V, with user input

    :param my_breaker: The breaker that is used.
    :return power_rail_trig: The rail to trigger breaker signals from
    """

    print("Please select the power rail to trigger the breaker from")
    #PCIe based drives, so 12V, 3V3 and 3V3 Aux power rails
    power_rail_options = ["12V", "3V3"]
    #Asks the user to select an option for the power rail to trigger from
    power_rail_trig = listSelection(title="Power rail to trigger from", selectionList=power_rail_options, nice=True)
    #Assign power_rail_trig to the rail
    #power_rail_trig = power_rail_options[power_rail_index]
    #3v3_host or 12v_host
    my_breaker.send_command("TRIGger:OUT:MODE " + power_rail_trig + "_host")

def log_write(log_string):
    """"
    Appends log_string to log file - useful for debugging

    :param log_string: The string to log

    :return: None
    """
    #Writes the string log_string to log file and prints new line
    with open(log_file_path, "a") as log_file:
        log_file.write(log_string + "\n")

#Exits script cleanly, and closes the connection to the device
def exit_script(my_device1, my_device2, err=None):
    """
    Exit script cleanly, ensuring module is reset to default state
    and no connection to module is left open.
    #Script makes use of 2 modules, hence has 2 devices as parameters

    :param my_device1: quarchDevice obj - Module wrapper for selected module.
    :param my_device2: quarchDevice obj - Module wrapper for selected module.
    :param err : String (optional) - Display an error to user before exiting the script.
    """
    my_device1.send_command("CONFig:DEFault STATE")
    my_device1.close_connection()
    my_device2.send_command("CONFig:DEFault STATE")
    my_device2.close_connection()
    if err:
        logging.error(err)
    quit()

# Standard Python entry point. This ensures the main() function is called when the script is executed.
if __name__== "__main__":
    main()
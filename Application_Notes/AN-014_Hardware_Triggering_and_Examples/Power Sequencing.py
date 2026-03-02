"""
AN-014 - Application note demonstration of power sequencing using a breaker and PAM
The PAM is used to verify that the operation is working as intended

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Runs a simple script for the breaker and PAM
- Takes user input using Quarchpy's userInterface
- Configures a breaker to add user configurable delays
- And sets the breaker to trigger from a user selectable power rail (3V3 or 12V)
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

This application note references the PCIe Card ElectroMechanical Specification. It is therefore recommended to use
Add-In Card modules rather than another standard based on the PCIe spec.

This app note can be used to help verify compliance with the spec. You should run this script a few times, varying the
length and order of delays, and the power rail that is triggered from changed.

This script was written and tested using a QTL2910 AIC PAM Fixture, and a QTL2358 AIC Breaker,
with a Host Card as the PCIe device - See Scripts User Guide.docx for an image of the setup

It is suggested to use separate host and control PCs. Connect the Torridon and PAM to the control PC. Run the script,
follow the instructions on screen. Once the stream starts, power up or power down the host PC.


Section 4.4 of the PCIe CEM specification states

There is no specific requirement for power supply sequencing of the power supply rails, whether delivered by the
system board or cables. They may come up or go down in any order
"""

# Import necessary libraries used in the examples
import os
import sys
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

#Leaves only numeric characters, strips all non-numeric characters
REGEX_PATTERN = r"\D+"

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    print("Quarch application note example: AN-014 Power Sequencing")
    print("---------------------------------------\n\n")

    #Gives instructions to user in the terminal
    print("\n*************************************")
    print("*************************************\n")
    print("When the stream is running, power up or power down the host system. The stream will run for 60 seconds - you can adjust this value in the script")
    print("\n*************************************")
    print("*************************************\n")

    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print("Connect to Breaker. Scanning for Devices...\n")
    device_list = scanDevices('all', favouriteOnly=True)

    #Takes the users input from command line
    module_str = userSelectDevice(device_list, additionalOptions = ["Rescan","All Conn Types","Quit"], nice=True)

    #If user has to quit, quit and close nicely
    if module_str == "quit":
        return 0

    # Create a device using the module connection string returned from the selection
    print("\n\nConnecting to the selected device")
    breaker_device = get_quarch_device(module_str)

    # Print the device name after the selection to confirm connection
    print("Module Name:")
    print(breaker_device.send_command("hello?"))

    # Sets the module to its default state
    breaker_device.send_command("CONFig:DEFault STATE")

    #Breaker is powered down -
    breaker_device.send_command("RUN:POWer DOWN")

    #Configure what power rail the breaker is triggered off
    user_select_trigger(breaker_device)

    #Calls the user selected delay function
    print("Please enter the delays in ms for the power up sequence")

    delay1_up, delay2_up, delay3_up = user_select_delays()

    #Opening QPS
    print("-Starting QPS")

    # Checks if QPS is already running, and starts it if it isn't
    if not isQpsRunning():
        # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps(keepQisRunning=True)

    # Open an interface to local QPS - used for communicating with it
    my_qps = qpsInterface()

    print("\n-Requesting PAM selection")
    #Asks user to select the PAM to be used
    my_device_id = GetQpsModuleSelection(my_qps)

    # Create a Quarch device connected via QPS
    my_quarch_device = get_quarch_device(my_device_id, ConType="QPS")

    # Upgrade Quarch device to QPS device
    pam_device = quarchQPS(my_quarch_device)

    #Opens connection to the PAM
    pam_device.open_connection()

    # Powers the pam up
    pam_device.send_command("RUN:POWer up")

    # Creates the stream folder, named YY-MM-DD_HH_MM_SS
    file_name = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

    #Configures breaker with user selected delay
    breaker_configure_delays(breaker_device, delay1_up, delay2_up, delay3_up)


    #STREAM START
    #Started the stream
    print("Starting Stream, open QPS")
    my_stream = pam_device.start_stream(stream_path + "\\" + file_name)

    #Streams for 60 seconds - enough for a power up or power down on most systems - increase this if needed
    visual_sleep(60)

    #Stops streaming
    my_stream.stop_stream()
    print("Stream completed")
    #STREAM END


    #Close connection to the breaker and PAM - streaming finished
    print("Closing connections")
    breaker_device.close_connection()

    pam_device.close_connection()

    #Test finished
    print("\nTest completed")

    print("\n\nThe PCI Express Card Electromechanical Specification, Revision 6, Section 4.4 states")
    print("\nThere is no specific requirement for power supply sequencing of the power supply rails, whether")
    print("delivered by the system board or cables. They may come up or go down in any order. ")

    print("\nSuggested actions to verify compliance with spec:")
    print("\n\nChange the host power rail that is triggered from")
    print("Change the delays, and the order of the delays")
    print("Verify that the device comes online as expected")

    sys.exit()


def user_select_delays():
    """
    Used to input delays in milliseconds from the user.
    Delay 1 is for 12V_POWER, Delay 2 is for 3V3_POWER, Delay 3 is for 3V3_AUX
    Inputs are stripped of any non-numeric characters
    If left blank, or wholly non-numeric characters, default delays of 1s, 2s, 1.5s will be assigned

    :return str delay1, delay2, delay3:  Delays in ms to assign to power rails
    """
    print("\nPlease enter the delays below. Suggested delays are: 1000, 2000, 1500ms")
    print("If left blank, suggested delays will be the default")

    print("\nThe delay entered is the time after host power comes up, that each power rail will come up\n")

    print("\nPlease enter the delay for the 12V rail in ms")
    delay1_input = str(input("Delay 1: "))
    delay1 = re.sub(REGEX_PATTERN, '', delay1_input)
    #If Blank
    if delay1 == "":
        delay1 = str(1000)
    else:
        delay1 = delay1

    print("\nPlease enter the delay for the 3V3 rail in ms")
    delay2_input = str(input("Delay 2: "))
    delay2 = re.sub(REGEX_PATTERN, '', delay2_input)
    #If Blank
    if delay2 == "":
        delay2 = str(2000)
    else:
        delay2 = delay2

    print("\nPlease enter the delay for the 3V3_AUX rail in ms")
    delay3_input = str(input("Delay 3: "))
    delay3 = re.sub(REGEX_PATTERN, '', delay3_input)
    if delay3 == "":
        delay3 = str(1500)
    else:
        delay3 = delay3

    print("\nDelays selected are")
    print("12V delay: " + delay1 + "ms")
    print("3V3 delay: " + delay2 + "ms")
    print("3V3_AUX delay: " + delay3 + "ms\n")

    return [delay1,delay2,delay3]

def breaker_configure_delays(my_breaker, delay1, delay2, delay3):
    """
    Used to configure the breaker delays on power rails
    Written for PCIe based devices, so 12V and 3V3, with an optional 3V3Aux - hence 3 delays

    :param my_breaker: The breaker to be configured
    :param delay1: The delay in milliseconds to be assigned to 12V_POWER
    :param delay2: The delay in milliseconds to be assigned to 3V3_POWER
    :param delay3: The delay in milliseconds to be assigned to 3V3_AUX
    :return None:
    """

    #Delays are in milliseconds
    my_breaker.send_command("SOURce:1 DELAY " + delay1)
    my_breaker.send_command("SOURce:2 DELAY " + delay2)
    my_breaker.send_command("SOURce:3 DELAY " + delay3)

    #Moves all signals to source 7 - Immediate change
    my_breaker.send_command("SIGnal:ALL:SOURce 7")

    # Assigns source 1 delay to 12V power, source 2 delay to 3V3 power, source 3 delay to 3V3 aux
    my_breaker.send_command("SIGnal:12V_POWER:SOURce 1")
    my_breaker.send_command("SIGnal:3V3_POWER:SOURce 2")
    my_breaker.send_command("SIGnal:3V3_AUX:SOURce 3")

def user_select_trigger(my_breaker):
    """
    Takes user input to select the host power rail to trigger the breaker power from

    :param my_breaker: The breaker that is used.
    :return None:
    """

    print("\nPlease select the power rail to trigger the breaker from")

    #3V3_AUX is not available as an option, as it is normally on standby
    power_rail_options = ["12V_HOST", "3V3_HOST"]

    #Asks the user to select an option for the power rail to trigger from
    power_rail_trig = listSelection(title="Power rail to trigger from", selectionList=power_rail_options, nice=True)

    #Sets the trigger mode to power
    my_breaker.send_command("TRIGger:IN:MODE POWER")

    #Triggers on the rising edge of the power rail
    my_breaker.send_command("TRIGger:IN:TYPE EDGE")

    #Sets the trigger to the rail the user selected
    my_breaker.send_command("TRIGger:IN:SOURce " + power_rail_trig)

    #Prints the rail selected
    print("Power rail triggered from is " + power_rail_trig + "\n")


# Standard Python entry point. This ensures the main() function is called when the script is executed.
if __name__== "__main__":
    main()
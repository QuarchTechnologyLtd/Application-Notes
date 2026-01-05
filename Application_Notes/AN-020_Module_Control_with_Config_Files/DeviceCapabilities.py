'''
AN-020 - Application note demonstrating module control with configuration files

This example shows how to use the configuration file data to find the capabilities of a Quarch module.
The script uses the selected module to find the config file and then parses it.
We then print the various sections to the terminal.

########### VERSION HISTORY ###########

19/08/2019 - Andy Norrie    - Initial release
17/03/2023 - Matt Holsey    - Application note reworks

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

Update to the latest quarcypy (python -m pip install quarchpy --upgrade) to get the latest configuration files
Connect any Quarch breaker/hot-plug module and run the script

####################################
'''
import logging

from quarchpy.config_files import *
from quarchpy.device import *


def main():
    print("Quarch application note example: AN-020")
    print("---------------------------------------\n\n")

    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print("Scanning for devices...\n")
    deviceList = scanDevices('all', favouriteOnly=False)

    # You can work with the deviceList dictionary yourself, or use the inbuilt 'selector' functions to help
    # Here we use the user selection function to display the list on screen and return the module connection string
    # for the selected device
    moduleStr = userSelectDevice(deviceList, additionalOptions=["Rescan", "All Conn Types", "Quit"], nice=True)
    if moduleStr == "quit":
        return 0

    # If you know the name of the module you would like to talk to then you can skip module selection and hardcode the string.
    # moduleStr = "USB:QTL1743-01-001"

    # Create a device using the module connection string
    print("\n\nConnecting to the selected device")
    my_device = getQuarchDevice(moduleStr)

    file = None
    try:
        # Find the correct config file for the connected module (breaker modules only for now)
        # We're passing the module connection here, the idn_string can be supplied instead if the module is not currently attached (simulation/demo mode)
        file = get_config_path_for_module (module_connection = my_device)
    except FileNotFoundError as err:
        logging.error(f"Config file not found for module : {moduleStr}\nExiting Script")
        my_device.closeConnection()
        return

    # Parse the file to get the device capabilities
    dev_caps = parse_config_file (file)

    if not dev_caps:
        logging.error(f"Could not parse config file for {moduleStr}\nExiting Script")
        my_device.closeConnection()
        return

    print ("\nCONFIG FILE LOCATED:")
    print (file)
    print ("\n")

    # Prints a list of top level capabilities that this module has (differentiating from a 'base' module)
    # This is useful to check if a module supports features such as driving and monitoring
    print ("GENERAL CAPABILITIES:")
    for key, value in dev_caps.get_general_capabilities().items():
        print(key + " = " + value)
    print ("\n")

    # Print the list of signals on the module, and the capability flags for each signal
    # This can be used to iterate a test over every signal in a module
    print ("SIGNALS AVAILABLE:")
    for sig in dev_caps.get_signals():
        print ("Name:\t" + sig.name)
        for key, value in sig.parameters.items():
            print("\t" + key + " = " + value)
    print ("\n")

    # Print out the list of signal groups, and the list of signals they control
    # Groups allow faster settings of blocks of signals, without needing to know all the individual names
    print ("SIGNALS GROUPS AVAILABLE:")
    for group in dev_caps.get_signal_groups():
        print ("Name:\t" + group.name)
        print ("\t", end='')
        for sig in group.signals:
            print (sig + ",", end='')
        print ("")
    print ("\n")

    # Print the sources on the module, and list their capabilities
    # Some modules have fewer sources available, or have different timing resolutions
    print ("SOURCES AVAILABLE:")
    for source in dev_caps.get_sources():
        print ("Name:\t" + source.name)
        for key, value in source.parameters.items():
            print("\t" + key + " = " + str(value))
        print ("")

    print("Finished script. \nClosing module connection.")
    my_device.closeConnection()

if __name__ == "__main__":
    main()
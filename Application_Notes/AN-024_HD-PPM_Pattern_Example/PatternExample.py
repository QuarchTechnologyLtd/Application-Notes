#!/usr/bin/env python
'''
This example demonstrates the creation of a complex ripple pattern on an HD PPM

########### VERSION HISTORY ###########

07/09/2021 - Andy Norrie     - First Version
13/02/2023 - Matt Holsey     - Updating inline with other app notes

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

1- Connect a Quarch PPM to your PC via USB or LAN and power it on
2- Ensure quarcypy is installed

####################################
'''

import os, time
import logging
import quarchpy
from quarchpy.device import *

# # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
# # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
# logging.basicConfig(level=logging.DEBUG)
# # To control specifically the quarchpy console log level use the following line:
# quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
# # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

# USER CHANGABLE VARIABLES
start_magnitude = 35
end_magnitude = 100
incr_magniture = 5
# Magnitudes are defined as the level that the pattern will drive both above and below the nominal value (pp / 2)


def main():
    '''
    Main function, containing the example code to execute
    '''

    # Required min version for this application note
    quarchpy.requiredQuarchpyVersion("2.0.20")

    # Display title text
    print("\n################################################################################\n")
    print("\n                           QUARCH TECHNOLOGY                                  \n\n")
    print("                        PPM Pattern generation Example                              ")
    print("\n################################################################################\n")

    # Scan for quarch devices on the system
    deviceList = scanDevices('All')
    # Display devices and allow user to select module
    myDeviceID = userSelectDevice(deviceList, additionalOptions=["quit"], nice=True)
    if myDeviceID == "quit":
        return 0

    ######################################################
    # Here we connect to the PPM and power up the outputs
    ######################################################

    myQuarchDevice = quarchDevice(myDeviceID)
    # Convert the base device to a power device class
    myPpmDevice = quarchPPM(myQuarchDevice)

    # Prints out connected module information
    print("MODULE CONNECTED: \n" + myPpmDevice.sendCommand("*idn?"))

    print("-Waiting for drive to be ready")
    # Setup the voltage mode and enable the outputs.  This is used so the script is compatible with older XLC modules which do not autodetect the fixtures
    setupPowerOutput(myPpmDevice)

    # (OPTIONAL) Wait for device to power up and become ready
    time.sleep(1)

    ######################################################
    # Now we set up the PPM streaming parameters
    ######################################################

    print("-Setting up module record parameters")
    # Sets for a manual record trigger, so we can start the stream from the script
    msg = myPpmDevice.sendCommand("record:trigger:mode manual")
    if (msg != "OK"):
        print("Failed to set trigger mode: " + msg)

    # Set the averaging rate to the module to 4uS
    msg = myPpmDevice.sendCommand("record:averaging 0")
    if (msg != "OK"):
        print("Failed to set hardware averaging: " + msg)
    else:
        print("Averaging: " + myPpmDevice.sendCommand("record:averaging?"))

    current_magniture = start_magnitude
    while current_magniture <= end_magnitude:

        # Show the user what we are doing for this test cycle
        print("\nTEST - " + str(int(current_magniture) * 2) + " mV pp ripple injection")

        ######################################################
        # Here we create and send the required pattern to the PPM.  This is generated
        # using an example function to create a rapid ripple effect with a reducing frequency
        ######################################################
        setPowerPattern(myModule=myPpmDevice, set5V=True, set12V=True, upper_margin=current_magniture,
                        lower_margin=-current_magniture, incr_us=1, incr_repeat=2, end_time=5000)

        print("Pattern set OK")

        ######################################################
        # Run the pattern
        ######################################################
        logging.debug("Sending command : 'run pattern 1'")
        response = myPpmDevice.sendCommand("run pattern 1")
        if "OK" not in response:
            raise ValueError("Device failed pattern run command with error: " + response)
        else:
            print("Pattern Run OK")

        # Move to the next magnitude for testing
        current_magniture = (current_magniture + incr_magniture)

    # Close connection to the module now we're done with it.
    print("\n-Closing module")
    myPpmDevice.closeConnection()

    print("ALL DONE!")


def setupPowerOutput(myModule):
    """
    Function to check the output state of the module and prompt to select an output mode if not set already

    :param myModule: quarchPPM obj - Wrapper for quarch module containing automation functionality
    """

    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    if "DISABLED" in myModule.sendCommand("config:output Mode?"):
        try:
            drive_voltage = raw_input(
                "\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"
        except NameError:
            drive_voltage = input(
                "\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"

        myModule.sendCommand("config:output:mode:" + drive_voltage)

    # Check the state of the module and power up if necessary
    powerState = myModule.sendCommand("run power?")
    print(f"Checking power up on device: {powerState}")

    # If outputs are off
    if "OFF" in powerState:
        # Power Up
        print("\n Turning the outputs on:"), myModule.sendCommand("run:power up"), "!"


def setPowerPattern(myModule, set5V, set12V, upper_margin, lower_margin, incr_us, incr_repeat, end_time):
    """
    Exception function to generate a pattern on the PPM output.  This allows an arbitary over and under margin level to be set
    along with parameters to allow an ongoing shift in the frequency of the pattern.  The pattern always ends in the same voltage
    as it starts, so it can be run in on repeat if needed.

    :param myModule: quarchPPM obj - Wrapper for quarch module containing automation functionality
    :param set5V: Allow the 3v3/5v channel to enable or disable pattern generation for each power rail
    :param set12V: Allow the 12v channel to enable or disable pattern generation for each power rail
    :param upper_margin: Milli Volts to add to the initial level of the power rail (max value for the pattern)
    :param lower_margin: Milli Volts to subtract to the initial level of the power rail (min value for the pattern)
    :param incr_us: Number of microseconds to increment the pattern period for
    :param incr_repeat: Number of periods that the pattern should run for, before the increment value is applied
    :param end_time: Final time in microseconds for the last point in the pattern
    :return:
    """

    # Clear any existing patterns
    myModule.sendCommand("sig:5v:pattern clear")
    myModule.sendCommand("sig:12v:pattern clear")

    # Init the first point manually
    point_time = 0
    point_level = upper_margin
    # Set up the repeat pattern parameters
    repeat_count = 1
    current_incr = incr_us
    margin_toggle = False

    # Loop until we reach the end time
    print("-Writing the pattern to the device...")
    while point_time < end_time:
        # Write out the points, using interpolate to ensure smooth transitions
        if set12V:
            logging.debug(f"Sending command 'sig:12v:pat:add {str(point_time)}uS {str(point_level)} i")
            response = myModule.sendCommand("sig:12v:pat:add " + str(point_time) + "uS " + str(point_level) + " i")
            if ("OK" not in response):
                raise ValueError("Device failed pattern command with error: " + response)
            # print (str(point_time) + "\t" + str(point_level))
        if set5V:
            logging.debug(f"Sending command 'sig:5v:pat:add {str(point_time)}uS {str(point_level)} i")
            response = myModule.sendCommand("sig:5v:pat:add " + str(point_time) + "uS " + str(point_level) + " i")
            if ("OK" not in response):
                raise ValueError("Device failed pattern command with error: " + response)

        # Calculate the paramaters for the next point
        point_time = point_time + current_incr
        repeat_count = repeat_count - 1
        # Handle flipping of the pattern between upper and lower bounds
        if margin_toggle:
            point_level = upper_margin
            margin_toggle = False
        else:
            point_level = lower_margin
            margin_toggle = True
        # Handle increasing steps between each pattern point
        if repeat_count == 0:
            repeat_count = incr_repeat
            current_incr = current_incr + incr_us

    # Make sure the pattern always ends at 0, so it can be repeated
    point_level = 0
    if set12V:
        logging.debug(f"Sending command 'sig:12v:pat:add {str(point_time)}uS {str(point_level)} i")
        myModule.sendCommand("sig:12v:pat:add " + str(point_time) + "uS " + str(point_level) + " i")
    if set5V:
        logging.debug(f"Sending command 'sig:5v:pat:add {str(point_time)}uS {str(point_level)} i")
        myModule.sendCommand("sig:5v:pat:add " + str(point_time) + "uS " + str(point_level) + " i")


if __name__ == "__main__":
    main()

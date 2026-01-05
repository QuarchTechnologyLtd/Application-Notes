'''
AN-001 - Application note demonstrating manual manipulation of signals to create a 
custom glitch/drive event, where precise timing is not critical

This was designed for a QTL1630/QTL1688 PCIe x16 Slot breaker, but can be easily
modified for any breaker by tweaking the signal names used in the script.

In this customer example, there was a requirement to sequence PERST#, SSD +12V and REFCLK. 

This uses the quarchpy python package and demonstrates
- Connecting to a module
- Setting up driving options
- Running a timed sequence to control the signals

########### VERSION HISTORY ###########

19/09/2017 - Tom Pope       - Moved to QuarchPy library
21/03/2018 - Pedro Cruz     - Re-written against quarchpy 1.0
29/03/2018 - Andy Norrie    - Minor edits for formatting and layout
24/04/2018 - Andy Norrie    - Updated from functional to object form
12/05/2021 - Matt Holsey    - Fixed power margining bug - 3v3 vs 5v rail
25/01/2023 - Andy Norrie    - Reviewed code and updated requirements and instructions

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
2- Connect a Quarch module to your PC via USB, Serial or LAN and power it on
3- Run the script and follow the instructions on screen

####################################
'''

# Import other libraries used in the examples
import time     # Used for sleep commands
import logging  # Optionally used to create a log to help with debugging

# '.device' provides connection and control of modules
from quarchpy.device import *
from quarchpy.user_interface import user_interface


def main():

    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    #logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    
    print ("\n\nQuarch application note example: AN-001")
    print ("---------------------------------------\n\n")

    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print ("Scanning for devices...\n")
    deviceList = scanDevices('all', favouriteOnly=False)

    # You can work with the deviceList dictionary yourself, or use the inbuilt 'selector' functions to help
    # Here we use the user selection function to display the list on screen and return the module connection string
    # for the selected device
    moduleStr = userSelectDevice(deviceList,additionalOptions = ["Rescan","All Conn Types","Quit"], nice=True)
    if moduleStr == "quit":
        return 0

    # If you know the name of the module you would like to talk to then you can skip module selection and hardcode the string.
    #moduleStr = "USB:QTL1999-05-005"

    # Create a device using the module connection string
    print("\n\nConnecting to the selected device")
    myDevice = getQuarchDevice(moduleStr)    
    print ("\nConnected to module: " + myDevice.sendCommand("hello?"))

    # Set the module into its defualt initial 
    myDevice.sendCommand("conf:def state")
    
    # assign all signals to source 8 so they are always connected.  This allows us to avoid changing
    # the signals we want to leave alone for this test
    myDevice.sendCommand("sig:all:source 8")

    # Assign the signals we want to change to the timed sources (1-6 can be used for this)
    # The signals we want to move together are assigned to the same source so they are affected
    # at exactly the same time.  This example can be quickly changed for other modules or tests by
    # tweaking the assignments here
    print ("Assign the signals we want to control, to the correct sources:")
    commandResult = myDevice.sendCommand("sig:PERST:source 1")
    print ("Setting PERST to source 1: " + commandResult)    
    commandResult = myDevice.sendCommand("sig:12V_POWER:source 2")
    print ("Setting REFCLK_MN to source 2: " + commandResult)
    commandResult = myDevice.sendCommand("sig:REFCLK_MN:source 2")
    print ("Setting REFCLK_PL to source 2: " + commandResult)
    commandResult = myDevice.sendCommand("sig:REFCLK_PL:source 2")   

    # By default signals transition from plugged (connected) to pulled (isolated).  We can also
    # use 'driving' on breakers that support it.  This allows us to activly drive supported sideband signals
    # ensuring they transition to the state we require.  Here we ensure PERST is pulled down to reset the drive
    # when the switch would otherwise be open:
    # This command drives PERST 'LOW' when the switch is open
    print ("\nSetting up driving for the PERST signal")
    myDevice.sendCommand("SIGnal:PERST:DRIve:OPEn LOW")
    # THis command drives PERST 'HIGH' when the switch is closed
    myDevice.sendCommand("SIGnal:PERST:DRIve:CLOsed HIGH")
    
    # We want to change the state of all signals on a source at the same time, and with the minimum
    # number of commands, so we avoid any unwanted additional delays. To do this, we use the source 'enable'
    # setting.  When a timed source is turned 'off', the signals assigned to it are pulled (and they are 'plugged'
    # when the source is turned on).  With a few sleep commands, we can create the required event:
    print ("\nRunning the timing sequence, this will take a few seconds...")
    myDevice.sendCommand("source:1:STATE off")
    time.sleep(0.4);
    myDevice.sendCommand("source:1:STATE on")
    time.sleep(4.5);
    myDevice.sendCommand("source:1:STATE off")
    time.sleep(0.4);
    myDevice.sendCommand("source:2:STATE off")
    time.sleep(1.6);
    myDevice.sendCommand("source:2:STATE on")
    time.sleep(0.2);
    myDevice.sendCommand("source:1:STATE on")
    time.sleep(6);
    myDevice.sendCommand("source:1:STATE off")
    time.sleep(0.6);
    myDevice.sendCommand("source:2:STATE off")
    time.sleep(3.8);
    myDevice.sendCommand("source:2:STATE on")
    time.sleep(0.2);
    myDevice.sendCommand("source:1:STATE on")

    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    myDevice.closeConnection()

    print("\n\nTest complete!")

if __name__== "__main__":
    main()















'''
AN-002 - Simulating physical layer faults

This application note demonstrates the use of a Quarch breaker module to inject standard forms
of physical layer faults onto a high speed data bus such as SAS, SATA or PCIe.

It will work with any quarch breaker module BUT you will have to tweak the signal names
depending on the module you are using as SAS and PCIe use different naming conventions.

The example is also relevant for many other interfaces, such as USB, CAN and RJ-45

This uses the quarchpy python package and demonstrates
- Connecting to a module
- Running a series of fault injections

NOTE: For simplicity, the fault tests are run in sequence.  In the real world, any of the tests might cause
the device under test to reset or fault, so if you are using this against a real device, you should probably 
comment out all but one of the test examples.

This example only creates the fault scenario.  It would be up to you to determine the effect on your device and
if it responded/recovered correctly

########### VERSION HISTORY ###########

25/01/2023 - Andy Norrie    - Reviewed code and updated requirements and instructions

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on Windows only)
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

import quarchpy
# '.device' provides connection and control of modules
from quarchpy.device import *
from quarchpy.user_interface import quarchSleep

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.
    
    print ("\n\nQuarch application note example: AN-002")
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
        
    # Setup the glitch engine for the later examples which use it.
    SetupGlitch(myDevice)

    # Comment out any of the following functions you do not wish to run, each example is seperate so can be removed without affecting the others

    # Run the randon disruption sequence
    RandomDisruption(myDevice)

    # Fault one side of a differential pair
    FaultPair(myDevice)

    # Fault an entire lane
    FaultLane(myDevice)

    # Create a simple glitch
    SimpleGlitch(myDevice)
    
    print ("\n\nApplication note example complete!")
    

# Setup glitch module, to glitch all signals in Lane 1, with a glitch length of 1mS
# Edid the 'Lane0' name if you are using a different module, see the 'HELP NAMES' command
# or the technical manual for details
def SetupGlitch(myDevice):
    print ("\nSetting up the glitch engine")
    result = myDevice.sendCommand("SIGnal:Lane0:GLITch:Enable ON")
    print ("Enabling glitch for chosen signal(s): " + result)
    
    # 1mS = 5uS x 200, based on the allowed settings in the technical manual
    result = myDevice.sendCommand("GLITch:SETup 5uS 200")
    print ("Setting the length of the glitch to 1mS: " + result)       


# Create a random disruption, using the PRBS generator to inject errors at a set rate
def RandomDisruption(myDevice):
    print ("\nRunning PRBS disruption example")

    # Set PRBS rate to glitch at an average rate of 1:16,384.  The glitches will be placed randomly using a standard PRBS sequence
    # This is a rate of 2^14
    result = myDevice.sendCommand("GLITch:PRBS 16384")
    print ("Set the glitch ratio (2^14): " + result)       
    
    result = myDevice.sendCommand("RUN:GLITch PRBS")
    print ("Activate the glitch generator: " + result)  
    
    # Continue to glitch for 20 seconds, we use a progress bar for tracking
    print ("\nWait for 20 seconds while the test runs")
    quarchSleep (20)
   
    result = myDevice.sendCommand("RUN:GLITch STOP")
    print ("Stop the glitch event at the end: " + result)            



# Create a fault on one side of a differential pair, in this case we have created a fault on lane 1, TX1_Pl
# The signal name 'TX1_PL' may need changed depending on the breaker you are using to run this test
def FaultPair(myDevice):
    print ("\nStarting test to fault one side of a differential pair")
    
    # Assign the signal to source 0 (always off) which will immediately disconnet the signal
    result = myDevice.sendCommand("SIGnal:TX1_PL:SOURce 0")
    print ("Assign the signal to source 0 (always off): " + result)     
    
    print ("\nWait for 20 seconds while the test runs")
    quarchSleep (20)
    
    # Return the signal to its default source, to re-connect it
    result = myDevice.sendCommand("SIGnal:TX1_PL:SOURce 1")
    print ("Assign the signal to source 1 to reconnect it: " + result)         

    
# Create a fault in an entire lane, in this case we have created a fault on lane 1
# The signal name 'Lane0' may need changed depending on the breaker you are using to run this test
def FaultLane(myDevice):

    print ("\nStarting test to fault one lane")
    
    result = myDevice.sendCommand("SIGnal:Lane0:SOURce 0")
    print ("Assign the lane to source 0 (always off): " + result)   

    print ("\nWait for 20 seconds while the test runs")
    quarchSleep (20)
    
    # Return the signals to their default source, to re-connect them
    result = myDevice.sendCommand("SIGnal:Lane0:SOURce 1")
    print ("Assign the lane to source 1 to reconnect it: " + result)   


# Creating a simple glitch, using the current glitch settings.  This will create a single glitch which may cause data corruption, framing errors, SAS identify or many similar errors
# depending on the length of the glitch and the exact time that the glitch is run.  To time a glitch precisely within the data stream, you would require a module that supports external triggering so an
# analyser can be used to trigger the glitch at a precise point.
def SimpleGlitch(myDevice):
    print ("\nStarting test to inject a single glitch:")
    
    # Create a single glitch, using the current glitch length and glitch enable settings
    result = myDevice.sendCommand("RUN:GLITch ONCE")
    print ("Creating a single glitch now: " + result)       


if __name__== "__main__":
    main()
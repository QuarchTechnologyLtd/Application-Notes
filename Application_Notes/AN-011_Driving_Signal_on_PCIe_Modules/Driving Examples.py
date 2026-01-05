'''
AN-011 - Application note demonstrating the driving feature of breaker modules

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Setting up driving functions and combining them with other features

########### VERSION HISTORY ###########

15/02/2023 - Andy Norrie    - Reviewed code and updated requirements and instructions

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
from quarchpy.user_interface import quarchSleep

''' 
Simple example code, specifically targeted at a GEN5 U.2 breaker module (QTL2651)
but could be adapted for any module which supports driving, by selecting
a signal name that is present on your specific module
'''
def main():

    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    
    print ("Quarch application note example: AN-011")
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
    #moduleStr = "USB:QTL2651-03-005"

    # Create a device using the module connection string
    print("\n\nConnecting to the selected device")
    myDevice = getQuarchDevice(moduleStr)
    
    print("Module Name:")
    print(myDevice.sendCommand("hello?"))
    
    # NOTE: You can set these to any signal on your breaker which supports driving!
    myPerstSignal = "PERST"
    
    # Example functions here, comment any in/out as you like, they can all run independantly!
    
    # Resets the drive once
    ResetDrive (myDevice, myPerstSignal);
    # Resets the drive once per second for n seconds
    CyclingReset (myDevice, myPerstSignal, 10);
    

    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    myDevice.closeConnection()
    
    print("Test finished!")


'''
Uses a 100mS glitch from the glitch engine to combine with the driving feature to drive the PERST signal low for 100mS
'''
def ResetDrive(myDevice, myDrivingSignal):
    print ("\nBeginning simple drive reset test\n")
    # Ensure we are in the default state at the beginning of the test
    print("Set module to default state: " + myDevice.sendCommand("conf:def state"))

    # Example: Use glitch engine to assert PERST to the drive for 100mS
    print ("Setup signal to drive low for 100mS")
    # Configure the signal to drive LOW when the switch would normally be open (signal disconnected/pulled state)
    callResult = myDevice.sendCommand("signal:" + myDrivingSignal + ":drive:open low")
    # Error (will occur if the module selected does not support this signal)
    if ("FAIL" in callResult):
        print ("ERROR - failed to set drive mode for the signal: " + callResult)
    # Enable the signal for glitching
    myDevice.sendCommand("signal:" + myDrivingSignal + ":glitch:enable on")
        
    # Setup the glitch engine to create a 100mS glitch event.  Glitches are created by a time period and multiplier
    # here we are using the 500uS interval and 200x multiplier to reach 100mS
    myDevice.sendCommand("glitch:setup 500us 200")
    
    # We create the actual glitch here, which will immediately cause the PERST line to be pulled low for 100mS
    print ("Resetting the drive now!!")
    myDevice.sendCommand("run:glitch once")
    
    print ("Delay for drive to re-enumerate after reset...")
    quarchSleep(5)
    
'''
Uses a 100mS glitch from the glitch engine to combine with the driving feature to drive the PERST signal low for 100mS
We then use the glitch 'cycle' function to repeat the glitches in a set pattern.  This is designed to stress the drive by resetting
it multiple times
'''
def CyclingReset(myDevice, myDrivingSignal, testTime):
    print ("\nBeginning cycling reset test\n")
    # Ensure we are in the default state at the beginning of the test
    print("Set module to default state: " + myDevice.sendCommand("conf:def state"))

    # Example: Use glitch engine to assert PERST to the drive for 100mS
    print ("Setup signal to drive low for 100mS")
    # Configure the signal to drive LOW when the switch would normally be open (signal disconnected/pulled state)
    callResult = myDevice.sendCommand("signal:" + myDrivingSignal + ":drive:open low")
    # Error (will occur if the module selected does not support this signal)
    if ("FAIL" in callResult):
        print ("ERROR - failed to set drive mode for the signal: " + callResult)
    # Enable the signal for glitching
    myDevice.sendCommand("signal:" + myDrivingSignal + ":glitch:enable on")
        
    # Setup the glitch engine to create a 100mS glitch event.  Glitches are created by a time period and multiplier
    # here we are using the 500uS interval and 200x multiplier to reach 100mS
    myDevice.sendCommand("glitch:setup 500us 200")
    
    # The cycle time is the delay betwen cycled glitches, and uses the same setting mechanism, we are aiming for 1000mS here
    myDevice.sendCommand("glitch:cycle:setup 5ms 200")
    
    # We begin the glitch events here, PERST will be pulled down for 100mS, with a gap of 1 Second between each glitch    
    myDevice.sendCommand("run:glitch cycle")
    
    print ("Waiting while the repeated glitches are running")
    quarchSleep(testTime)
    myDevice.sendCommand("run:glitch stop")
    
    print ("Delay for drive to re-enumerate after final reset...")
    quarchSleep(5)




    
if __name__== "__main__":
    main()

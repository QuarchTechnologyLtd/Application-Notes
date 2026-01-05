'''
Part of the Triggering Application Note 

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Runs a simple script for setting PPM to ground upon PERST ASSERT


########### VERSION HISTORY ###########

12/12/2024 - Damir Kadyrzhan - First version. Reviewed by Nabil Ghayyda

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
2- Connect Breaker Module that support triggering
3- Connect PPM and Quarch Interface Unit with USB to control PC 
4- Connect Power cables to PPM and Quarch Interface Unit 
5- Run the script and follow the instructions on screen
6- Refer to hardware triggering notes set-up section for an illustration

####################################
'''

# Import other libraries used in the examples
import time     # Used for sleep commands
import logging  # Optionally used to create a log to help with debugging

# '.device' provides connection and control of modules
from quarchpy.device import *
from quarchpy.user_interface import quarchSleep


'''
Simple script that first configures Breaker to trigger out upon power down (PERST).
Then configures PPM to external trigger to set 12V to GND. 
This script can be configured in multiple ways for example to set GND to 12V on PPM once powered up
'''
def main():
    
    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    
    print ("Quarch application note example: Triggering")
    print ("---------------------------------------\n\n")
    
    
    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print ("Scanning for devices...\n, connect to Breaker")
    deviceList = scanDevices('all', favouriteOnly=True)
    
    # You can work with the deviceList dictionary yourself, or use the inbuilt 'selector' functions to help
    # Here we use the user selection function to display the list on screen and return the module connection string
    # for the selected device
    moduleStr = userSelectDevice(deviceList,additionalOptions = ["Rescan","All Conn Types","Quit"], nice=True)
    if moduleStr == "quit":
        return 0
    
    # Create a device using the module connection string
    print("\n\nConnecting to the selected device")
    myBreakerDevice = getQuarchDevice(moduleStr)
    
    # Print the device name after the selection 
    print("Module Name:")
    print(myBreakerDevice.sendCommand("hello?"))
    
    # Execute breaker configuration function
    BreakerConf(MyBreakerDevice)
    
    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    myBreakerDevice.closeConnection()
    
    
    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print ("Scanning for devices...\n, connect to PPM")
    deviceList = scanDevices('all', favouriteOnly=True)
    
    # You can work with the deviceList dictionary yourself, or use the inbuilt 'selector' functions to help
    # Here we use the user selection function to display the list on screen and return the module connection string
    # for the selected device
    moduleStr = userSelectDevice(deviceList,additionalOptions = ["Rescan","All Conn Types","Quit"], nice=True)
    if moduleStr == "quit":
        return 0
    
    # Create a device using the module connection string
    print("\n\nConnecting to the selected device")
    myPPMDevice = getQuarchDevice(moduleStr)
    
    # Print the device name after the selection 
    print("Module Name:")
    print(myPPMDevice.sendCommand("hello?"))
    
    # Execute PPM configuration function
    PPMConf(myPPMDevice)
    
    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    myPPMDevice.closeConnection()
    
    print("Test finished, Try POWER DOWN the Breaker, 12V on PPM will be pulled to GND")
    

'''
Function that configures the Breaker to have all signals to be active except of the PERST
When the breaker is pulled then it will send the trigger out to PPM
'''
def BreakerConf(myBreakerDevice):
    myBreakerDevice.sendCommand("conf def state") # Sets to default state
    myBreakerDevice.sendCommand("SIGNAL:ALL:SOURCE 8") # Sets all signals to source 8 (always on)
    myBreakerDevice.sendCommand("SIGNAL:PERST:SOURCE 4") # Sets PERST# to Source 4
    myBreakerDevice.sendCommand("SIGNAL:PERST:DRIVE:OPEN LOW") # When PERST is discounted, module will drive device side LOW
    myBreakerDevice.sendCommand("TRIGGER:OUT:INVERT ON") # Need to invert so it triggers on power down
    myBreakerDevice.sendCommand("TRIGGER:OUT:MODE POWER") # Trigger out on power event
    
    
'''
Function that configures PPM to once the trigger is received to pull 12V to GND
'''
def PPMConf(myPPMDevice):
    myPPMDevice.sendCommand("conf def state") # Sets to default state
    time.sleep(6) # Wait for 6 seconds before proceeding. Because PPM needs time to reset the registers
    myPPMDevice.sendCommand("RUN POWER UP") # Turns on the power
    myPPMDevice.sendCommand("CONFIG:OUTPUT:12V:PULLDOWN ON") # Enables pull down
    myPPMDevice.sendCommand("SIGNAL:12V:PATTERN:ADD 0S -12000") # Adds the pattern, when the voltage goes from 12V to 0V the delay of the drop is 0 seconds.
    myPPMDevice.sendCommand("PATTERN:TRIGGER:EXTERNAL:TYPE:EDGE") # Sets trigger in to trigger on an edge
    myPPMDevice.sendCommand("PATTERN:TRIGGER:EXTERNAL ON") # Pattern above will be only triggered externally

if __name__== "__main__":
    main()
    

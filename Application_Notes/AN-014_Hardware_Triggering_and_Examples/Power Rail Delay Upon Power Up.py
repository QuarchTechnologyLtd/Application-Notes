'''
Part of the Triggering Application Note 

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Runs a simple script for delaying the power rails. 


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
2- Connect PCIe Module that supports triggering
3- Connect Quarch Interface Unit with USB to control PC 
4- Connect the Power cable Quarch Interface Unit 
5- Run the script and follow the instructions on screen
6- Refer to hardware triggering note set-up section for an illustration

####################################
'''

# Import other libraries used in the examples
import time     # Used for sleep commands
import logging  # Optionally used to create a log to help with debugging

# '.device' provides connection and control of modules
from quarchpy.device import *
from quarchpy.user_interface import quarchSleep


'''
Script that sets 12V and 3v3 power rails to delay each other. To run the specific test scenarios. 
The delay can be configured to suit the customer's requirements. 
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
    
    # Print the device dame after the selection 
    print("Module Name:")
    print(myBreakerDevice.sendCommand("hello?"))

    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    myBreakerDevice.closeConnection()

    print("Test finished, Try POWER DOWN the Breaker, 12V on PPM will be pulled to GND")
    
    
    '''
    Function that sets all signals to active except of 12V and 3V3 power rails. 
    12V is set to Source 1 and 3v3 to Source 2, meaning the delay can be configured in any way. 
    The delay can be put longer or shorter than 50ms. 
    The delay will happen on the power up. 
    '''
def BreakerConf(myBreakerDevice):
    myBreakerDevice.sendCommand("conf def state") # Sets to default state
    time.sleep(6) # Wait for 6 seconds before proceeding. Because Breaker needs time to reset the registers
    myBreakerDevice.sendCommand("SIGNAL:ALL:SOURCE 8") # Sets all signals to active high
    myBreakerDevice.sendCommand("SIGNAL:12v_power:SOURCE 1") # Sets 12V to Source 1
    myBreakerDevice.sendCommand("SIGNAL:3v3_power:SOURCE 2") # Sets 3v3 to Source 2
    myBreakerDevice.sendCommand("SOURCE 1 DELAY 50") # Delay Source 1 by 50ms
    myBreakerDevice.sendCommand("SOURCE 2 DELAY 100") # Delay Source 2 by 100ms
    myBreakerDevice.sendCommand("TRIGGER:OUT:MODE:POWER") # Trigger out on power event
     
if __name__== "__main__":
    main()

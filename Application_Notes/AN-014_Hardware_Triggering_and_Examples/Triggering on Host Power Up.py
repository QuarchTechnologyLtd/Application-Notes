'''
AN-014 - Application note demonstration the triggering feature of the breaker

This uses the quarchpy python package and demonstrates
- Scanning for modules
- Connecting to a module
- Runs a simple script for the breaker and PPM, setting up the host power up


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
3- Connect PPM and Quarch Interface Unit with USB to control PC 
4- Connect Power cables to PPM and Quarch Interface Unit 
5- Run the script and follow the instructions on screen
6- Refer to AN-014 set-up section for an illustration

####################################
'''

# Import other libraries used in the examples
import time     # Used for sleep commands
import logging  # Optionally used to create a log to help with debugging

# '.device' provides connection and control of modules
from quarchpy.device import *
from quarchpy.user_interface import quarchSleep


'''
Simple script that first configures Breaker to trigger out on 12V Host power event.
Then configures PPM to external trigger. 
PPM also configured to perform glitches on 3v3 upon host power up.
'''

def main():
    
    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    
    print ("Quarch application note example: AN-014 Triggering")
    print ("---------------------------------------\n\n")
    
    
    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print ("Connect to Breaker. Scanning for Devices...\n")
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
    
    # Sets to default state
    myBreakerDevice.sendCommand("conf def state") 

    # Wait for 6 seconds before proceeding. Because PPM needs time to reset the registers
    time.sleep(6) 
    
    # Trigger out on power event. Sets the module to Trigger Out on 12V Host Power Up
    myBreakerDevice.sendCommand("TRIGger:OUT:MODE:12V_Host")
    
    
    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    myBreakerDevice.closeConnection()
    
    
    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    print ("Connect to PPM. Scanning for devices...\n")
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
    
    
    # Print the device dame after the selection 
    print("Module Name:")
    print(myPPMDevice.sendCommand("hello?"))
    
    # Configures PPM to respond on an external trigger
    HostPowerUp(myPPMDevice)
    
    # Close the module before we go round the loop to try another test
    # The module should always be closed when you are finished using it
    myPPMDevice.closeConnection()
    print("Test finished, try running QPS on Control PC and run the HOST PC. 12V and 3V3 on PPM should power up")
    
    
'''
- Sets the PPM to respond on an external Trigger
- Configures PPM to glitch 3V3 line during the host power up
'''
def HostPowerUp(myPPMDevice):
    # Sets to default state
    myPPMDevice.sendCommand("conf def state") 
    # input("Press Enter to Continue") # Optional input 
    # Wait for 6 seconds before proceeding. Because PPM needs time to reset the registers
    time.sleep(6) 
    # Turns on the power
    myPPMDevice.sendCommand("RUN POWER UP")
    # Set the output voltage to 0
    myPPMDevice.sendCommand("SIGNAL:12V:VOLTAGE 0") 
    myPPMDevice.sendCommand("SIGNAL:3v3:VOLTAGE 0")
    # Add a pattern to slowly ramp the 12V and 3v3 over 50ms
    myPPMDevice.sendCommand("SIGNAL:12V:PATTERN:ADD 50mS 12000 i") 
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 50mS 3300 i")
    # Add a pattern for 3v3 which glitches 3 times. Then keeps the 3v3 ON
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 100mS 3000") 
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 150ms 0") 
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 200ms 3000")       
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 250mS 0")      
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 300mS 3000")              
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 350mS 0") 
    myPPMDevice.sendCommand("SIGNAL:3v3:PATTERN:ADD 400mS 3300") 
    # Set to run the pattern on an external trigger
    myPPMDevice.sendCommand("PATTERN:TRIGGER:EXTERNAL ON") 
    # Set the type of the trigger to EDGE
    myPPMDevice.sendCommand("PATTERN:TRIGGER:EXTERNAL TYPE EDGE")
    
    

     
if __name__== "__main__":
    main()

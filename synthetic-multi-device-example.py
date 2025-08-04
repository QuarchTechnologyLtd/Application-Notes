"""
AN-032 - Application note demonstrating automated setup and streaming from two modules at once

This example demonstrates how to select to Quarch two power modules and combine them together into
a 'Synthetic' device that can combine the data from both into a single analysis.  
This can be used to increase the number of channels you can measure, it can also be used to 
combine AC and DC instruments into one trace (as an example)

########### VERSION HISTORY ###########

004/08/2025 - Andy Norrie    - First Version

########### REQUIREMENTS ###########


1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on Windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/
5- Java 8, with JaxaFX
    https://quarch.com/support/faqs/java/

########### INSTRUCTIONS ###########

1- Connect two Quarch modules to your PC via USB or LAN and power them on.
2- Enter the IDs of the devices in the code below
3- Run the script and follow the instructions on screen.

####################################
"""

# Import other libraries used in the examples
import time     # Used for sleep commands
import logging  # Optionally used to create a log to help with debugging
import subprocess
import os

from quarchpy.device import *
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.user_interface.user_interface import quarchSleep

# ACTION: Set the devices you want to connect to here
# The first device is the primary one and will be used
# to setup the main controls in QPS
Device1 = "USB::QTL2843-02-001"     # ID of the primary device
Device2 = "USB::QTL2312-01-219"     # ID of the additional device
SyntheticName = "Combi"             # Name of the virtual device
SyntheticDescrip = "PAM + PPM"      # Additional description text for the device

myDeviceID = "VIRT::" + SyntheticName

def main():
    # Put this line back in to enable debug logging if you require
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

    print ("\n\nMulti-device QPS example")
    print ("---------------------------------------\n\n")    

    # Checks if QPS is running on the localhost
    if isQpsRunning() is False:
        # Start QPS from quarchpy
        startLocalQps()
    
    # Connect to the localhost QIS instance
    myQps = qpsInterface()
    print ("QIS Version: " + myQps.sendCommand('$version'))
    
    # Set both device averages to match
    print ("Set averaging")    
    print (myQps.sendCommand(Device1 + " stream mode resample 1ms"))
    print (myQps.sendCommand(Device2 + " stream mode resample 1ms"))                
    
    print ("Create device")
    print (myQps.sendCommand("$create device " + SyntheticName + " newDevice( \"" + SyntheticDescrip + "\" device(" + Device1 + ", PAM) device(" + Device2 + ", PPM) )"))      
    
    # Set default power path to the local folder and use the date/time as the analysis folder name
    filePath = os.path.dirname(os.path.realpath(__file__))
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
    print("File output path set: " + str(os.path.join(filePath, fileName)))

    # Start the stream, which will show live data being captured in QPS
    myStream = myQps.startStream(os.path.join(filePath, fileName))
    quarchSleep (30, title="Capturing data")

    # After the set time, end the stream
    myStream.stopStream()    



# Calling the main() function
if __name__=="__main__":
    main()
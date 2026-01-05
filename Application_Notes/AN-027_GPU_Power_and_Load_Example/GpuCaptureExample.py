"""
AN-015 - Application note demonstrating automated control over Quarch Power Studio (QPS)

This example demonstrates adding annotations and datapoints to a QPS stream.

########### VERSION HISTORY ###########

03/10/2023 - Andy Norrie    - First Version.

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
6- Pywin32 library
    > pip install pywin32
6- Quarch GPU PAM or similar, set to measure GPU power consumption

########### INSTRUCTIONS ###########

1- Connect the Quarch module to your PC via USB or LAN and power it on.
2- Run the script and follow the instructions on screen.
3- For localhost QPS, run the example as it is.

####################################
"""

# Import other libraries used in the examples
import os
import time
import win32com.client
import logging

# Import QPS functions
from quarchpy import qpsInterface, isQpsRunning, startLocalQps, GetQpsModuleSelection, getQuarchDevice, quarchDevice, quarchQPS, \
    requiredQuarchpyVersion    


def main():
    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

    print("\n\nQuarch application note example: AN-027")
    print("---------------------------------------\n\n")

    # Version 2.0.15 or higher expected for this application note
    requiredQuarchpyVersion("2.0.15")

    # File paths for the example are set here, and can be altered to put your data files in a different location
    # The path must be writable via a standard OS path
    filePath = os.path.dirname(os.path.realpath(__file__))

    # Checks if QPS is running on the localhost
    if isQpsRunning() is False:
        # Start QPS from quarchpy
        startLocalQps()

    # Connect to the localhost QPS instance - you can also specify host='127.0.0.1' and port=xxxx for remote control.
    # This is used to access the basic functions, allowing us to scan for devices.
    myQps = qpsInterface()

    # Display and choose module from found modules.
    # This returns a String with the connectionTarget to the device; eg USB::QTL1999-05-005 or TCP::192.168.1.1
    myDeviceID = GetQpsModuleSelection(myQps)

    # If you know the name of the module you would like to talk to then you can skip module selection and hardcode the string.
    # moduleStr = "USB:QTL1999-05-005"

    # Convert module to Quarch module
    print("\n\nConnecting to the selected device")
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType="QPS")

    # Create the device connection, as a QPS connected device
    myQpsDevice = quarchQPS(myQuarchDevice)
    myQpsDevice.openConnection()

    # Prints out connected module information
    print("\nConnected to module: " + myQpsDevice.sendCommand("hello?"))

    # Setup the voltage mode and enable the outputs
    setupPowerOutput(myQpsDevice)

    # Set the averaging rate for the module. This sets the resolution of data to record.
    # This is done via a direct command to the power module.
    print(myQpsDevice.sendCommand("record:averaging 32k"))

    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())    
    myStream = myQpsDevice.startStream(os.path.join(filePath, fileName))
    print("File output path set: " + str(os.path.join(filePath, fileName)))
    
    # Create performance channels, give them simple names for now as the full names are very long and complex
    gpuChannels = getSysterPerformanceItems ()
    num = 0
    for channel in gpuChannels:        
        print (myStream.createChannel ("GPU_" + str(num), 'Perf_' + str(num), '%', False))
        print ("Creating custom performance channel: " + "GPU_" + str(num) + " - For: " + channel)
        num = (num + 1)

    # Now poll for the GPU data once per second and add it to the chart
    # We're assuming the results are in the same order as the channels were created.  This is not ideal but avoids more
    # complex code in this simple example
    for x in range (300):
        perfValues = pollSystemPerformanceItems (gpuChannels)
        # For each performance metric, add the new data point (at the current/live stream time)
        num = 0
        for result in perfValues:            
            myStream.addDataPoint("GPU_" + str(num), 'Perf_' + str(num), str(result.UtilizationPercentage))
            print ("Adding value for channel: " + "GPU_" + str(num) + " - of: " + str(result.UtilizationPercentage))
            num = (num + 1)
        
    # End the stream and tidy up
    myStream.stopStream()

# Query win32 data to get the avaialble GPU metrics on this system
def getSysterPerformanceItems():
    perfItems = []
    wmi = win32com.client.GetObject("winmgmts:root\cimv2")
    # Get all GPU metrics
    counter_name = "GPUEngine"
    query = f"SELECT * FROM Win32_PerfFormattedData_GPUPerformanceCounters_{counter_name}"
    
    # For simplicity, filter for metrics that are showing a non-zero value as 'many' are found
    for item in wmi.ExecQuery(query):    
        if (int(item.UtilizationPercentage) > 0):
            perfItems.append (item.Name)

    return perfItems
    
# Poll for the current value of one or more performance item names, returns the list of performance items
def pollSystemPerformanceItems (requestItems):
    perfResults = []
    wmi = win32com.client.GetObject("winmgmts:root\cimv2")
    # Get all GPU metrics
    counter_name = "GPUEngine"
    query = f"SELECT * FROM Win32_PerfFormattedData_GPUPerformanceCounters_{counter_name}"
    
    for item in wmi.ExecQuery(query):    
        if item.Name in requestItems:
            perfResults.append (item)

    return perfResults

'''
Simple function to check the output mode of the power module, setting it to 3v3 if required
then enabling the outputs if not already done.  This will result in the module being turned on
and supplying power.
'''
def setupPowerOutput(myModule):
    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    outModeStr = myModule.sendCommand("config:output mode?")
    if "DISABLED" in outModeStr:
        try:
            drive_voltage = raw_input(
                "\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"
        except NameError:
            drive_voltage = input(
                "\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"

        myModule.sendCommand("config:output:mode:" + drive_voltage)

    # Check the state of the module and power up if necessary
    powerState = myModule.sendCommand("run power?")
    # If outputs are off
    if "OFF" in powerState or "PULLED" in powerState:  # PULLED comes from PAM
        # Power Up
        print("\n Turning the outputs on:"), myModule.sendCommand("run:power up"), "!"


# Calling the main() function
if __name__=="__main__":
    main()
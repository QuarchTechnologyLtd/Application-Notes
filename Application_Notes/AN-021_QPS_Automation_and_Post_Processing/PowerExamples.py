#!/usr/bin/env python
'''
This example demonstrates basic automation with QPS and post processing of raw data after recording.
We will record at a high rate and post process down to a lower rate, ending with 100uS and 500uS sample rates

########### VERSION HISTORY ###########

03/10/2019 - Andy Norrie     - First Version
18/10/2024 - Nabil Ghayyda   - Updated Header

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

1- Connect a Quarch power module to your PC via USB or LAN and power it on
2- Ensure quarcypy is installed
2- On startup, select the options for the device you wish to test

####################################
'''

import os
import time

import quarchpy
from quarchpy.device import *
from quarchpy.qps import *

# Path where stream will be saved to (defaults to current script path)
streamPath = os.path.dirname(os.path.realpath(__file__))

'''
Main function, containing the example code to execute
'''
def main():

    # Required min version for this application note
    quarchpy.requiredQuarchpyVersion ("2.0.9")
    
    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    print("\n\nQuarch application note example: AN-021")
    print("---------------------------------------\n\n")

    print ("-Starting QPS")
    # Checks is QPS is running on the localhost
    if not isQpsRunning():
    # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps(keepQisRunning=True)    

    # Open an interface to local QPS
    myQps = qpsInterface()
    
    print ("-Requesting module selection")
    # Module to work with
    myDeviceID = GetQpsModuleSelection (myQps)

    # Create a Quarch device connected via QPS
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType = "QPS")
    
    # Upgrade Quarch device to QPS device
    myQpsDevice = quarchQPS(myQuarchDevice)
    myQpsDevice.openConnection()

    # Prints out connected module information        
    print ("MODULE CONNECTED: \n" + myQpsDevice.sendCommand ("*idn?"))
    
    print ("-Waiting for drive to be ready")
    # Setup the voltage mode and enable the outputs. This is used so the script is compatible with older XLC modules which do not autodetect the fixtures
    setupPowerOutput (myQpsDevice)    
    # Wait for device to power up and become ready (you can start your workloads here if needed)
    time.sleep(5)
    
    print ("-Setting up module record parameters")
    # Set the averaging rate to the module to 16 (64uS) as the closest to 100uS
    msg = myQpsDevice.sendCommand ("record:averaging 16")   
    if (msg != "OK"):
        print ("Failed to set hardware averaging: " + msg)
    # Set the resampling mode to give us exactly 100uS
    msg = myQpsDevice.sendCommand ("stream mode resample 100us")
    if (msg != "OK"):
        print ("Failed to set software resampling: " + msg)

    print ("-Recording data...")
    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())        
    myStream = myQpsDevice.startStream (streamPath + "\\" + fileName)

    # Wait for a few seconds to record data then stop the stream
    time.sleep(5)    
    myStream.stopStream()
    # Wait for remaining stream data to save and complete, otherwise the export will fail
    time.sleep(2)   

    # Request raw CSV data from the stream, into the local folder (NOTE: current QPS does not support spaces in the export path)
    rawOutputPath = streamPath + "\\RawData100us.csv"
    export_command = "$save csv \"" + rawOutputPath + "\" -l1000000"
    print(export_command)
    msg = myQpsDevice.sendCommand (export_command)
    if (msg != "OK"):
        print ("Failed export CSV data: " + msg)

    # Run the post process step.  The first one is purely for the stats calculations, as we alredy have it in the correct sample rate
    print ("-Post processing step 1")
    post_process_resample (rawOutputPath, 1, streamPath + "\\PostData100us.csv")
    print ("-Post processing step 2")
    post_process_resample (rawOutputPath, 5, streamPath + "\\PostData500us.csv")
    print ("-Post processing step 3")
    post_process_resample (rawOutputPath, 10, streamPath + "\\PostData1ms.csv")

    
# Post process and resample the CSV file (for now assuming all data is in one file, QPS v1.09 maxes out at 100k lines right now in a single file, this limit will be removed in the next version)    
# Assumes first column is time and next (max 8) columns are data or empty, this could be automated by parsing the stream header to see the record channels and setting up dynamically
def post_process_resample (raw_file_path, resample_count, output_file_path):    
    # Init variables
    firstLine = True
    stripeCount = 0
    dilimiter = ","
    number_of_columns = 9
    averaged_stripe_count = 0
    # Storage for the accumulating data (9 columns of data)
    procData = [0,0,0,0,0,0,0,0,0]
    # Storage for the summary data (8 columns as time is note processed)
    maxData = [0,0,0,0,0,0,0,0]
    minData = [999999,999999,999999,999999,999999,999999,999999,999999]
    aveData = [0,0,0,0,0,0,0,0]
    # Open both the input and output files in appropriate access modes
    with open(raw_file_path, 'r') as rawFile:
        with open (output_file_path, 'w') as postFile:
            # Iterate through all input files
            for fileLine in rawFile:
                # headerline is unique, copy it directly
                if (firstLine == True):
                    postFile.write (fileLine + "\n")
                    firstLine = False
                    continue

                # Accumulate the required number of lines                
                lineSections = fileLine.split(dilimiter)
                # Update to the latest time point
                procData[0] = lineSections[0]
                # Sum the values for all other columns
                for i in range (1, number_of_columns):     
                    # Avoid crash on blank cells (happens with unused columns)
                    if (lineSections[i] != ''):
                        procData[i] += int(lineSections[i])
                stripeCount += 1

                # When we have enough data to complete one output line we can process it
                if (stripeCount == resample_count):
                    # Track the number of output stripes
                    averaged_stripe_count += 1

                    # Divide down the averaged colums to get the final result
                    for i in range (1, number_of_columns):                                    
                        procData[i] /= resample_count
                    # Generate the single line for the output file
                    outStr = dilimiter.join (str(x) for x in procData)
                    postFile.write (outStr + "\n")
                    # Track maximums
                    for i in range (1, number_of_columns):       
                        if (procData[i] > maxData[i-1]):
                            maxData[i-1] = procData[i]
                    # Track minimums
                    for i in range (1, number_of_columns):
                        if (procData[i] < minData[i-1]):
                            minData[i-1] = procData[i]
                    # Track averages (Note: large datasets may overflow this simple averaging mechanism)
                    for i in range (1, number_of_columns):                       
                        aveData[i-1] += procData[i]

                    # Reset the accumulating data buffer
                    procData = [0,0,0,0,0,0,0,0,0]    
                    stripeCount = 0

            # Complete the calculation of the average values
            for i in range (1, number_of_columns):                       
                aveData[i-1] /= averaged_stripe_count

            # Add the stats data to the bottom of the output file
            postFile.write ("\n\nSTATISTICS\n")
            postFile.write ("MAX," + dilimiter.join(str(x) for x in maxData) + "\n")
            postFile.write ("MIN," + dilimiter.join(str(x) for x in minData) + "\n")
            postFile.write ("AVE," + dilimiter.join(str(x) for x in aveData) + "\n")

'''
Function to check the output state of the module and prompt to select an output mode if not set already
'''
def setupPowerOutput (myModule):
    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    if "DISABLED" in myModule.sendCommand("config:output Mode?"):
        try:
            drive_voltage = raw_input("\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"
        except NameError:
            drive_voltage = input("\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"

        myModule.sendCommand("config:output:mode:"+ drive_voltage)
    
    # Check the state of the module and power up if necessary
    powerState = myModule.sendCommand ("run power?")
    # If outputs are off
    if "OFF" in powerState:
        # Power Up
        print ("\n Turning the outputs on:"), myModule.sendCommand ("run:power up"), "!"

if __name__=="__main__":
    main()

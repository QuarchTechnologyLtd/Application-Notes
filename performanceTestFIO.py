#!/usr/bin/env python
'''
AN-017 - Application note demonstrating FIO and QPS running traffic tests to a drive, with the power and performance data displayed.

- Uses quarchpy to automate QPS stream from quarch module, and kick off a FIO workload plotting data on QPS.

########### VERSION HISTORY ###########

10/09/2018 - Pedro Cruz   - First Version
15/09/2020 - Pedro Cruz   - Updated to support PAM
31/02/2023 - Stuart Boon - Updated format

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/
5- Install FIO (Go to releases and look for msi installer for windows or install CMD for linux version. )
    https://github.com/axboe/fio

########### INSTRUCTIONS ###########
1- Install the required items above
2- Connect a Quarch power module to your PC via USB or LAN
3- Run this script, select the options for the device you wish to test
4- Use the file dialogue to pick the location on the drive you would like to test. (WARNING This should NOT be on the same drive as you OS.)
####################################
'''

# Import modules and packages
import os
import time
import logging  # Optionally used to create a log to help with debugging
try: 
    #python 2.7
    import Tkinter, tkFileDialog
except:
    #python 3.7
    import tkinter
    from tkinter import filedialog
import quarchpy
from quarchpy.device import *
from quarchpy.qps import *
from quarchpy.fio import *
from quarchpy.user_interface.user_interface import visual_sleep
# We use TK for the directory selection box, this code avoids additional TK GUI items being shown
try:
    #python 3.7
    root = tkinter.Tk()
    tkFileDialog = filedialog
except:
    #python 2.7
    root = Tkinter.Tk()
root.withdraw()

# Path where stream will be saved to (defaults to current script path)
streamPath = os.path.dirname(os.path.realpath(__file__))

'''
Main function, containing the example code to execute FIO and display the results
'''
def main():

    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    #logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

    # Required min version for this application note
    quarchpy.requiredQuarchpyVersion ("2.0.0")
    
    # Display title text
    print ("\n################################################################################")
    print ("\n                           QUARCH TECHNOLOGY                        \n\n  ")
    print ("Automated power and performance data acquisition with Quarch Power Studio.   ")
    print ("\n################################################################################\n")  

    # Checks is QPS is running on the localhost
    if not isQpsRunning():
    # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps()

    # Open an interface to local QPS
    myQps = qpsInterface()
    
    # Select Quarch Module
    myDeviceID = GetQpsModuleSelection (myQps)

    # Create a Quarch device connected via QPS
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType = "QPS")
    
    # Upgrade Quarch device to QPS device
    myQpsDevice = quarchQPS(myQuarchDevice)
    myQpsDevice.openConnection()

    # Prints out connected module information        
    print ("MODULE CONNECTED: \n" + myQpsDevice.sendCommand ("*idn?"))
    
    '''
    NOTE: You may need a delay after this call, to allow your drive more time to enumerate on the system before
    are prompted to select the folder to use for FIO performance testing
    '''
    # Setup the voltage mode and enable the outputs (for PPM modules.)
    setupPowerOutput (myQpsDevice)
    
    # Get the required averaging rate from the user.  This sets the resolution of data to record        
    averaging = userInput("\n>>> Enter the average rate [1k]: ", "1k")
    
    # Set the averaging rate to the module
    cmdResponse=myQpsDevice.sendCommand ("record:averaging " + averaging)
    print("Sent:record:averaging " + averaging+"   Responded:"+cmdResponse)

    print ("\n>>> Select a folder for FIO Data:")
    # Request user to select the folder to use for FIO data
    try:
        testDirectory = tkFileDialog.askdirectory()
    except:
        testDirectory = userInput("Failed to open folder dialog, the enter the folder path for FIO to access\n>", None) #todo test this exception
    if testDirectory=="":
        raise Exception("No directory selected")

    print ("")
    print ("Selected : " + testDirectory)
    #FIO needs colons escaped when passing "directory" or "filename" look at FIO documentation online for more info.
    testDirectory = testDirectory.replace (":","\:")# escape colons from tkinter input.

    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())  
    streamLocation = os.path.join (streamPath, fileName)
    myStream = myQpsDevice.startStream (streamLocation)

    # Create new custom channels to plot IOPS results
    myStream.createChannel ('read_iops', 'IOPS', 'IOPS', "Yes")
    myStream.createChannel ('write_iops', 'IOPS', 'IOPS', "Yes")

    # hide unwanted default channels. This is commented out so you can see all default channels. Uncomment and change to hide any undesired traces on the QPS trace.
    # myStream.hideChannel ("3v3:voltage")
    # myStream.hideChannel ("3v3:current")
    
    # Specify the FIO data channels that we want to add to the QPS data
    user_data = ["read_iops","write_iops"]
    
    # Set the callback functions that will be used to handle events during the test sequence
    fioCallbacks = {"TEST_START": notifyTestStart,
                    "TEST_END": notifyTestEnd,
                    "TEST_RESULT": notifyTestPoint}

    '''
    First we will run FIO using command line arguments only (no .fio file needed)
    '''
    # Setup the arguments as required. job 'name' should always be last added
    arguments = {"directory":testDirectory, 
                 "rw":"randread",           
                 "size":"128m",             
                 "runtime":"20",
                 "bs":"4k",
                 "time_based":"",           # This will force FIO to run for the time declared in runtime
                 "output":"testFile",       # Required output file, so we can parse it
                 "status-interval":"1",     # Update interval to add user data on the chart
                 "name":"4kRead"}

    # Run the FIO workload        
    print ("Running Job 1 of 2: FIO run from arguments in Python code\nThis may take some time to complete.")
    runFIO(myStream,        # The QPS stream object
           "arg",           # Execution mode ("arg" for arguments, "file" for FIO job file)
           fioCallbacks,    # Callback list, used to notify the test status and retrieve user data
           user_data,       # The user data items that we want to add to the trace
           arguments)       # FIO execution arguments, describing the workload

     # Wait a few seconds before the next test
    visual_sleep(sleepLength=5, updatePeriod=0.5, title="Sleep 5 seconds to let drive idle")


    '''
    Now we will run FIO using a pre-written file ('file' mode execution).
    NOTE: In this mode, you MUST specify the path for FIO testing within the file.  Set this to a valid path first
    Using the "directory=" parameter of the .fio file
    '''
    arguments = {"directory":testDirectory,                       
                 "output":"testFile"}       # Required output file, so we can parse it

    # Location of the example .fio file used later (in the local folder in this example)
    fioFile = "jobFileExample.fio" #os.getcwd() + 
    
    # Check for a 'filename' parameter in the FIO workload file.  If this is present, we will not be able to specify the output
    # file from the command line (as required by this example, so we can parse it later)
    if 'filename' in open(fioFile).read():
        print("This script will not work as intended with the argument \'filename\' in file: " + fioFile)
        return
    # Convert the file path into that needed by FIO (escape :)
    fioFile = fioFile.replace ("/","\\")
    fioFile = fioFile.replace (":","\\:")
    
    # Run the FIO workload      
    print ("Running Job 2 of 2: FIO run from a .fio file describing the jobs\nThis may take some time to complete.")
    runFIO(myStream,        # The QPS stream object
           "file",          # Execution mode ("arg" for arguments, "file" for FIO job file)
           fioCallbacks,    # Callback list, used to notify the test status and retrieve user data
           user_data,       # The user data items that we want to add to the trace
           arguments,       # FIO execution argumants, describing the workload
           fioFile)         # File containing the job details           

    # End the stream after a few seconds of idle
    visual_sleep(sleepLength=5, updatePeriod=0.5, title="Sleep 5 seconds to let drive idle")

    myStream.stopStream()
    myQpsDevice.closeConnection()
    print("You have reach the end of the application note.\nHave a nice day!")

'''
Callback: Run to add the start point of a test run.  Adds an annotation to the chart
'''
def notifyTestStart (myStream, timeStamp, title, testDescription):
    #adding an annotation using xml format
    print(myStream.addAnnotation(title = title, extraText = testDescription, annotationTime= timeStamp))

'''
Callback: Run to add the end point of a test run.  Adds an annotation to the chart and 
ends the current block of performance data
'''
def notifyTestEnd (myStream, timeStamp, testName="END"):
    #breaking data input to graph between tests
    myStream.addDataPoint('read_iops', 'IOPS', "endSeq" , timeStamp )
    myStream.addDataPoint('write_iops', 'IOPS', "endSeq" , str(int(timeStamp)+1))
    myStream.addAnnotation(testName, timeStamp)

'''
Callback: Run for each test point to be added to the chart
'''
def notifyTestPoint (myStream, timeStamp, dataValues):
    myStream.addDataPoint('read_iops', 'IOPS', dataValues['read_iops'], timeStamp)
    myStream.addDataPoint('write_iops', 'IOPS', dataValues['write_iops'], timeStamp)    

'''
Function to check the output state of the module and prompt to select an output mode if not set already
'''
def setupPowerOutput (myModule):
    output_mode = myModule.sendCommand("config:output Mode?")

    # Skip setupPowerOutput for PAM modules
    if output_mode[0:4] == 'FAIL':
        return
    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    if "DISABLED" in output_mode:
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

'''
Function to get user input in python 2.x or 3.x
'''
def userInput(text, orStr=""):
    try:
        return raw_input (text) or orStr
    except NameError:
        return input (text) or orStr        


if __name__=="__main__":
    main()

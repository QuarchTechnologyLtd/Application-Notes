#!/usr/bin/env python
'''
This example uses FIO and QPS to run traffic tests to a drive, with the power and performance data displayed.

- The user is prompted to select a target (mapped drive location)
- FIO is invoked to run a workload to the selected location.  Power and IO performance data is logged and displayed in QPS

########### VERSION HISTORY ###########

10/09/2018 - Pedro Leao		- First Version

########### INSTRUCTIONS ###########

1- Connect a Quarch power module to your PC via USB or LAN
2- On startup, select the options for the device you wish to test

####################################
'''

# Import modules and packages
import time, os
import Tkinter, tkFileDialog

from quarchpy import ( requiredQuarchpyVersion,
                     isQpsRunning, startLocalQps, quarchQPS, qpsInterface, GetQpsModuleSelection, 
                     quarchDevice,
                     runFIO)

# We use TK for the directory selection box, this code avoids additional TK GUI items being shown
root = Tkinter.Tk()
root.withdraw()

# Verify a recent version of quarchpy is available
if not requiredQuarchpyVersion ("1.3.4"):
            raise ValueError ("QuarchPy reported version is outdated for this script!")

# Path where stream will be saved to (defaults to current script path)
streamPath = os.path.dirname(os.path.realpath(__file__))

'''
Main function, containing the example code to execute FIO and display the results
'''
def main():

    # Display title text
    print ("\n################################################################################")
    print ("\n                           QUARCH TECHNOLOGY                        \n\n  ")
    print ("Automated power and performance data acquisition with Quarch Power Studio.   ")
    print ("\n################################################################################\n")  

    # Checks is QPS is running on the localhost
    if not isQpsRunning():
    # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps(keepQisRunning=True)    

    # Open an interface to local QPS
    myQps = qpsInterface()
    
    # Module to work with
    myDeviceID = GetQpsModuleSelection (myQps)

    # Create a Quarch device connected via QPS
    myQuarchDevice = quarchDevice (myDeviceID, ConType = "QPS")
    
    # Upgrade Quarch device to QPS device
    myQpsDevice = quarchQPS(myQuarchDevice)
    myQpsDevice.openConnection()

    # Prints out connected module information        
    print ("MODULE CONNECTED: \n" + myQpsDevice.sendCommand ("*idn?"))
    
    '''
    NOTE: You may need a delay after this call, to allow your drive more time to enumerate on the system before
    are prompted to select the folder to use for FIO performance testing
    '''
    # Setup the voltage mode and enable the outputs
    setupPowerOutput (myQpsDevice)
    
    # Get the required averaging rate from the user.  This sets the resolution of data to record        
    averaging = userInput("\n>>> Enter the average rate [32k]: ", "32k")
    
    # Set the averaging rate to the module
    myQpsDevice.sendCommand ("record:averaging " + averaging)


    print ("\n>>> Select a folder for FIO Data:")
    # Request user to select the folder to use for FIO data
    testDirectory = tkFileDialog.askdirectory ()
    print ("Selected : " + testDirectory)
    # Convert path to format needed by FIO (backslashes and colons escaped)
    testDirectory = testDirectory.replace ("/","\\")
    testDirectory = testDirectory.replace (":","\\:")
    

    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())        
    myStream = myQpsDevice.startStream (streamPath + "\\" + fileName)

    # Create new custom channels to plot IOPS results
    myStream.createChannel ('read_iops', 'IOPS', 'IOPS', "Yes")
    myStream.createChannel ('write_iops', 'IOPS', 'IOPS', "Yes")

    #hiding all the unwanted default channels
    myStream.hideChannel ("3v3:voltage")
    myStream.hideChannel ("5v:voltage")
    myStream.hideChannel ("12v:voltage")
    myStream.hideChannel ("3v3:current")
    myStream.hideChannel ("5v:current")
    myStream.hideChannel ("12v:current")

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
                 "size":"64m",             
                 "runtime":"10",             
                 "output":"testFile",       # Required output file, so we can parse it
                 "status-interval":"1",     # Update interval to add user data on the chart
                 "name":"job1"}

    # Run the FIO workload                             
    runFIO(myStream,        # The QPS stream object
           "arg",           # Execution mode ("arg" for arguments, "file" for FIO job file)
           fioCallbacks,    # Callback list, used to notify the test status and retrieve user data
           user_data,       # The user data items that we want to add to the trace
           arguments)       # FIO execution arguments, describing the workload

     # Wait a few seconds before the next test
    time.sleep(5)
    

    '''
    Now we will run FIO using a pre-written file ('file' mode execution).
    NOTE: In this mode, you must specify the path for FIO testing within the file.  Set this to a valid path first.
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
    runFIO(myStream,        # The QPS stream object
           "file",          # Execution mode ("arg" for arguments, "file" for FIO job file)
           fioCallbacks,    # Callback list, used to notify the test status and retrieve user data
           user_data,       # The user data items that we want to add to the trace
           arguments,       # FIO execution argumants, describing the workload
           fioFile)         # File containing the job details           

    # End the stream after a few seconds of idle
    time.sleep(5)

    myStream.stopStream()

'''
Callback: Run to add the start point of a test run.  Adds an annotation to the chart
'''
def notifyTestStart (myStream, timeStamp, title, testDescription):
    #adding an annotation using xml format
    myStream.addAnnotation("<<text>" + title + "</text><extraText>" + testDescription + "</extraText>>", timeStamp)

'''
Callback: Run to add the end point of a test run.  Adds an annotation to the chart and 
ends the current block of performance data
'''
def notifyTestEnd (myStream, timeStamp, testName="END"):
    #breaking data input to graph between tests
    myStream.addDataPoint('read_iops', 'IOPS', "endSeq" , timeStamp )
    myStream.addDataPoint('write_iops', 'IOPS', "endSeq" , timeStamp)
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

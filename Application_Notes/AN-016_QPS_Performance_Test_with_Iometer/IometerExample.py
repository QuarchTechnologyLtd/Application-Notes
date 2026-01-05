#!/usr/bin/env python
'''
FMS2018 Demo
This example uses IOMeter and QPS to run traffic tests to a drive, with the power and performance data displayed.

- The user is prompted to select an IOmeter target (Physical disk or drive letter)
- The .conf files are IOmeter templates which are then turned into .icf files with the selected target in place
- IOmeter is invoked over each .icf file in the folder whild QPS is used to display combined power and performance data

########### VERSION HISTORY ###########

27/06/2018 - Andy Norrie    - First version, based on initial work from Nikolas Ioannides
02/08/2018 - Pedro Leao     - Updated to add nicer selection screens and IOmeter control
28/03/2019 - Andy Norrie    - Updated for v1.9 of quarchpy, with improved import system
17/03/2023 - Matt Holsey    - Updating in-line with application notes overhaul

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/
5- Install wmi package from pypi (Windows only)
    https://pypi.org/project/WMI/
6- Install pywin32 package from pypi (Windows only)
    https://pypi.org/project/pywin32/
7- Java 8, with JaxaFX
    https://quarch.com/support/faqs/java/

########### INSTRUCTIONS ###########

1- Connect a Quarch power module to your PC via USB or LAN
2- On script startup, select the Quarch Power module you are streaming with from the table displayed.
3- Next you will be prompted to select the Block device or the drive partition you wish to test.
4- Next you'll select if you wish to run the script using the CSV tests or the tests inside '/conf'.
5- Lastly, you will be asked to type an averaging rate for the Quarch Power Module. ( Note - This can
   be left blank and the module will be set to 32k Averaging as a default )

####################################
'''

# Import modules and packages.
from __future__ import division

import multiprocessing as mp
import time
import os
import sys
from sys import platform

try:
    # for Python 2.x
    import thread
except ImportError:
    # for Python 3.x
    import _thread

try:
    # for Python 2.x
    from StringIO import StringIO
except ImportError:
    # for Python 3.x
    from io import StringIO

if platform == "win32":
    try:
        import wmi as newImport
    except ImportError:
        raise ImportError("'wmi' module required, please install this")
    try:
        import win32file, win32api
    except ImportError:
        raise ImportError("'pywin32' module required, please install this")

import quarchpy
from quarchpy.device import *
from quarchpy.qps import *
from quarchpy.iometer import *
from quarchpy.disk_test import getDiskTargetSelection


# Global Variables
filePath = os.path.dirname(os.path.realpath(__file__))


def main():
    """
    The main function sets up the tests and then invokes Iometer, QPS and the results reading thread which reads
    the data back from the IOmeter results file
    """

    # Setup the callback dictionary, used later to notify us of data needing processed.
    # If you don't want to implement all the functions, just delete the relevant item
    iometerCallbacks = {
        "TEST_START": notifyTestStart,
        "TEST_END": notifyTestEnd,
        "TEST_RESULT": notifyTestPoint,
    }

    # Make sure quarchpy is up to date (min version required = 2.0.0)
    quarchpy.requiredQuarchpyVersion("2.0.0")

    # Display title text
    print("\n################################################################################")
    print("\n                           QUARCH TECHNOLOGY                        \n\n  ")
    print("Automated power and performance data acquisition with Quarch Power Studio.   ")
    print("\n################################################################################\n")

    '''
    *****
    First we activate QIS and prompt the user to select a power module
    *****
    '''
    # Checks is QPS is running on the localhost
    if not isQpsRunning():
        # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps()

    # Open an interface to local QPS
    myQps = qpsInterface()

    # Get the user to select the module to work with
    myDeviceID = GetQpsModuleSelection(myQps)

    # Create a Quarch device connected via QPS
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType="QPS")

    # Upgrade Quarch device to QPS device
    myQpsDevice = quarchQPS(myQuarchDevice)

    # Open a connection to this selected module
    myQpsDevice.openConnection()
    # Prints out connected module information
    print("MODULE CONNECTED: \n" + myQpsDevice.sendCommand("*idn?"))

    # Setup the voltage mode and enable the outputs
    # Uncomment for modules that can perform power margining (XLC, HDPPM)
    # setupPowerOutput (myQpsDevice)

    # Turning on power to the module
    if check_power_state(myQpsDevice):
        # Sleep for a few seconds to let the drive target enumerate if it wasn't powered on
        print("")
        print("Waiting for drives to enumerate...")
        time.sleep(5)
        
    '''
    *****
    Get the user to select a valid target drive
    *****
    '''
    targetInfo = getDiskTargetSelection (purpose="iometer")

    print ("\n TARGET DEVICE: " + targetInfo["NAME"])
    print (" VOLUME: " + targetInfo["DRIVE"])


    run_option = 0
    while run_option not in ("1", "2"):
        # Run from CSV settings or all the files in /conf
        try:
            run_option = raw_input ("\n1 - Use settings in CSV file\n2 - Run all files in /conf\n>>> Please select a mode: ")
        except NameError:
            run_option = input ("\n1 - Use settings in CSV file\n2 - Run all files in /conf\n>>> Please select a mode: ")

    tempList = []
    if "1" in run_option:
        keepReading = True
        count = 1
        # The CSV data is used to generate .icf files for execution in this folder.  Make sure you delete any old files from here if you do not want to run them again
        confDir = os.path.join(os.getcwd(), "conf", "temp_conf")
        # If this path doesn't exist already, then make it.
        if not os.path.exists(confDir):
            os.makedirs(confDir)

        # If the CSV file doesn't exist then close the module connection and exit as script cannot continue without it
        if not os.path.isfile("csv_example.csv"):
            myQpsDevice.closeConnection()
            raise FileNotFoundError(f"Missing 'csv_example.csv' file from current dir!\n"
                                    f"Please add this file from app note folder and restart.")

        # For each line in the CSV file, generate a new .icf file
        while 1:
            # read the line into a dictionary
            csvData, keepReading = readIcfCsvLineData("csv_example.csv", count)
            # If no more lines in file, continue with script
            if not keepReading:
                break
            timeStamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
            icfFilePath = os.path.join(confDir, f"file{str(count)}_{timeStamp}.icf")
            # Add file path to list to be removed at the end of the test
            tempList.append(icfFilePath)
            # Generate a new .icf file
            generateIcfFromCsvLineData(csvData, icfFilePath, targetInfo)
            count += 1

    if "2" in run_option:
        confDir = os.path.join(os.getcwd(), "conf")
        # If there's no 'conf' directory, script cannot use .conf file inside.
        if not os.path.exists(confDir):
            myQpsDevice.closeConnection()
            raise NotADirectoryError("Could not find 'conf' directory.\n "
                                     "Please add this folder from the app note and restart")

        # If there's a directory but no files inside, the script cannot use files for Iometer test
        if os.listdir(confPath).count() == 0:
            myQpsDevice.closeConnection()
            raise FileNotFoundError("Could not find config files inside 'conf' directory.\n "
                                     "Please add these .conf files from the app note and restart")

        # Use the .conf files to generate new .icf files for new Iometer job
        generateIcfFromConf(confDir, targetInfo)

    '''
    *****
    Setup and begin streaming
    *****
    '''
    # Get the required averaging rate from the user.  This sets the resolution of data to record
    try:
        averaging = raw_input ("\n>>> Enter the average rate [32k]: ") or "32k"
    except NameError:
        averaging = input ("\n>>> Enter the average rate [32k]: ") or "32k"

    # Set the averaging rate to the module
    myQpsDevice.sendCommand ("record:averaging " + averaging)

    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
    myStream = myQpsDevice.startStream (filePath + "\\" + fileName)

    # Create new custom channels to plot IO results
    myStream.createChannel ('I/O', 'IOPS', 'IOPS', "Yes")
    myStream.createChannel ('Data', 'Data', 'Bytes', "Yes")
    myStream.createChannel ('Response', 'Response', 'mS', "No")

    # Delete any old output files
    if os.path.exists("testfile.csv"):
        os.remove("testfile.csv")
    if os.path.exists("insttestfile.csv"):
        os.remove("insttestfile.csv")

    # Execute every ICF file in sequence and process them. Deletes any temporary ICF
    executeIometerFolderIteration (confDir, myStream, iometerCallbacks)

    # Deletes temporary files that were created
    try:
        for tempFile in tempList:
             os.remove(tempFile)
    except NameError:
        pass

    # End the stream after a few seconds of idle
    time.sleep(5)
    myStream.stopStream()
    # Close the connection to the module in use
    myQpsDevice.closeConnection()
   

def executeIometerFolderIteration (confDir, myStream, userCallbacks):
    """
    Executes a group of .ICF files in the given folder and processes the results into the current stream
    :param confDir: String                  - Directory path for the conf directory containing .conf files
    :param myStream: quarchStream object    - For interacting with ongoing stream
    :param userCallbacks: List[<function>]  - List of functions to call during stream
    :return:
    """
    skipFileLines = 0
        
    for file in os.listdir(confDir):
        if file.endswith(".icf"):

            icfFilePath = os.path.join(confDir, file)
            icfFilePath = "\"" + icfFilePath + "\""

            # Change the current working directory to be inside /iometer in order to launch iometer program
            cur_dir = os.getcwd()
            os.chdir(os.path.join(os.getcwd(), "iometer"))

            try:
                os.remove("insttestfile.csv")
            except OSError:
                pass

            # Start up IOmeter and the results parser
            threadIometer = mp.Process(target=runIOMeter, args = (icfFilePath,))
                
            # Start both threads. 
            threadIometer.start()

            # Read data generated from iometer and add the data to QPS
            processIometerInstResults(file, myStream, userCallbacks)

            # Wait for threads to complete
            threadIometer.join()

            time.sleep(5)

            # Change the directory back to the original directory
            os.chdir(cur_dir)
         
'''
Function to check the output state of the module and prompt to select an output mode if not set already
'''


def setupPowerOutput(myModule):
    """
    Setting the module output mode if it is not already set.

    :param myModule: QpsDevice object
    :return: N/A
    """
    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    if "DISABLED" in myModule.sendCommand("config:output Mode?"):
        try:
            drive_voltage = raw_input(
                "\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3]: ") or "3V3"
        except NameError:
            drive_voltage = input(
                "\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3]: ") or "3V3"

        myModule.sendCommand("config:output:mode:" + drive_voltage)

def check_power_state(myModule):
    """
    Checking if the module is powered.
    Will power on module if it is not already.

    :param myModule: QpsDevice object
    :return: Boolean : True if module required power up else false
    """
    # Check the state of the module and power up if necessary
    powerState = myModule.sendCommand("run power?")

    print(f"Checking if the module was powered up... {powerState}")

    # If outputs are off
    if "OFF" in powerState:
        # Power Up
        print("\n Turning the outputs on:"), myModule.sendCommand("run:power up"), "!"
        return True

    return False

'''
*****
The following functions are callbacks from the Iometer parsing code, notifying us of new actions or data, so we can
act on it in a custom way (generally adding it to the QPS chart)
*****
'''

def notifyTestStart(myStream, timeStamp, testDescription):
    """
    Callback: Run to add the start point of a test run.  Adds an annotation to the chart

    :param myStream: quarchStream object    - For interacting with ongoing stream
    :param timeStamp: String                - Timestamp to send to QPS
    :param testDescription: String          - Small description of current action
    :return: N/A
    """
    myStream.addAnnotation(testDescription + "\\n TEST STARTED", timeStamp)


def notifyTestEnd(myStream, timeStamp, testName=None):
    """
    Callback: Run to add the end point of a test run.  Adds an annotation to the chart and
    ends the current block of performance data

    :param myStream: quarchStream object    - For interacting with ongoing stream
    :param timeStamp: String                - Timestamp to send to QPS
    :param testName : String                - Optional var
    :return:
    """
    # Add an end annotation
    myStream.addAnnotation("END", timeStamp)
    # Terminate the sequence of user data just after the current time, to avoid spanning the chart across the idle area
    myStream.addDataPoint('I/O', 'IOPS', "endSeq", timeStamp)
    myStream.addDataPoint('Data', 'Data', "endSeq", timeStamp)
    myStream.addDataPoint('Response', 'Response', "endSeq", timeStamp)


def notifyTestPoint(myStream, timeStamp, dataValues):
    """
    Callback: Run for each test point to be added to the chart

    :param myStream: quarchStream object    - For interacting with ongoing stream
    :param timeStamp: String                - Timestamp to send to QPS
    :param dataValues: Dictionary           - Key:value for value to add to QPS channel
    :return:
    """
    # Add each custom data point that has been passed through
    if "IOPS" in dataValues:
        myStream.addDataPoint('I/O', 'IOPS', dataValues["IOPS"], timeStamp)
    if "DATA_RATE" in dataValues:
        myStream.addDataPoint('Data', 'Data', dataValues["DATA_RATE"], timeStamp)
    if "RESPONSE_TIME" in dataValues:
        myStream.addDataPoint('Response', 'Response', dataValues["RESPONSE_TIME"], timeStamp)


# Calling the main () function
if __name__ == "__main__":
    main()
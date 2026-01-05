'''
AN-003 - Application note implements the UNH-IOL plugfest test for hotswap of U.2 drives
This application note was written to be used in conjunction with QuarchPy python package and Quarch modules.

########### VERSION HISTORY ###########

05/04/2018 - Andy Norrie    - First version

########### INSTRUCTIONS ###########

1- Connect a Quarch module to your PC via QTL1260 Interface kit and USB cable with the button pushed in
2- If needed, install the FTDI VCOM driver to support the virtual COM port


####################################
'''

#Imports QuarchPy library, providing the functions needed to use Quarch modules
from __future__ import print_function
from quarchpy import quarchDevice
from lsSATA import pickSataTarget, checkAdmin, devicePresent

# Import other libraries used in the examples
import os
import time
import datetime
# Imports QuarchPy library, providing the functions needed to use Quarch modules
from __future__ import print_function

import datetime
# Import other libraries used in the examples
import os
import time

from lsSATA import pickSataTarget, checkAdmin, devicePresent
from quarchpy import quarchDevice

#import exceptions

'''
Prints to screen and to the logfile at the same time
'''
logFilePath = os.path.join (os.getcwd(), "LogFile" + str(datetime.datetime.now ()).replace (':','_') + ".txt")
def logWrite (logString):
    print (logString)
    with open(logFilePath, 'a') as logFile:
        logFile.write (logString + "\n")

'''
Exit the script and close connections
'''
def exitScript (myDevice):
    setDefaultState (myDevice)
    myDevice.closeConnection()
    quit()

def setDefaultState (myDevice):
    myDevice.sendCommand ("conf:def:state"+ port)
    time.sleep(3)

'''
Sets up a simple hot-plug timing.  6 times sources are available on most modules.
Final delay to in 1270mS, so the total delay time must not exceed this
'''
def setupSimpleHotplug (myDevice, delayTime, stepCount):

    # Check parameters
    if delayTime < 1:
        raise ValueError('delaytime must be in range 1 to (1270/sourceCount)mS')
    if stepCount > 1:
        if delayTime > (1270/(stepCount-1)):
            raise ValueError('delaytime must be in range 1 to (1270/sourceCount)mS')
    if (stepCount < 2 or stepCount > 6):
        raise ValueError('stepCount must be between 1 and 6')

    # Run through all 6 timed sources on the module
    for steps in (1, 6):
        # Calculate the next source delay. Additional sources are set to the last value used
        if steps <= stepCount:
            nextDelay = (steps - 1 ) * delayTime

        cmdResult = myDevice.sendCommand ("source:" + str(steps) + ":delay " + str(nextDelay)+ port)
        if "OK" not in cmdResult:
                logWrite ("***FAIL: Config command failed to execute correctly***")
                logWrite ("***" + cmdResult)
                exitScript (myDevice)
    time.sleep(0.1)

''' 
Opens the connection, call the selected example function(s) and closes the connection.
The constructor opens the connection by default.  You must always close a connection before you exit
'''
def main():

    # Setting parameters that control the test
    onTime = 10                     # Drive on time
    offTime = 15                    # Drive off time
    plugSpeeds = [25,100,10,500]    # Hot plug speeds
    cycleIterations = 10            # Number of cycles at each speed

    # Check admin permissions (exits on failure)
    checkAdmin ()

    # Print header intro text
    logWrite ("SATA HotPlug Test Suite V1.0")
    logWrite ("(c) Quarch Technology Ltd 2018")
    logWrite ("")

    # Get the connection string
    try: 
        moduleStr = raw_input ("Enter the connection type followed by the module serial number: \ne.g.:\nUSB:QTL1743 - Connects directly to the module.\nREST:QTL1461 - Connects to the array controller and prompts for the (array) port the module is connected to.\n>>")

    except:
        moduleStr = input ("Enter the connection type followed by the module serial number: \ne.g.:\nUSB:QTL1743 - Connects directly to the module.\nREST:QTL1461 - Connects to the array controller and prompts for the (array) port the module is connected to.\n>>")

    if "1079" in moduleStr or "1461" in moduleStr:
        print (moduleStr)
        global port
        port = raw_input ("Enter the port you would like to connect to (e.g. 1, 2, 3 ... 28) >> ")
        port = " <" + port + ">"
    else:
        port = ""

    # Create a device using the module connection string
    myDevice = getQuarchDevice(moduleStr)

    # Sets the module to default state
    #setDefaultState (myDevice)

    # Check the module is connected and working
    QuarchSimpleIdentify (myDevice)

    # Select the PCIe device to use
    sataDevice = pickSataTarget ()
    if (sataDevice == 0):
        logWrite ("***FAIL: Valid PCIe device was not selected***")
        quit()

    # Loop through the list of plug speeds
    for testDelay in plugSpeeds:
        testName = str(testDelay) + "mS HotPlug Test"
        iteration = 0

        # Loop through plug iterations
        for currentIteration in range (0, cycleIterations):
            logWrite ("")
            logWrite ("")
            logWrite ("===============================")
            logWrite ("Test - " + testName + " - " + str(currentIteration+1) + "/" + str(cycleIterations))
            logWrite ("===============================")
            logWrite ("")

            # Setup hotplug timing (QTL1743 uses 3 sources by default)
            setupSimpleHotplug (myDevice, testDelay, 3)

            # Pull the drive
            logWrite ("Beginning the test sequence:\n")
            logWrite ("  - Pulling the device...")
            cmdResult = myDevice.sendCommand ("RUN:POWer DOWN"+ port)
            print ("    <"+cmdResult+">")
            if "OK" not in cmdResult:
                logWrite ("***FAIL: Power down command failed to execute correctly***")
                logWrite ("***" + cmdResult)
                exitScript (myDevice)

            # Wait for device to remove
            logWrite ("  - Waiting for device removal (" + str(offTime) + " Seconds)...")
            time.sleep(offTime)

            # Check that the device removed correctly
            cmdResult = devicePresent (sataDevice)
            if cmdResult == True:
                logWrite ("***FAIL: " + testName + " - Device did not remove***")
                exitScript (myDevice)
            else:
                logWrite ("    <Device removed correctly!>")

            # Power up the drive
            logWrite ("\n  - Plugging the device")
            cmdResult = myDevice.sendCommand ("RUN:POWer UP"+ port)
            print ("    <"+cmdResult+">")
            if "OK" not in cmdResult:
                logWrite ("***FAIL: Power down command failed to execute correctly***")
                exitScript (myDevice)

            # Wait for device to enumerate
            logWrite ("  - Waiting for device enumeration (" + str(onTime) + " Seconds)...")
            time.sleep(onTime)

            # Verify the device is back
            cmdResult = devicePresent (sataDevice)
            if cmdResult == False:
                logWrite ("***FAIL: " + testName + " - Device not present***")
                exitScript (myDevice)
            else:
                logWrite ("    <Device enumerated correctly!>")

            logWrite ("\nTest - " + testName + " - Passed!")

    logWrite ("")
    logWrite ("ALL DONE!")
    logWrite ("\nTest - " + "100% Tests run" + " - Passed")
    logWrite ("")
            
    # Close the module before exiting the script
    myDevice.closeConnection()

'''
This function demonstrates a very simple module identify, that will work with any Quarch device
'''
def QuarchSimpleIdentify(device1):
    # Print the module name
    time.sleep(0.1)
    print("\nModule Name:"),
    print("<"+device1.sendCommand("hello?" + port)+">")
    time.sleep(0.1)
    # Print the module identify and version information
    print("\nModule Status:")
    print("<"+device1.sendCommand("*tst?"+ port)+">")
    print("")




if __name__== "__main__":
    main()

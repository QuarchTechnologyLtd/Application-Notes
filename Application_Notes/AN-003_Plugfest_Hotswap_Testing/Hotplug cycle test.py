'''
AN-003 - Application note implements the UNH-IOL plugfest test for hotswap of U.2 drives
This application note was written to be used in conjunction with QuarchPy and QuarchQCS python packages and Quarch modules.

########### VERSION HISTORY ###########

05/04/2018 - Andy Norrie	- First version
14/10/2018 - Pedro Cruz	- Added support to other connection types and array controllers
27/11/2019 - Stuart Boon - Compatible with linux, moved to lspci in Qpy, Updated for newest Qpy features like drive and module selection.
11/11/2021 - Stuart Boon / Matt Holsey - Updating for use with newer drive detection mechanisms
01/02/2023 - Matt Holsey - Restructuring / refactoring with instructions.

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- QuarchQCS python package
    https://pypi.org/project/quarchQCS/
4- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
5- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

# LINUX USERS REQUIRE ADDITIONAL DOWNLOADS #
- SmartCtl download : https://www.smartmontools.org/wiki/Download
- PCIUTILS download : "sudo apt install pciutils"   ( Or your OS equivalent )

########### INSTRUCTIONS ###########

1- Connect a Quarch module to your PC via QTL1260 Interface kit or array controller
2- Check test parameters.
3- Run this script using in an elevated command prompt.
4- Select the module and drive in your set up and watch the results.

####################################
'''

# Try to make script back compatible to python 2.x
from __future__ import print_function
try:
    input = raw_input
except NameError:
    pass

# Imports QuarchPy library, providing the functions needed to use Quarch modules
from quarchpy.device import *
from QuarchpyQCS.hostInformation import HostInformation
from quarchpy.user_interface import *
from quarchpy.user_interface.user_interface import displayTable

# Import other libraries used in the examples
import os
import time
import datetime
import logging


# Creating a path for the log file to be written to.
logFilePath = os.path.join(os.getcwd(), "LogFile" + str(datetime.datetime.now()).replace(':', '_') + ".txt")

# Reference to hostInformation class for drive detection functionality.
myHostInfo = HostInformation()

# List of failures encountered - if any.
summary_list = []


def main():
    """
    Main function for running test.
    """
    logging.basicConfig(filename='output.log',
     level=logging.DEBUG,
     format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
     datefmt='%H:%M:%S')

    # Setting parameters that control the test
    onTimeout = 10  # Timeout (s) to poll for drive insertion
    offTimeout = 10  # Timeout (s) to poll for drive removal
    mappingMode = False  # lspci mapping mode
    plugSpeeds = [25, 100, 10, 500]  # Hot plug speeds (mS) between pin lengths - Per UNH specification
    cycleIterations = 3  # Number of cycles at each speed
    linkSpeed = "ERROR"
    linkWidth = "ERROR"

    # Check admin permissions (exits on failure)
    if not is_user_admin():
        logWrite("Application note must be run with administrative privileges.")

    # Print header intro text
    logWrite("Quarch Technology Ltd")
    logWrite("HotPlug Test Suite V3.0")
    logWrite("(c) Quarch Technology Ltd 2015-2023")
    logWrite("")

    # Scan for quarch devices over all connection types (USB, Serial and LAN)
    logWrite("Scanning for devices...\n")
    deviceList = scanDevices('all', favouriteOnly=False)

    # You can work with the deviceList dictionary yourself, or use the inbuilt 'selector' functions to help
    # Here we use the user selection function to display the list on screen and return the module connection string
    # for the selected device
    moduleStr = userSelectDevice(deviceList, additionalOptions=["Rescan", "All Conn Types", "Quit"], nice=True)
    if moduleStr == "quit":
        return 0

    # If you know the name of the module you would like to talk to then you can skip
    # module selection and hardcode the string.
    # moduleStr = "USB:QTL2266-01-001"

    # Create a device using the module connection string
    logWrite("\n\nConnecting to the selected device")
    myDevice = getQuarchDevice(moduleStr)
    logWrite("\nConnected to module: " + myDevice.sendCommand("hello?"))

    # Sets the module to default state
    setDefaultState(myDevice)

    # Checking to see if Quarch module selected is legacy.
    # Legacy modules may include out of date firmware or be unable to run at high resolution timings
    # If the module is legacy, check if there's an update available on our website
    # https://quarch.com/downloads/update-pack/
    # Alternatively, consider enquiring about potential modules with newer functionality.
    is_legacy_module = check_legacy_timings(myDevice)

    logWrite("Running power up..." + myDevice.sendCommand("run pow up"))

    # Retrieve a list of drives located on system and format into a list
    listOfDrives = retrieve_list_of_found_drives()

    # Asking user to select their drive from the list of drives found.
    selectedDrive = None
    while selectedDrive is None or selectedDrive in "Rescan":
        selectedDrive = listSelection(selectionList=listOfDrives, nice=True, additionalOptions=["Rescan", "Quit"],
                                      tableHeaders=["Drive"], align="c")

        listOfDrives = retrieve_list_of_found_drives()

    if selectedDrive in "Quit":
        printText("User quit program")
        exitScript(myDevice)
        exit(1)

    # Deconstructing the drive chosen to get the drive wrapper object for use in test.
    selectedDrive = selectedDrive.split(":-")
    myDrive = myHostInfo.get_wrapped_drive_from_choice(selectedDrive[0])

    # If the drive is PCIE, do link verification on drive too
    if myDrive.drive_type == "pcie":
        pcieHotplug(cycleIterations, mappingMode, myDevice, offTimeout, onTimeout, myDrive, plugSpeeds,
                    is_legacy_module)
    else:
        basicHotplug(cycleIterations, mappingMode, myDevice, offTimeout, onTimeout, myDrive, plugSpeeds,
                     is_legacy_module)

    logWrite("")

    logWrite("Test Complete")

    # Adding a table of results if there were any failures.
    if summary_list:
        displayTable(summary_list, align="l", tableHeaders=["Delay (mS)", "Test iteration", "Failure description"])
    else:
        logWrite("All tests Passed!")

    logWrite("")

    # Close the module before exiting the script
    myDevice.closeConnection()


def retrieve_list_of_found_drives():
    # Retrieving a list of drives located on the system
    listOfDrives = myHostInfo.return_wrapped_drives()
    # Formatting list into 'nice' layout for user
    listOfDrives = _return_drives_as_list(listOfDrives)
    return listOfDrives


def logWrite(log_string):
    """
    Function to print to screen and to the logfile at the same time

    :param log_string: (String) - String to write to console & file.
    """
    print(log_string)
    with open(logFilePath, 'a') as logFile:
        logFile.write(log_string + "\n")


def exitScript(my_device, err=None):
    """
    Exit script cleanly, ensuring module is reset to default state
    and no connection to module is left open.

    :param my_device: quarchDevice obj - Module wrapper for selected module.
    :param err : String (optional) - Display an error to user before exiting the script.
    """
    setDefaultState(my_device)
    my_device.closeConnection()
    if err:
        logging.error(err)
    quit()


def setDefaultState(my_device):
    """
    Issue command to reset the Quarch module do it's default state

    :param my_device: (quarchDevice obj) - Module wrapper for selected module.
    """
    my_device.sendCommand("conf:def:state")
    # A small wait is added to allow complete module reset before exit.
    time.sleep(3)


def check_legacy_timings(my_device):
    """
    Checking if the Quarch Breaker module is incapable of long hotplug

    :param my_device: (QuarchDevice Obj) - Module wrapper
    :return: Boolean - True if legacy module else False
    """

    logWrite("Checking for legacy module...")
    # If command below returns a fail, then the module is legacy.
    result = my_device.sendCommand("source:5:delay 1500")

    if "FAIL: 0x16 -Numeric value not in valid range" in result:
        logWrite("Module is legacy.")
        return True
    else:
        logWrite("Module is not legacy.")
        return False


def is_user_admin():
    """
    Checking if current terminal / command prompt session has elevated privileges
    """
    if os.name == 'nt':
        import ctypes
        # WARNING: requires Windows XP SP2 or higher!
        try:
            # If == 1, user is running from elevated cmd prompt
            # printText(ctypes.windll.shell32.IsUserAnAdmin() == 1)
            return ctypes.windll.shell32.IsUserAnAdmin() == 1
        except:
            traceback.print_exc()
            return False
    elif os.name == 'posix':
        # Check for root on Posix
        return os.getuid() == 0
    else:
        raise RuntimeError("Unsupported operating system for this module: %s" % (os.name,))


def QuarchSimpleIdentify(quarch_module):
    """
    Simple identify of the Quarch module selected

    :param quarch_module: quarchDevice obj - Quarch module wrapper obj
    """
    # Print the module name
    time.sleep(0.1)
    logWrite("\nModule Name:")
    logWrite(quarch_module.sendCommand("hello?"))
    time.sleep(0.1)
    # Print the module identify and version information
    logWrite("\nModule Status:")
    logWrite(quarch_module.sendCommand("*tst?"))
    print("")


def setupSimpleHotplug(my_device, delay_time, step_count, is_legacy):
    """
    Sets up a simple hot-plug timing.  6 times sources are available on most modules.
    If module is a legacy module, final delay set to 1270mS, so not exceed legacy delay limitations.

    :param my_device: QuarchDevice Obj - Quarch Moudle wrapper
    :param delay_time: Int - Time in mS to delay each source
    :param step_count: Int - Number of sources to iteratively delay
    :param is_legacy: Boolean - True if the Quarch module has legacy timings
    """

    # Check parameters
    if delay_time < 1:
        exception_err = "1270" if is_legacy else "16777"
        exitScript(my_device, f'delaytime must be in range 1 to ({exception_err}/sourceCount)mS')
    if step_count > 1:
        if is_legacy:
            if delay_time > (1270 / (step_count - 1)):
                exitScript(my_device, 'delaytime must be in range 1 to (1270/sourceCount)mS')
    if step_count < 2 or step_count > 6:
        exitScript(my_device, 'stepCount must be between 1 and 6')

    # Run through all 6 timed sources on the module
    for steps in (1, step_count):
        # Calculate the next source delay. Additional sources are set to the last value used
        nextDelay = (steps - 1) * delay_time
        cmdResult = my_device.sendCommand("source:" + str(steps) + ":delay " + str(nextDelay))
        if "OK" not in cmdResult:
            logWrite("***FAIL: Config command failed to execute correctly***")
            logWrite("***" + cmdResult)
            exitScript(my_device)
    time.sleep(0.1)


def basicHotplug(cycleIterations, mappingMode, myDevice, offTime, onTime, myDrive, plugSpeeds, is_legacy_module):
    """
    Function to perform hotplug tests.
    Each "power down" searches for a time <offTime> to ensure the drive is not discovered by the System.
    Each "power up" search for a time <onTime> to ensure system has re-discovered drive.

    All failures are added to a list for display at the end of the test.

    :param cycleIterations: int - Number of times to perform hotplug
    :param mappingMode:
    :param myDevice: QuarchDevice obj - Wrapper for Quarch Module
    :param offTime: int - Max time (Seconds) to poll for drive removal on system
    :param onTime: int - Max time (Seconds) to poll for drive insertion on system
    :param myDrive: DriveWrapper obj - Wrapper for DUT
    :param plugSpeeds: List<int> - List of hotplug delay speeds
    :param is_legacy_module: Boolean - True if the selected quarch module has legacy timings
    """

    # Loop through the list of plug speeds
    for testDelay in plugSpeeds:
        all_testpoints_passed = True
        testName = str(testDelay) + "mS HotPlug Test"

        # Loop through plug iterations
        for currentIteration in range(0, cycleIterations):
            logWrite("")
            logWrite("")
            logWrite("===============================")
            logWrite("Test -" + testName + " - " + str(currentIteration + 1) + "/" + str(cycleIterations))
            logWrite("===============================")
            logWrite("")

            # Setup hotplug timing (QTL1743 uses 3 sources by default)
            setupSimpleHotplug(myDevice, testDelay, 3, is_legacy_module)

            # Pull the drive
            logWrite("Beginning the test sequence:\n")
            logWrite("  - Pulling the device...")

            cmdResult = myDevice.sendCommand("RUN:POWer DOWN")
            logWrite("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myDevice)

            # Wait for device to remove
            logWrite("  - Waiting for device removal (" + str(offTime) + " Seconds Max)...")
            startTime = time.time()

            while True:
                cmdResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if cmdResult is False:
                    logWrite("Device removed correctly in " + str(currentTime - startTime) + " sec")
                    break
                if currentTime - startTime > offTime:
                    logWrite("***FAIL: " + testName + " - Drive was not removed after " + str(offTime) + " sec ***")
                    all_testpoints_passed = False
                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive was not removed after " + str(offTime) + " sec"])
                    break

            # Power up the drive
            logWrite("\n  - Plugging the device")

            cmdResult = myDevice.sendCommand("RUN:POWer UP")
            logWrite("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myDevice)

            # Wait for device to enumerate
            logWrite("  - Waiting for device enumeration (" + str(onTime) + " Seconds Max)...")
            startTime = time.time()

            while True:
                cmdResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if cmdResult is True:
                    logWrite("<Device enumerated correctly in " + str(currentTime - startTime) + " sec>")
                    break
                if currentTime - startTime > onTime:
                    logWrite("***FAIL: " + testName + " - Drive did not return after " + str(onTime) + " sec ***")
                    all_testpoints_passed = False
                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive did not return after " + str(onTime) + " sec"])
                    break
            if all_testpoints_passed:
                logWrite("Test - " + testName + " - Passed")
            else:
                logWrite("Test - " + testName + " - Failed")


def pcieHotplug(cycleIterations, mappingMode, myDevice, offTime, onTime, myDrive, plugSpeeds, is_legacy_module):
    """
    Function to perform hotplug tests.
    Each "power down" searches for a time <offTime> to ensure the drive is not discovered by the System.
    Each "power up" search for a time <onTime> to ensure system has re-discovered drive.

    All failures are added to a list for display at the end of the test.

    PCIE hotplug will also check drive's Link Speed and Lane Width after power up.

    :param cycleIterations: int - Number of times to perform hotplug
    :param mappingMode:
    :param myDevice: QuarchDevice obj - Wrapper for Quarch Module
    :param offTime: int - Max time (Seconds) to poll for drive removal on system
    :param onTime: int - Max time (Seconds) to poll for drive insertion on system
    :param myDrive: DriveWrapper obj - Wrapper for DUT
    :param plugSpeeds: List<int> - List of hotplug delay speeds
    :param is_legacy_module: Boolean - True if the selected quarch module has legacy timings
    """
    # Get the current link status
    linkStartSpeed = myDrive.link_speed
    linkStartWidth = myDrive.lane_width
    logWrite("Current PCIe device link speed: " + myDrive.link_speed)
    logWrite("Current PCIe device link width: " + myDrive.lane_width)

    # Loop through the list of plug speeds
    for testDelay in plugSpeeds:
        all_testpoints_passed = True
        testName = str(testDelay) + "mS HotPlug Test"

        # Loop through plug iterations
        for currentIteration in range(0, cycleIterations):
            logWrite("")
            logWrite("")
            logWrite("===============================")
            logWrite("Test -" + testName + " - " + str(currentIteration + 1) + "/" + str(cycleIterations))
            logWrite("===============================")
            logWrite("")

            # Setup hotplug timing (QTL1743 uses 3 sources by default)
            setupSimpleHotplug(myDevice, testDelay, 3, is_legacy_module)

            # Pull the drive
            logWrite("Beginning the test sequence:\n")
            logWrite("  - Pulling the device...")

            cmdResult = myDevice.sendCommand("RUN:POWer DOWN")
            logWrite("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myDevice)

            # Wait for device to remove
            logWrite("  - Waiting for device removal (" + str(offTime) + " Seconds Max)...")
            startTime = time.time()

            while True:
                pullResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if not pullResult: # Looking for device to be missing after pull requested
                    logWrite("Device removed correctly in " + str(currentTime - startTime) + " sec")
                    break
                if currentTime - startTime > offTime:
                    logWrite("***FAIL: " + testName + " - Drive was not removed after " + str(offTime) + " sec ***")
                    all_testpoints_passed = False
                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive was not removed after " + str(offTime) + " sec"])
                    break

            # Power up the drive
            logWrite("\n  - Plugging the device")

            cmdResult = myDevice.sendCommand("RUN:POWer UP")
            logWrite("    <" + cmdResult + ">")
            if "OK" not in cmdResult:
                logWrite("***FAIL: Power down command failed to execute correctly***")
                logWrite("***" + cmdResult)
                exitScript(myDevice)

            # Wait for device to enumerate
            logWrite("  - Waiting for device enumeration (" + str(onTime) + " Seconds Max)...")
            startTime = time.time()

            while True:
                plugResult = myHostInfo.is_wrapped_device_present(myDrive)
                currentTime = time.time()
                if plugResult is True:
                    logWrite("<Device enumerated correctly in " + str(currentTime - startTime) + " sec>")
                    break
                if currentTime - startTime > onTime:
                    logWrite("***FAIL: " + testName + " - Drive did not return after " + str(onTime) + " sec ***")
                    all_testpoints_passed = False
                    summary_list.append([str(testDelay), str(currentIteration + 1) + "/" + str(cycleIterations),
                                         "Drive did not return after " + str(onTime) + " sec"])
                    break

            # Verify link width and speed
            linkEndSpeed = myHostInfo.return_wrapped_drive_link(myDrive)
            linkEndWidth = myHostInfo.return_wrapped_drive_width(myDrive)
            if linkStartSpeed != linkEndSpeed:
                logWrite("***FAIL: " + testName + " - Speed Mismatch, " + linkStartSpeed + " -> " + linkEndSpeed + "***")
                exitScript(myDevice)
            if linkStartWidth != linkEndWidth:
                logWrite("***FAIL: " + testName + " - Width Mismatch, " + linkStartWidth + " -> " + linkEndWidth + "***")
                exitScript(myDevice)

            if all_testpoints_passed:
                logWrite("Test - " + testName + " - Passed")
            else:
                logWrite("Test - " + testName + " - Failed")

def _return_drives_as_list(drive_list):
    """
    Function to sort drives into correctly formatted list for display

    :param drive_list: List of driveWrapper objects
    :return new_return: List of strings correctly formatted
    """
    new_return = []

    for drive in drive_list:
        new_return.append("{0} :- {1}".format(drive.identifier_str, drive.description))

    return new_return


if __name__ == "__main__":
    main()

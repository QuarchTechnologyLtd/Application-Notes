"""
AN-015 - Application note demonstrating automated control over Quarch Power Studio (QPS)

This example demonstrates adding annotations and datapoints to a QPS stream.

########### VERSION HISTORY ###########
1
05/06/2018 - Andy Norrie    - First Version.
02/10/2018 - Matt Holsey    - Updated Script for updated QuarchPy Methods.
15/10/2020 - Pedro Cruz     - Updated Script for PAM.
23/03/2023 - Graham Seed    - Reviewed code and updated requirements and instructions.
30/06/2025 - Nabil Ghayyda/Andy Norrie - Updated with more detailed examples and documentation for adding annotations and custom data.

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

1- Connect a Quarch module to your PC via USB, Serial or LAN and power it on.
2- Run the script and follow the instructions on screen.
3- For localhost QPS, run the example as it is.
4- For remote QPS, comment out the 'startLocalQps()' command and specify the IP:Port in the qpsInterface(...) command
   This can also be used if you want to use a different version of QPS and will run it yourself

####################################
"""

# Import other libraries used in the examples
import os
import time

# Import QPS functions
from quarchpy import qpsInterface, isQpsRunning, startLocalQps, GetQpsModuleSelection, getQuarchDevice, quarchDevice, \
    quarchQPS, \
    requiredQuarchpyVersion, closeQPS, __version__ as qpv
from quarchpy.user_interface.user_interface import showDialog, requestDialog


def main():

    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    print("\n\nQuarch application note example: AN-015")
    print("---------------------------------------\n")
    print("Quarchpy version: " + str(qpv) + "\n\n")
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
    # myDeviceID = "TCP::QTL2312-01-035"

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

    # Set the resampling rate for the module. This sets the resolution of data to record.
    # This is done via the QPS command "stream mode resample ... ".
    print(myQpsDevice.sendCommand("stream mode resample 1ms"))
    # # On a multirate device groups can be resampled separately as show here:
    # print(myQpsDevice.sendCommand("stream mode resample group 0 132ms"))
    # print(myQpsDevice.sendCommand("stream mode resample group 1 132ms"))

    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
    myStream = myQpsDevice.startStream(os.path.join(filePath, fileName))
    print("File output path set: " + str(os.path.join(filePath, fileName)))

    time.sleep(2)
    myStream.addAnnotation('Adding an example annotation\\nIn real time!')
    time.sleep(1)
    annotation_time = int(time.time() * 1000)  # time in milliseconds
    myStream.addAnnotation('Adding an example annotation\\nAt a specific time!', annotation_time)
    time.sleep(1)


    # Create new channel to record data into
    print("creating custom channels ...")
    response = myStream.createChannel('T1', 'Temp', 'C', False) # For Temp data
    print("command response: " + response)
    response = myStream.createChannel('T2', 'Temp', 'C', False) # Channel in the same group with no data
    print("command response: " + response)
    response = myStream.createChannel('Fan1', 'Fans', 'RPM', False)
    print("command response: " + response)
    time.sleep(1) # waiting 1s to allow QPS to add the channels before we start adding data to them.

    # Write some example temperature data into the channel
    writeArbitraryData_Temp(myStream, 'T1', 'Temp')

    # Write some example fan speed data into the channel
    writeArbitraryData_Fans(myStream, 'Fan1', 'Fans')
    time.sleep(1)

    # Statistics can be fetched from QPS. Stats show the channel data between annotations.
    print("\n\nHere are example stats, pulled from the API, these can be dropped into a CSV file or directly processed")
    print(myStream.get_stats())

    # End the stream
    time.sleep(10)
    myStream.stopStream()
    showDialog("End of test. Press enter to close QPS")  # showDialog is from quarchpy userinterface class. Which handles py2 and py3 compatibility.
    closeQPS()





def setupPowerOutput(myModule):
    '''
    Simple function to check the output mode of the power module, setting it to 3v3 if required
    then enabling the outputs if not already done.  This will result in the module being turned on
    and supplying power.
    '''
    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    outModeStr = myModule.sendCommand("config:output mode?")
    if "DISABLED" in outModeStr:
        # From quarchpy userinterface class. Which handles py2 and py3 compatibility.
        drive_voltage = requestDialog(
            message="\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ")
        myModule.sendCommand("config:output:mode:" + drive_voltage)

    # Check the state of the module and power up if necessary
    powerState = myModule.sendCommand("run power?")
    # If outputs are off
    if "OFF" in powerState or "PULLED" in powerState:  # PULLED comes from PAM
        # Power Up
        print("\n Turning the outputs on:"), myModule.sendCommand("run:power up"), "!"





def writeArbitraryData_Temp(myStream, channelName, groupName):
    '''
    Example function to write data to an arbitrary channel that has been previously created
    This data would normally come from another process such as drive monitor software or
    a traffic generator.
    '''
    print("Writings 10 seconds worth of (made up) temperature data, please wait...")
    # Add a few temperature points to the stream at 1 second intervals
    driveTemp = 18
    myStream.addAnnotation('Starting temperature measurement here!')
    for x in range(0, 19):
        myStream.addDataPoint(channelName, groupName, str(driveTemp))
        driveTemp = driveTemp + 0.8
        time.sleep(1)
        if (x % 10 == 9): #every 10 loops add an endSeq which stops linier interpolation between points.
            myStream.addDataPoint(channelName, groupName, str("endseq"))
            time.sleep(5)
    time.sleep(1)
    # Add a final time point at a specific time to demonstrate random addition of points
    last_reading_time = int(time.time() * 1000)  # time in milliseconds
    myStream.addDataPoint(channelName, groupName, str("endseq"), last_reading_time)





def writeArbitraryData_Fans(myStream, channelName, groupName):
    '''
    Example function to write data to an arbitrary channel that has been previously created
    This data would normally come from another process such as drive monitor software or
    a traffic generator.
    '''
    print("Writings 10 seconds worth of (made up) fan data, please wait...")
    # Add a few rpm points to the stream at 1 second intervals
    fanRPM = 11
    myStream.addAnnotation('Starting fan speed measurement here!')

    for x in range(0, 10):

        myStream.addDataPoint(channelName, groupName, str(fanRPM))
        fanRPM = fanRPM + 1.25
        time.sleep(1)
    time.sleep(1)
    # Add a final time point at a specific time to demonstrate random addition of points
    last_reading_time = int(time.time() * 1000)  # time in milliseconds
    myStream.addDataPoint(channelName, groupName, str(fanRPM), last_reading_time)

# Calling the main() function
if __name__ == "__main__":
    main()

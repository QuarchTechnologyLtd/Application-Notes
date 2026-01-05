'''

########### VERSION HISTORY ###########

28/01/2025 - Stuart Boon
29/04/2025 - Stuart Boon

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- FIO (3.38 is the latest release at time of writing)
    https://github.com/axboe/fio
3- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
4- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
5- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

########### INSTRUCTIONS ###########

1. Run this script
2. Select FIO test folder
3. Open the merged QIS+FIO csv file

Optional
4. Open the produced output files from QIS/FIO
5. Edit the FIO arguments to your desired test, change the test directory.

####################################
'''


# Import other libraries used in the examples
import datetime
import os
import subprocess
import time  # Used for sleep commands
from quarchpy.device import *
from quarchpy.fio import *
from quarchpy.fio.FIO_interface import merge_fio_qis_stream
from quarchpy.qis import *
from quarchpy.user_interface.user_interface import visual_sleep, displayTable


def main():
    '''
    Main function that starts QIS, connects to the module and does some basic setup before running the test.
    '''

    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    #logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    # Path where stream will be saved to (defaults to current script path)
    streamDirectory = os.path.dirname(os.path.realpath(__file__))
    #testDirectory = input("Please enter the FIO test directory \n>")
    testDirectory = "C\:\\temp"

    displayTable("Quarch application note example: AN-028") #Print the title in a one cell table. Looks nice.

    # Start QIS (if it is already running, skip this step and also avoid closing it at the end)
    closeQisAtEndOfTest = False
    if isQisRunning() == False:
        print("Starting QIS...\n")
        startLocalQis(headless=True)
        closeQisAtEndOfTest = True

    # Connect to the localhost QIS instance
    myQis = QisInterface()
    print("QIS Version: " + myQis.sendAndReceiveCmd(cmd='$version'))

    # Ask the user to select a module to use, via the console.
    myDeviceID = myQis.GetQisModuleSelection()
    # If you know the name of the module you would like to talk to then you can skip module selection and hardcode the string.
    # myDeviceID = "USB:QTL1999-05-005"
    print("Module Selected: " + myDeviceID + "\n")

    # Connect to the module
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType="QIS")
    # Convert the base device class to a power device, which provides additional controls, such as data streaming
    myPowerDevice = quarchPPM(myQuarchDevice, skipDefaultSyntheticChannels=True)

    # This ensures the latest stream header is used, even for older devices.  This will soon become the default, but is in here for now
    # as it ensures the output CSV is in the latest format with units added to the row headers.
    myPowerDevice.sendCommand("stream mode header v3")
    # These are optional commands which create additional channels in the output for power (current * voltage) and total power 
    # (sum of individual power channels).  This can be useful if you don't want to calculate it in post-processing
    myPowerDevice.sendCommand("stream mode power enable")
    myPowerDevice.sendCommand("stream mode power total enable")

    # Prints out connected module information
    print("Running QIS RESAMPLING Example")
    print("Module Name: " + myPowerDevice.sendCommand("hello?"))
    # Sets for a manual record trigger, so we can start the stream from the script
    print("Set manual Trigger: " + myPowerDevice.sendCommand("record:trigger:mode manual"))
    # Use 16k averaging as this is a bit faster than we require
    print("Set averaging: " + myPowerDevice.sendCommand("record:averaging 16"))
    # SET RESAMPLING HERE
    # This tells QIS to re-sample the data at a new timebase of 1 samples per second
    # Software averaging ensures that every sample of data is averaged, ensuring no data is lost
    print("Setting QIS resampling to 100us")
    myPowerDevice.streamResampleMode("100us")

    qis_stream_and_FIO_example(myPowerDevice, testDirectory, streamDirectory)
    if closeQisAtEndOfTest:
        closeQis()

    print("End of Script")


def qis_stream_and_FIO_example(module, testDirectory, streamDirectory):
    """
    An example of how to stream using QIS and run an FIO workload then merge the csv data together.
    Args:
        module: The quarch module you would like to stream with.
        testDirectory: The test directory for writing FIO data to.
        streamDirectory: The stream directory for QIS to write stream data to.
    Returns:
        None
    """

    # Creating the qis file path
    streamFileName = 'QIS_Stream_' + str(datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")) + '.csv'
    qisFilePath = os.path.join(streamDirectory, streamFileName)
    #Create the FIO output path
    fIOOutputPath=os.path.join(streamDirectory, "FIOOutputFile")
    fIOOutputPath='"'+fIOOutputPath+'"'

    print("\nStarting Recording!")
    streamStartTime=time.time_ns()
    module.startStream(qisFilePath, '1000', 'Example stream to file with resampling')

    # Required FIO arguments
    arguments = {"directory": "\"" + testDirectory + "\"",
                 "rw": "randread",
                 "size": "128m",
                 "runtime": "5",
                 "bs": "4k",
                 "time_based": "",  # This will force FIO to run for the time declared in runtime
                 "output": fIOOutputPath,  # Required output file, so we can parse it
                 "status-interval": "250ms",  # Update interval to add user data on the chart
                 "name": "4kRead"} # Required output file, so we can parse it

    print("\nStarting FIO test!")
    # Run our FIO arguments
    runFIO("arg",  # Execution mode ("arg" for arguments, "file" for FIO job file)
           arguments)  # FIO execution arguments, describing the workload

    # Do a visual sleep for the length of the FIO task
    if 'runtime' in arguments.keys():
        sleepLength = int(arguments['runtime'])+1
    else:
        sleepLength = 5
    visual_sleep(sleepLength=sleepLength, updatePeriod=0.5, title="Sleep "+str(sleepLength)+" seconds to run the FIO Job")

    # Check the stream status, so we know if anything went wrong during the capture period
    print("Checking the stream is running (all data has been captured)")
    streamStatus = module.streamRunningStatus()
    if ("Stopped" in streamStatus):
        if ("Overrun" in streamStatus):
            print('\tStream interrupted due to internal device buffer has filled up')
        elif ("User" in streamStatus):
            print('\tStream interrupted due to max file size has being exceeded')
        else:
            print("\tStopped for unknown reason")
    else:
        print("\tStream ran correctly")

    # Stop the stream.  This function is blocking and will wait until all remaining data has been downloaded from the module
    module.stopStream()
    stop_stream_time = time.time()
    while (True):  # wait until stream status returns "stopped" or we time out
        stream_status = module.streamRunningStatus()
        elapsed_time = time.time() - stop_stream_time
        timeout = 10
        if "stopped" in stream_status.lower() or elapsed_time - stop_stream_time > timeout:
            break
        time.sleep(0.3)

    print("Merging QIS and FIO data into one csv file.")
    merge_file_location =  merge_fio_qis_stream(
        qis_stream_file=qisFilePath,
        fio_output_file=fIOOutputPath[1:-1],
        unix_stream_start_time=str(streamStartTime)+"nS",
        rounding_option="round",  # or "insert",
        output_file=qisFilePath.replace(".csv","")+"_merged_with_fio.csv"
    )

    # Here we use quarchpy display table function to nicely output the location of the 3 data file for the user to look at.
    file_paths = [["Qis Data", qisFilePath], ["FIO Data", fIOOutputPath[1:-1]], ["Merged Data", merge_file_location]]
    displayTable(file_paths)


def runFIO(mode, arguments="", file_name=""):
    """
    Completes some necessary argument processing before passing them on to start_fio
    This function is a stripped back version of what you will find in quarchpy/fio/fio_interface.py customised for this example
    Args:
        mode:
        arguments:
        file_name:
    Returns:
    """
    try:
        xrange # Python 2 compatibility
    except NameError:
        xrange = range
    for i in xrange(0, len(arguments)):
        try:
            arguments_ori = arguments[i]
        except:
            arguments_ori = arguments
        output_file = arguments_ori["output"]
        if (file_name != ""):
            # allows filename with spaces
            file_name = "\"" + file_name + "\""
    start_fio(output_file, mode, arguments_ori, file_name)


def start_fio(output_file, mode, options, fileName=""):
    """
    Uses the provided arguments to start an FIO workload.
    This function is a stripped back version of what you will find in quarchpy/fio/fio_interface.py customised for this example
    Args:
        output_file:
        mode:
        options:
        fileName:

    Returns:
        p: the process running the fio workload
    """
    if mode == "arg":
        command = "fio --log_unix_epoch=1 --output-format=json"
    for i in options:
        if (options[i] == ""):
            command = command + " --" + i
        else:
            command = command + " --" + i + "=" + options[i]
    command = command
    # removes the output file if it already exists.
    if os.path.exists(output_file):
        os.remove(output_file)
    print("FIO CMD: "+str(command))
    p = subprocess.Popen(command, shell=True)
    return p



# Calling the main() function
if __name__ == "__main__":
    main()

'''
AN-031 - Application note demonstrating control of AC power modules via QIS and saving the outputted QIS data to csv

Automating via QIS is a lower overhead than running QPS (Quarch Power Studio) in full but still
provides easy access to data for custom processing.  This example uses Quarchpy functions to set up
an AC power module with QIS.

There are several examples that run in series, these can be commented out if you want to simplify the actions:

simpleStreamExample() - This example streams data to a python data structure and then outputs the data to a csv file "stream-data.csv"

QIS is distributed as part of the Quarchpy python package and does not require separate install

########### VERSION HISTORY ###########

30/09/2024 - Nabil Ghayyda  - First Version

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Java 8, with JaxaFX
    https://quarch.com/support/faqs/java/
3- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
4- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
5- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

########### INSTRUCTIONS ###########

1. Connect an AC PAM device via USB or LAN and power it up
2. Run the script and follow any instructions on the terminal

####################################
'''
import os

# Import other libraries used in the examples
import time  # Used for sleep commands
import logging  # Optionally used to create a log to help with debugging

from quarchpy.device import *
from quarchpy.qis import *

from io import StringIO
from threading import Thread

# Global variables to store last values and stream status
csv_data_io = StringIO()  # Store stream data in memory
last_values = {}  # Cache last values for each channel
stream_running = False


def main():
    # If required you can enable python logging, Quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

    print("\n\nQuarch application note example: AN-031")
    print("---------------------------------------\n\n")

    # Start QIS (if it is already running, skip this step and also avoid closing it at the end)
    print("Starting QIS...\n")
    closeQisAtEndOfTest = False
    if isQisRunning() == False:
        startLocalQis()
        closeQisAtEndOfTest = True

    # Connect to the localhost QIS instance
    myQis = QisInterface()
    print("QIS Version: " + myQis.sendAndReceiveCmd(cmd='$version'))

    # Ask the user to select a module to use, via the console.
    myDeviceID = myQis.GetQisModuleSelection()
    print("Module Selected: " + myDeviceID + "\n")

    # If you know the name of the module you would like to talk to then you can skip module selection and hardcode the string.
    # myDeviceID = "USB:QTL1999-05-005"

    # Connect to the module
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType="QIS")

    # Convert the base device class to a power device, which provides additional controls, such as data streaming
    # The power class now also automatically sets up the default synthetic channels - to disable them simply pass skipDefaultSyntheticChannels=True
    myPowerDevice = quarchPPM(myQuarchDevice)

    # Select one or more example functions to run, you can comment any of these out if you do not want to run them
    simple_stream_example(myPowerDevice)

    if closeQisAtEndOfTest == True:
        closeQis()


'''
This example streams measurement data to file, by default in the same folder as the script
'''


# Start the stream and record data for 30 seconds
def simple_stream_example(module):
    global stream_running

    print("Setting QIS resampling to 125uS")
    module.streamResampleMode("125uS")

    print("\nStarting Recording!")
    module.startStream(inMemoryData=csv_data_io, fileName=None)

    stream_running = True
    # Start a separate thread to read and cache stream data every second
    thread = Thread(target=read_and_print_last_values, daemon=True)
    thread.start()

    print("\nWait for 30 seconds...\n")
    time.sleep(30)

    # Stop the stream
    print("\nStopping the stream...")
    module.stopStream()

    stream_running = False
    # Process final stream data and update cache
    process_stream_data()

    # Check stream status
    check_stream_status(module)

    # Print & output the acquired data to a csv file "stream-date.csv"
    process_qis_data(csv_data_io)


# Function to cache the last sample for each column
def process_stream_data():
    csv_data_io.seek(0)  # Rewind to the start of the CSV data
    lines = csv_data_io.readlines()  # Read all lines
    if lines:
        headers = lines[0].strip().split(',')  # Extract headers from first line
        last_line = lines[-1].strip().split(',')  # Extract the last line of data
        for i, header in enumerate(headers):
            if header != "" and header is not None:  # Only process non-empty headers
                last_values[header] = last_line[i]  # Cache the last sample for each valid column


# API to request the last value by channel name
def get_last_value(channel_name):
    return last_values.get(channel_name, None)


# Continuously read and print last values during the stream every second
def read_and_print_last_values():
    while stream_running:
        # Process the latest stream data to update the cache
        process_stream_data()

        # Get and print last values for L1 RMS Voltage, Current and Power
        l1_rms_voltage = get_last_value("L1_RMS mV")
        l1_rms_current = get_last_value("L1_RMS mA")
        l1_p_app = get_last_value("L1_PApp mVA")

        if l1_rms_voltage or l1_rms_current or l1_p_app:
            print(f"L1 RMS Voltage: {l1_rms_voltage}, L1 RMS Current: {l1_rms_current}, L1 RMS Power: {l1_p_app}")

        time.sleep(1)


# Check stream status and ensure no interruptions
def check_stream_status(module):
    print("Checking the stream is running (all data has been captured)")
    stream_status = module.streamRunningStatus()
    if "Stopped" in stream_status:
        if "Overrun" in stream_status:
            print("\tStream interrupted due to internal device buffer filling up")
        elif "User" in stream_status:
            print("\tStream Stopped")
        else:
            print("\tStopped for unknown reason")
    else:
        print("\tStream ran correctly")


def process_qis_data(csv_data_io):

    # Get the entire contents of the buffer as a string
    csv_data_string = csv_data_io.getvalue()

    # # DEBUG - Print Header and CSV Data as a List
    # print("\nIn-Memory Data acquired from QIS: \n")
    #
    # # Print all csv data (for debugging)
    # print(csv_data_string)

    # Move cursor to the beginning of the StringIO object
    csv_data_io.seek(0)

    # Get the current directory (where the script is located)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the file path for the CSV file in the same directory as the script
    csv_file_path = os.path.join(current_dir, 'stream-data.csv')

    # Output content of returned QIS data to a csv file
    with open(csv_file_path, 'w', newline='') as csv_file:
        csv_file.write(csv_data_io.getvalue())


# Calling the main() function
if __name__ == "__main__":
    main()
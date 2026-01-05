'''
AN-032 - Application note demonstrating capture of power data from multile devices at the same time

Automated capture allows data from multiple instruments to be gathered at the same time, and with lower overhead than running QPS (Quarch Power Studio).
This example uses quarchpy functions to connect and pull data from a list of instruments on the network.

We demonstrate two capture modes:
simple_multi_stream_example() - This example streams each modules stream data to a CSV file for post-processing
multi_device_live_monitoring_example() - This example showcases live monitoring for select stream data

QIS is distributed as part of the Quarchpy python package and does not require separate install

########### VERSION HISTORY ###########

25/03/2025 - Nabil Ghayyda  - First Version

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

########### INSTRUCTIONS ###########

1. Connect multiple Quarch power modules via USB/Ethernet.
2. Edit the script and hard-code the modules you'd like to stream with (edit myDeviceIDs list).
3. Optionally select the channels you want to monitor for live data (edit channelsToMonitor dict).
4. Run the script and follow any instructions on the terminal

####################################
'''
import os

# Import other libraries used in the examples
import time  # Used for sleep commands
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from io import StringIO
from threading import Thread
# import logging  # Optionally used to create a log to help with debugging
# QuarchPy imports
from quarchpy.device import *
from quarchpy.qis import *
from quarchpy.user_interface import displayTable, visual_sleep

# Global variables to store last values and stream status
csv_data_io = []  # Store stream data in memory
last_values = {}  # Cache last values for each channel
stream_running = False

# Hardcoded list to hold all module ID's you'd like to stream with.
myDeviceIDs = [
    # 'TCP:QTL2789-01-001',
    # 'TCP:QTL2789-01-002',
    'TCP:QTL2582-01-005',
    'TCP:QTL2582-01-006',
    'TCP:QTL2843-03-002'
    # 'TCP:QTL2751-02-002',
    # 'TCP:QTL2751-01-001'
]

channels = []


# Define a Channel object using a dataclass
@dataclass
class Channel:
    name: str
    group: str
    units: str
    max_t_value: int
    data_position: int


# List of channels to monitor.
# The key represents the channel header from the output CSV, while the value is a user-friendly label for reporting purposes.
channelsToMonitor = {
    "L1_RMS mV": "L1 RMS Voltage",
    "L1_RMS mA": "L1 RMS Current",
    "Tot_PApp mVA": "Total Apparent Power"
}


def main():
    """
    This is the main function that starts QIS, Connections to Modules and calls the Example Functions.
    :return: None
    """
    # If required you can enable python logging, Quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

    displayTable("Quarch application note example: AN-032")

    closeQisAtEndOfTest = False
    # Check if QIS is running locally (if it is already running, skip this step and also avoid closing it at the end)
    if isQisRunning() is False:
        # Start QIS
        print("Starting QIS...\n")
        startLocalQis()
        closeQisAtEndOfTest = True
    else:
        print("QIS already running on Host Machine")

    # Connect to the localhost QIS instance
    myQis = QisInterface()
    print("QIS Version: " + myQis.sendAndReceiveCmd(cmd='$version'))

    # List of "quarchPPM" objects, this extends the base device class to a power device to provide additional control.
    myPowerDevices = {}

    for i in range(len(myDeviceIDs)):
        # Connect to the module
        myQuarchDevice = getQuarchDevice(myDeviceIDs[i], ConType="QIS", timeout=30)

        # Show which device you have connected to.
        print(f"Connected to Module: " + myDeviceIDs[i])

        # Convert the base device class to a power device, which provides additional controls, such as data streaming
        # The power class now also automatically sets up the default synthetic channels - to disable them simply pass skipDefaultSyntheticChannels=True
        myPowerDevice = quarchPPM(myQuarchDevice)
        # Add power device to list
        myPowerDevices[i] = myPowerDevice
        # Generate a new StringIO object for each power module
        csv_data_io.append(StringIO())

    # Select one or more example functions to run, you can comment any of these out if you do not want to run them
    # simple_multi_stream_example(myPowerDevices)
    multi_device_live_monitoring_example(myPowerDevices)

    if closeQisAtEndOfTest:
        closeQis()

# Setup each power module and start streaming
def simple_multi_stream_example(modules):
    """
    Starts streaming measurement data from multiple devices to separate files.

    1. Sets the resampling rate for each module.
    2. Starts recording and streams data to a file for 30 seconds.
    3. Starts a separate thread to check the stream status once a second
    4. Stops the stream.

    :param modules: dict[int, quarchPPM]
    :return: None
    """
    global stream_running

    print("\nSimple Multi Device Streaming Example\n")

    # Loop through all set devices in hard-coded list
    for i in range(len(myDeviceIDs)):
        print(f"\nSetting QIS resampling to 1mS on module: {myDeviceIDs[i]}")
        modules[i].streamResampleMode("1mS")

        # Start the recording and set the stream duration to 30 seconds to ensure all modules stream for the same amount of time.
        # Setting the fileName allows the API call to stream directly to the file.
        print(f"Started Recording on module: {myDeviceIDs[i]}\n")
        # Create file name using the device id
        file_name = f'{get_device_id(myDeviceIDs[i])}.csv'
        # Start the stream
        # Note: You can optionally add the parameter "streamDuration" for finer control.
        modules[i].startStream(fileName=file_name)

    stream_running = True

    # Start a separate thread to check the stream status each second
    thread = Thread(target=check_stream_status, args=(modules,))
    thread.start()

    print("\nWait for 30 seconds...\n")
    visual_sleep(30)

    # Ensure global variable is set too false to stop the live data coming through.
    stream_running = False

    # Loop through the devices and stop each device stream
    for i in range(len(myDeviceIDs)):
        # Stop the stream
        print(f"\nStopping the stream on module: {myDeviceIDs[i]}")
        modules[i].stopStream()


def multi_device_live_monitoring_example(modules):
    """
    Starts live monitoring for multiple devices.

    1. Sets the resampling rate and starts recording on each module.
    2. Checks that the stream header contains the required channels.
    3. Runs a background thread to read and print live data for 30 seconds.
    4. Stops the stream and checks its status on each module.

    :param modules: dict[int, quarchPPM]
    :return: None
    """
    global stream_running

    print("\nMulti Device Live Monitoring Example\n")

    for i in range(len(myDeviceIDs)):
        print(f"\nSetting QIS resampling to 500mS on module {myDeviceIDs[i]}")
        modules[i].streamResampleMode("500mS")

        # Start the recording
        print(f"Started Recording on module: {myDeviceIDs[i]}\n")
        modules[i].sendAndVerifyCommand("rec stream")

        # Check stream header contains channels you'd like to monitor
        check_header_contains_channels_to_monitor(modules[i])

    stream_running = True

    # Start a separate thread to read and cache stream data at the specified interval
    thread = Thread(target=read_and_print_last_values, args=(modules,))
    thread.start()

    print("\nWait for 30 seconds...\n")
    time.sleep(30)

    # Ensure global variable is set too false to stop the live data coming through.
    stream_running = False

    for i in range(len(myDeviceIDs)):
        # Stop the stream
        print(f"\nStopping the stream on module: {myDeviceIDs[i]}")
        modules[i].sendCommand("rec stop")


def process_stream_data(modules: dict[int, quarchPPM]):
    """
    Function to cache the stream data for each module.
    :param modules: dict[int, quarchPPM]
    :return:
    """
    # Iterate through each module in the provided list of modules.
    for i in range(len(modules)):
        # Send a command to get the streaming data in text format.
        line = modules[i].sendCommand("stream text 1")

        # Split the returned line into parts, removing leading/trailing whitespace.
        # Skip the first part (assumed to be the timestamp) using slicing.
        parts = line.strip().split()[1:]

        # Convert the remaining parts to integers and store them as a sublist in last_values.
        last_values[f'{get_device_id(myDeviceIDs[i])}'] = [int(x) for x in parts]

def read_and_print_last_values(modules: dict[int, quarchPPM], sleep_interval=0.4):
    """
    Continuously reads and prints the latest channel values for monitored devices at a specified interval.
    :param modules: dict[int, quarchPPM]
    :param sleep_interval: int
    :return: None
    """
    # Loop continuously while the stream is active.
    while stream_running:
        # Update the cache with the most recent stream data for all modules.
        process_stream_data(modules)

        # Initialize an index to track the position in the channels list.
        index = 0
        # Iterate through each device in the list of device IDs.
        for device_id in myDeviceIDs:
            # Ensure the device ID is in the correct format or retrieve the actual ID.
            device_id = get_device_id(device_id)
            if len(last_values[device_id]) != 0:
                print(f'\n{device_id}')
                # Loop through each channel to monitor and its descriptor.
                for channel_key, channel_descriptor in channelsToMonitor.items():
                    # Retrieve the corresponding channel object using the current index and channel key.
                    channel = channels[index].get(channel_key)
                    # Check if there is any data to process
                    # Print the channel descriptor and the most recent value for this device and channel.
                    print(f'{channel_descriptor}: {last_values[device_id][channel.data_position - 1]}', end=' ')

            # Move to the next device's channels.
            index += 1

        # Print a blank line to separate outputs.
        print('\n')

        # Pause execution for the specified interval before the next iteration.
        time.sleep(sleep_interval)


def check_stream_status(modules):
    """
    Function that checks the status of each modules stream to ensure each stream ran with no interruptions.
    :param modules: dict[int, quarchPPM]
    :return: None
    """
    while stream_running:
        for module in modules:
            stream_status = module.streamRunningStatus()
            if "Stopped" in stream_status:
                if "Overrun" in stream_status:
                    print("\tStream interrupted due to internal device buffer filling up")
                elif "User" in stream_status:
                    print("\tStream Stopped")
                else:
                    print("\tStopped for unknown reason")
        time.sleep(1)


def check_header_contains_channels_to_monitor(module: quarchPPM):
    """
    Checks if the stream header returned from the module contains the set of channels you wish to monitor.
    Note: List of channels to monitor is currently defined as a global variable in the script.
    :param module: quarchPPM
    :return: None
    """
    # Get the stream header as XML.
    xml_response = module.sendCommand("stream text header")
    while "Header Not Available" in xml_response:
        xml_response = module.sendCommand("stream text header")

    # Parse the XML
    root = ET.fromstring(xml_response)

    # Extract channels and store them as Channel objects in a dict
    extracted_channels = {}
    # List of Channel Keys to check against
    for channel in root.findall(".//channel"):
        channel_obj = Channel(
            name=channel.find("name").text,
            group=channel.find("group").text,
            units=channel.find("units").text,
            max_t_value=int(channel.find("maxTValue").text),
            data_position=int(channel.find("dataPosition").text),
        )
        # Add extracted Channel object to a dict
        extracted_channels[f"{channel_obj.name} {channel_obj.units}"] = channel_obj

    # Append extracted channels from header into global channels list of dicts
    channels.append(extracted_channels)

    # Debug - output all channels.
    # print(str(extracted_channels))

    # Check if all channels to monitor are present in the stream
    for key, value in channelsToMonitor.items():
        if extracted_channels.get(key) is None:
            print(f"Channel: {key} not found.")


def process_qis_data(device_id, csv_data_io_data):
    """
    Converts the in-memory python data structure that holds the stream data from QIS into a CSV file.
    :param device_id:
    :param csv_data_io_data:
    :return: None
    """
    print(f"\nProcessing Stream Data for Module: {device_id}")

    # Move cursor to the beginning of the StringIO object
    csv_data_io_data.seek(0)

    # Get the current directory (where the script is located)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the file path for the CSV file in the same directory as the script
    csv_file_path = os.path.join(current_dir, f'{device_id}.csv')

    # Output content of returned QIS data to a csv file
    with open(csv_file_path, 'w', newline='') as csv_file:
        csv_file.write(csv_data_io_data.getvalue())

    print(f"QIS Stream Data Saved to CSV File: {csv_file_path}\n")


def get_device_id(device_id):
    """ Strips the device identifier e.g. "TCP:" and returns the device id """
    return device_id.split(":", 1)[1].strip()


# Calling the main() function
if __name__ == "__main__":
    main()

# AN-032: Multi-Device Power Streaming

This application note demonstrates capturing power data from multiple devices simultaneously using the Quarch Instrument Server (QIS) and the `quarchpy` Python package. The automated capture allows data from multiple instruments to be gathered at the same time, and with lower overhead than running QPS.

## Overview

The script showcases two capture modes:
1. **Simple Multi-Stream Example**: Streams each module's data to a CSV file for post-processing.
2. **Multi-Device Live Monitoring Example**: Demonstrates live monitoring of select stream data.

`QIS` is distributed as part of the `quarchpy` Python package and does not require a separate install.

## Version History

- **25/03/2025** - Nabil Ghayyda - First Version

## Requirements

1. **Python (3.x recommended)**
   - [Download Python](https://www.python.org/downloads/)
2. **Quarchpy Python package**
   - [Quarchpy Package](https://quarch.com/products/quarchpy-python-package/)
3. **Quarch USB driver (Required for USB connected devices on Windows only)**
   - [Download USB Driver](https://quarch.com/downloads/driver/)
4. **USB Permissions on Linux (if applicable)**
   - [USB Permissions FAQ](https://quarch.com/support/faqs/usb/)

## Instructions

1. Connect multiple Quarch power modules via USB/Ethernet.
2. Edit the script and hard-code the modules you'd like to stream with by modifying the `myDeviceIDs` list.
3. Optionally select the channels you want to monitor for live data by editing the `channelsToMonitor` dictionary.
4. Run the script and follow any instructions on the terminal.

## Script Details

### Main Function

The main function initiates QIS, connects to the modules, and calls the example functions.

```python
def main():
    # Initialization and QIS startup
    ...
    # Connect to QIS and modules
    ...
    # Call example functions
    ...
```

### Example Functions

#### Simple Multi-Stream Example

Streams measurement data from multiple devices to separate files.

```python
def simple_multi_stream_example(modules):
    # Setup and start streaming
    ...
    # Monitor stream status
    ...
```

#### Multi-Device Live Monitoring Example

Starts live monitoring for multiple devices.

```python
def multi_device_live_monitoring_example(modules):
    # Setup and start live monitoring
    ...
    # Read and print live data
    ...
```

## Helper Functions

- **process_stream_data()**: Caches stream data for each module.
- **read_and_print_last_values()**: Continuously reads and prints the latest channel values.
- **check_stream_status()**: Checks the status of each module's stream.
- **check_header_contains_channels_to_monitor()**: Ensures the stream header includes the required channels.
- **process_qis_data()**: Converts stream data into a CSV file.
- **get_device_id()**: Extracts the device ID from the identifier.

## Example Usage

Run the script using:

```bash
python QisMultiDeviceStreamingExample.py
```

Ensure you have edited the script to include your device IDs and selected channels.

---

This README provides a detailed overview of the application note and instructions for running the script. If you have any questions or need further assistance, please refer to the code comments or contact support.

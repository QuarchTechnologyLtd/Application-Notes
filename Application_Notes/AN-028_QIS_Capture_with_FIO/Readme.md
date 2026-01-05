# AN-028 - QIS Capture with FIO Example

## Overview
This application note demonstrates how to capture data using Quarch Instrument Server (QIS) and Flexible I/O Tester (FIO). The example script shows how to run an FIO test and merge the output with the QIS stream data into a single CSV file.

## Features
- Scanning for Quarch devices
- Connecting to a Quarch PPM
- Setting up and running data streaming functions
- Running FIO workloads
- Merging QIS and FIO data into a single CSV file

## Requirements

### Hardware
- Quarch Power Module (PPM)
- Host PC
- USB or LAN connection to the module

### Software
- Python (3.x recommended)
  - [Download Python](https://www.python.org/downloads/)
- FIO (3.38 is the latest release at the time of writing)
  - [FIO GitHub Repository](https://github.com/axboe/fio)
- Quarchpy Python package
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- Quarch USB driver (Required for USB-connected devices on Windows only)
  - [Quarch USB Driver](https://quarch.com/downloads/drivers/)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)

## Instructions

1. Install the required software listed above.
2. Connect the Quarch module to your PC via USB or LAN and power it on.
3. Run the script and follow the instructions on screen.
4. Select the FIO test folder when prompted.
5. Open the merged QIS+FIO CSV file.

### Optional
6. Open the produced output files from QIS/FIO to view the data before it was merged.
7. Edit the FIO arguments in the script to customize the test.

## Provided Files

- `QisFIOStreamExample.py` - Script demonstrating how to capture data using QIS and FIO, and merge the output into a single CSV file.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
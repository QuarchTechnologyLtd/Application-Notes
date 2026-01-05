# AN-016 - QPS Performance Test with Iometer

## Overview
This application note demonstrates using Iometer and Quarch Power Studio (QPS) to run performance tests on a drive, with power and performance data displayed. The example script allows users to select an Iometer target, configure test parameters, and visualize the results.

## Features
- Scanning for Quarch modules
- Connecting to a Quarch module via QPS
- Setting up power outputs
- Running Iometer tests on selected targets
- Fetching and displaying performance data from QPS

## Requirements

### Hardware
- Quarch Power Module (PPM/PAM)
- Host PC
- Power supply for the relevant module
- USB or LAN connection to the module

### Software
- Python (3.x recommended)
  - [Download Python](https://www.python.org/downloads/)
- Quarchpy Python package
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- Quarch USB driver (Required for USB-connected devices on Windows only)
  - [Quarch USB Driver](https://quarch.com/downloads/drivers/)
- WMI package from PyPI (Windows only)
  - [WMI](https://pypi.org/project/WMI/)
- PyWin32 package from PyPI (Windows only)
  - [PyWin32](https://pypi.org/project/pywin32/)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)

## Instructions

1. Install the required items listed above.
2. Connect a Quarch power module to your PC via USB or LAN.
3. Run the `IometerExample.py` script and follow the instructions on the terminal.
   - Select the Quarch Power module you are streaming with from the table displayed.
   - Select the block device or the drive partition you wish to test.
   - Choose whether to run the script using the CSV tests or the tests inside the `/conf` directory.
   - Optionally, type an averaging rate for the Quarch Power Module (default is 32k).

## Provided Example Scripts

- `IometerExample.py` - Main script to run Iometer tests and display power and performance data.
- `Iometer/Dynamo.exe` - Dynamo executable for running Iometer.
- `Iometer/IOmeter.exe` - IOmeter executable.
- `Iometer/Iometer License.txt` - License information for Iometer.
- `Iometer/insttestfile.csv` - Example CSV file for test configuration.
- `Iometer/testfile.csv` - Another example CSV file for test configuration.
- `conf/64k_full_read.conf` - Example configuration file for a 64k full read test.

## License
- Iometer license information can be found in `Iometer License.txt` file
- This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
# AN-025 - QPS Window Averaging Example

## Overview
This application note demonstrates post-processing of Quarch Power Studio (QPS) output to calculate the worst-case active power consumption using a user-specified averaging window.

## Features
- Scanning for Quarch devices
- Connecting to a Quarch PPM
- Setting up and running data streaming functions
- Post-processing CSV data to calculate worst-case active power consumption

## Requirements

### Hardware
- Quarch Power Module (PPM)
- Host PC
- USB or LAN connection to the module

### Software
- Python (3.x recommended)
  - [Download Python](https://www.python.org/downloads/)
- Quarchpy Python package
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- Quarch USB driver (Required for USB-connected devices on Windows only)
  - [Quarch USB Driver](https://quarch.com/downloads/drivers/)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)

## Instructions

1. Install the required software listed above.
2. Connect a Quarch PPM to your PC via USB or LAN and power it on.
3. Export a trace from QPS or similar in standard CSV format.
4. Specify the path of the CSV file in the script and run it.

## Provided Files

- `WindowAveragingExample.py` - Script demonstrating post-processing of QPS output to calculate worst-case active power consumption.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
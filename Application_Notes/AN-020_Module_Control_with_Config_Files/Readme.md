# AN-020 - Module Control with Configuration Files

## Overview
This application note demonstrates how to control Quarch modules using configuration files. The provided script shows how to use configuration file data to determine the capabilities of a Quarch module, connect to the module, and print various sections of the configuration to the terminal.

## Features
- Scanning for Quarch devices
- Connecting to a selected Quarch module
- Finding and parsing the configuration file for the connected module
- Printing general capabilities, signals, signal groups, and sources of the module

## Requirements

### Hardware
- Quarch breaker/hot-plug module
- Host PC
- USB or LAN connection cables

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

1. **Install the required software**
2. **Connect the hardware**
3. **Run the script**:
   - run `DeviceCapabilities.py` script 
   - Follow the on-screen instructions to select the Quarch module and view its capabilities.

## Provided Files

- `DeviceCapabilities.py` - Main script to run module control tests using configuration files.

## License
- This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)in the `LICENSE.txt` file.
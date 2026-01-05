# AN-018 - SATA Hotswap Testing

## Overview
This application note demonstrates using a Quarch module to perform SATA hotswap testing. The example script allows users to configure test parameters, run hotswap cycles, and verify the results.

## Features
- Scanning for SATA devices
- Connecting to a Quarch module
- Setting up hotswap timings
- Running hotswap cycles on selected devices
- Verifying device presence before and after hotswap

## Requirements

### Hardware
- Quarch Power Module (PPM or PAM)
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
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)
- smartmontools (Required for drive detection and SMART data)
  - [smartmontools](https://www.smartmontools.org/)

## Instructions

1. Install the required items listed above.
2. Connect a Quarch power module to your PC via USB or LAN.
3. Run the `Script SATA Hotswap testing.py` script and follow the instructions on the terminal.
   - Select the Quarch Power module you are streaming with from the table displayed.
   - Select the SATA device you wish to test.
   - Configure the hotswap parameters as prompted.
   - The script will run the hotswap cycles and verify the device presence before and after each cycle.

## Provided Example Files

- `Script SATA Hotswap testing.py` - Main script to run SATA hotswap tests.
- `lsSATA.py` - Helper script for SATA device detection and verification.
- `pySMART` - Directory containing the pySMART package used for SMART data retrieval.

## License
- This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
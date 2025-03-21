# AN-026 - QIS Interaction Example

## Overview
This application note demonstrates how to interact with Quarch Instrument Server (QIS) using Python. The example script shows how to stream data from a Quarch Power Module (PPM) and save it to a CSV file.

## Features
- Scanning for Quarch devices
- Connecting to a Quarch PPM
- Setting up and running data streaming functions
- Saving stream data to a CSV file

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
3. Edit the script to set the desired parameters (e.g., `streamLength`, `averaging`, `resampling`, `fileName`).
4. Run the script and follow the instructions in the terminal.

## Provided Files

- `qisSimpleStream.py` - Script demonstrating how to interact with QIS to stream data from a Quarch PPM and save it to a CSV file.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
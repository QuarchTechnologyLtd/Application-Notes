# AN-033-Multi-device-qps-streaming

## Overview
This application note demonstrates a multi-device setup, where 2 Quarch modules can be connected at once in QPS with the data combined in a single analysis.
Multi-device setup allows for measurement of a wider range of channels, or (for example) to view both AC and DC sides of a power supply

## Features
- Connecting to two Quarch modules
- Sending initial setup commands to each
- Combining data from both devices into a single recording for analysis

## Requirements

### Hardware
- Any two Quarch power modules
- Host PC
- USB or LAN connection to the modules

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

1. Install the required items listed above.
2. Connect the Quarch modules to your PC via USB or LAN and power them on.
3. Modify the script to set the modules to use
4. Run the script

## Provided Example Scripts

- `Multi-device-qps-example.py` - Demonstrates scanning for Quarch modules, connecting to a module, and running various test functions based on the selected module.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

# AN-011 - Driving Signals on PCIe Modules

## Overview
This application note demonstrates how to drive signals on Quarch PCIe modules using the `quarchpy` Python package. It provides an example script showing how to scan for modules, connect to a module, set up driving functions, and combine them with other features. This script is specifically targeted at a GEN5 U.2 breaker module (QTL2651) but can be adapted for any module that supports driving.

## Features
- Scanning for Quarch modules
- Connecting to a Quarch module
- Setting up driving functions
- Combining driving functions with other features

## Requirements

### Hardware
- Quarch Breaker Module that supports driving:
  - QTL1630 (-04 and higher)
  - QTL1688 (-03 and higher)
  - QTL1743 (-02 and higher)
  - All Gen4 Gen5, Gen6 PCIe modules
  - 24G SAS modules
- Host PC
- Power supply for the relevant module
- USB, Serial, or LAN connection to the module

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
2. Connect a Quarch module to your PC via USB, Serial, or LAN and power it on.
3. Run the script and follow the instructions on screen.

## Provided Example Scripts

- `Driving Examples.py` - Demonstrates scanning for Quarch modules, connecting to a module, and running driving functions based on the selected module.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
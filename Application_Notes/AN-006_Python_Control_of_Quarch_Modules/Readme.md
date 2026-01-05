# AN-006 - Simple Python Automation of Quarch Modules

## Overview
This application note demonstrates how to automate control of Quarch Modules using the `quarchpy` Python package. It provides an example script showing scanning for modules, connecting to a module, sending commands, and using responses.
All Quarch modules are compatable with atleast one of the tests withing this script. So reguardless of what quarch module you have this is a great place to learn how to use it.

## Features
- Scanning for Quarch modules
- Connecting to a Quarch module
- Sending commands and using responses

## Requirements

### Hardware
- Any Quarch Module
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

- `Python Control Examples.py` - Demonstrates scanning for Quarch modules, connecting to a module, and running various test functions based on the selected module.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
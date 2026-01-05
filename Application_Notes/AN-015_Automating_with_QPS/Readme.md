# AN-015 - Automating with Quarch Power Studio (QPS)

## Overview
This application note demonstrates automated control over Quarch Power Studio (QPS) using Python scripts. It provides example scripts for adding annotations and data points to a QPS stream, setting up the power output, and more.

## Features
- Scanning for Quarch modules
- Connecting to a Quarch module via QPS
- Setting up power outputs
- Adding annotations and data points to QPS streams
- Fetching statistics from QPS

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


## Instructions

1. Install the required items listed above.
2. Connect a Quarch module to your PC via USB, Serial, or LAN and power it on.
3. Run the desired script and follow the instructions on the terminal.

## Provided Example Scripts

- `QpsRecordingExample.py` - Demonstrates adding annotations and data points to a QPS stream.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
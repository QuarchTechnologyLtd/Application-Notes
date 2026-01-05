# AN-022 - QIS Automation and Post-Processing

## Overview
This application note demonstrates basic automation with Quarch Instrument Server (QIS) and post-processing of raw data after recording. The example script records data at a high rate and post-processes it to lower rates, ending with 100uS and 500uS sample rates.

## Features
- Scanning for Quarch modules via QIS
- Connecting to a Quarch module via QIS
- Setting up and running QIS data streaming functions
- Post-processing raw data to different sample rates

## Requirements

### Hardware
- Quarch Power Module (PPM/PAM)
- Host PC
- Power supply for the relevant module
- USB or LAN connection to the module

### Software
- Python (3.x recommended)
  - [Download Python](https://www.python.org/downloads/)
- Java 8, with JavaFX
  - [Java 8 with JavaFX](https://quarch.com/support/faqs/java/)
- Quarchpy Python package
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- Quarch USB driver (Required for USB-connected devices on Windows only)
  - [Quarch USB Driver](https://quarch.com/downloads/drivers/)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)

## Instructions

1. Install the required items listed above.
2. Connect a PPM/PAM device via USB or LAN and power it up.
3. Run the script and follow the instructions in the terminal.

## Provided Files

- `PowerExamples.py` - Main script to demonstrate QIS automation and post-processing.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
# AN-021 - QPS Automation and Post-Processing

## Overview
This application note demonstrates basic automation with Quarch Power Studio (QPS) and post-processing of raw data after recording. The example script records data at a high rate and post-processes it to lower rates, ending with 100uS and 500uS sample rates.

## Features
- Scanning for Quarch devices
- Connecting to a selected Quarch power module
- Setting up module record parameters
- Recording and exporting raw data
- Post-processing raw data to different sample rates

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

1. **Install the required software**
2. **Setup the hardware**
3. **Run the script**
   - Follow the on-screen instructions to post process QPS data

## Provided Files

- `PowerExamples.py` - Main script to demonstrate QPS automation and post-processing.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
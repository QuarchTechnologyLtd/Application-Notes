# AN-019 - HD PPM Calibration

## Overview
This application note provides detailed steps for calibrating HD Programmable Power Modules (PPM). It includes the necessary requirements, hardware setup, software installation, and a step-by-step guide to perform calibration.

## Features
- Detailed hardware setup instructions
- Step-by-step calibration process
- Troubleshooting and verification tips

## Requirements

### Hardware
- DUT PPM QTL1999 or QTL1995
- Keithley 2460 source meter
- HD Calibration Switchbox QTL2294

### Software
- Python (3.x recommended)
  - [Download Python](https://www.python.org/downloads/)
- Quarchpy Python package
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- Quarch USB driver (Required for USB-connected devices on Windows only)
  - [Quarch USB Driver](https://quarch.com/downloads/drivers/)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)
- Calibration software package from Quarch
  - [Quarch Calibration Package](https://quarch.com/products/quarchcalibration-python-package/)

## Instructions

1. **Install the required software**
2. **Setup the hardware**
3. **Run the calibration script**:
   - Run the main script in quarch calibration or call `python -m quarchpy.run calibration`


## Troubleshooting
Refer to the document for detailed troubleshooting steps and tips to ensure smooth calibration of the HD Power Permissive Module.

## License
- This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
# AN-031 - QIS Capture In-Memory Example

## Overview
This application note demonstrates control of AC power modules via Quarch Instrument Server (QIS) and saving the outputted QIS data to a CSV file. Automating via QIS provides a lower overhead than running Quarch Power Studio (QPS) in full but still provides easy access to data for custom processing. This example uses Quarchpy functions to set up an AC power module with QIS.

## Features
- Connecting to a Quarch Power Module (AC PAM)
- Setting up and running data streaming functions
- Saving QIS stream data to a CSV file

## Requirements

### Hardware
- Quarch Power Module (AC PAM)
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

1. Connect an AC PAM device via USB or LAN and power it up.
2. Run the script and follow any instructions on the terminal.

## Provided Files

- `QisAcStreamExample.py` - Script demonstrating control of AC power modules via QIS and saving the outputted QIS data to CSV.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
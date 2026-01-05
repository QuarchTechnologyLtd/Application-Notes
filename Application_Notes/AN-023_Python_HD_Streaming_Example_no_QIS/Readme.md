# AN-023 - Python HD Streaming Example (No QIS)

## Overview
This application note demonstrates basic automation with Quarch Power Modules using Python without the Quarch Instrument Server (QIS). The example scripts show how to record data at a high rate and post-process it to lower rates, ending with 100uS and 500uS sample rates.

## Features
- Scanning for Quarch modules via TCP
- Connecting to a Quarch module
- Setting up and running data streaming functions
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
- Quarchpy Python package
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- pandas Python package
  - `pip install pandas` More: [Pandas](https://pandas.pydata.org/)
- FIO (Flexible I/O Tester)
  - [FIO](https://github.com/axboe/fio)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)

## Instructions

1. Install the required items listed above.
2. Connect a PPM/PAM device via USB or LAN and power it up.
3. Run the script and follow the instructions in the terminal.

## Provided Files

- `PowerExamples.py` - Script demonstrating basic automation and data streaming with post-processing.
- `PythonExamples-SelfContained.py` - Script demonstrating a self-contained example with automation and data streaming using FIO.
- `intel_custom.py` - Custom Python module used for handling HD streaming.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
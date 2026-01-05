# AN-030 - Merging Custom Data into a QPS Trace

## Overview
This application note demonstrates the merging of custom data into a Quarch Power Studio (QPS) trace. The example script pulls in custom user data from another source (a water meter in this case) and creates new channels in QPS. It then imports the data into those channels. Note that the files supplied here will import volume/flow data into any QPS trace that is at least 10 seconds long. You can use this as a tool, pick your own QPS streams, and edit the CSV file or provide your own.

## Features
- Merging custom user data into a QPS trace
- Creating new channels in QPS
- Importing data into QPS channels

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

1. Run the script and follow the instructions on screen.
2. Select your trace when prompted and choose if you want to make a copy to add the data to or add to the original file.
3. Select the CSV data to add.
4. Look at the QPS main chart with the newly added data. Try hiding all channels except the newly added ones to see them clearly.
5. End the script and look through the code and comments for a better understanding of how it works.

## Provided Files

- `QpsDataMergeExample.py` - Script demonstrating merging custom data into a QPS trace.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
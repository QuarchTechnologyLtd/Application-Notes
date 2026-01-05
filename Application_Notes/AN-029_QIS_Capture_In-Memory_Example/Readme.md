# AN-029 - QIS Capture In-Memory Example

## Overview
This application note demonstrates control of power modules via Quarch Instrument Server (QIS) and saving the outputted QIS data in-memory. Automating via QIS provides a lower overhead than running Quarch Power Studio (QPS) in full but still provides easy access to data for custom processing. This example uses quarchpy functions to stream data from a quarch power module and dump it into a CSV file.

## Features
- Connecting to a Quarch Power Module (PPM)
- Setting up and running data streaming functions
- Saving QIS stream data in-memory
- Processing and analyzing in-memory data

## Requirements

### Hardware
- Quarch Power Module (PPM)
- Host PC
- USB or LAN connection to the module

### Software
- Python (3.x recommended)
  - [Download Python](https://www.python.org/downloads/)
- Java 8 with JavaFX
  - [Java 8 with JavaFX](https://quarch.com/support/faqs/java/)
- Quarchpy Python package
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- Quarch USB driver (Required for USB-connected devices on Windows only)
  - [Quarch USB Driver](https://quarch.com/downloads/drivers/)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)

## Instructions

1. Connect a PPM/PAM device via USB or LAN and power it up.
2. Run the script and follow any instructions on the terminal.

## Provided Files

- `QisStreamExample-InMemory.py` - Script demonstrating control of power modules via QIS and saving the outputted QIS data in-memory.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
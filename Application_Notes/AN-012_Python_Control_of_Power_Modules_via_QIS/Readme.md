# AN-012 - Python Control of Power Modules via QIS

## Overview
This application note demonstrates the control of Quarch Power Modules via QIS (Quarch Instrumentation System) using the `quarchpy` Python package. Automating via QIS provides a lower overhead compared to running QPS (Quarch Power Studio) in full, but still offers easy access to data for custom processing. This example script streams data from a Quarch power module and dumps it into a CSV file.

## Features
- Scanning for Quarch modules via QIS
- Connecting to a Quarch module via QIS
- Setting up and running QIS data streaming functions

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
3. Run the script and follow any instructions on the terminal.

## Provided Example Scripts

- `QisStreamExample.py` - Demonstrates scanning for Quarch modules, connecting to a module, and running various data streaming functions based on the selected module.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
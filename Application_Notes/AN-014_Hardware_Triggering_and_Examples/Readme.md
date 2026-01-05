# AN-014 - Hardware Triggering and Examples

## Overview
This application note demonstrates the hardware triggering feature of Quarch modules. It provides example scripts for setting up and using hardware triggers on Quarch modules. These scripts include scanning for modules, connecting to a module, and configuring the modules for specific triggering scenarios.

## Features
- Scanning for Quarch modules
- Connecting to a Quarch module
- Setting up hardware triggers
- Running example scripts for various triggering scenarios

## Requirements

### Hardware
- Quarch Breaker Module that supports triggering
- Quarch Power Module (PPM)
- Host PC
- Quarch Interface Unit
- Power cables for the modules and interface unit

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
2. Connect the relevant Quarch modules to your PC via USB or LAN and power them on.
3. Run the desired script and follow the instructions on the terminal.

## Provided Example Scripts

- `PPM to Ground upon PERST Assert.py` - Demonstrates setting PPM to ground upon PERST ASSERT.
- `Power Rail Delay Upon Power Up.py` - Demonstrates delaying the power rails upon power up.
- `Triggering on Host Power Up.py` - Demonstrates setting up hardware triggers for the breaker and PPM upon host power up.

## Additional Documentation
- `AN-014 - Hardware Triggering and Examples.docx` - Detailed application note for hardware triggering.
- `Scripts User Guide.docx` - User guide for the provided example scripts.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
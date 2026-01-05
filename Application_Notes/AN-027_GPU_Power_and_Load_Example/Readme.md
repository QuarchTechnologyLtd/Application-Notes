# AN-027 - GPU Power and Load Example

## Overview
This application note demonstrates automated control over Quarch Power Studio (QPS) for capturing GPU power and load metrics. The example script shows how to add annotations and datapoints to a QPS stream.

## Features
- Scanning for Quarch devices
- Connecting to a Quarch PPM
- Setting up and running data streaming functions
- Capturing GPU power and load metrics
- Adding custom performance channels to the QPS stream

## Requirements

### Hardware
- Quarch Power Module (PPM)
- Host PC
- USB or LAN connection to the module
- Quarch GPU PAM or similar, set to measure GPU power consumption

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

1. Install the required software listed above.
2. Connect the Quarch module to your PC via USB or LAN and power it on.
3. Run the script and follow the instructions on screen.

## Provided Files

- `GpuCaptureExample.py` - Script demonstrating automated control over QPS to capture GPU power and load metrics.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
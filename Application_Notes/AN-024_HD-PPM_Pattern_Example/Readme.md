# AN-024 - HD PPM Pattern Example

## Overview
This application note demonstrates how to use the pattern generator in a Quarch Programmable Power Module (PPM) from a Python script. The pattern generator can create a wide range of power test cases, such as ramps, glitches, power loss, brownout and ripple. This example creates a ripple 'chirp' on the 5V and 12V rails, where the ripple frequency falls over the length of the pattern, and repeats it at increasing magnitudes. You can add your own checks to confirm that the drive under test handled each run.

## Features
- Connecting to a Quarch Power Module and powering up its outputs
- Building a ripple pattern point by point with the `sig:<rail>:pattern` commands
- Running the pattern on the 5V and 12V rails
- Stepping the ripple magnitude up on each test cycle

## Requirements

### Hardware
- Quarch HD Power Module (QTL1995 or QTL1999)
  - XLC Power Modules (QTL1824, QTL1847) support this feature but have not been specifically tested with this note
- Host PC
- USB or LAN connection to the module
- Drive under test connected to the output of the power module

### Software
- Python (3.x recommended)
  - [Download Python](https://www.python.org/downloads/)
- Quarchpy Python package (version 2.0.20 or later)
  - [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- Quarch USB driver (Required for USB-connected devices on Windows only)
  - [Quarch USB Driver](https://quarch.com/downloads/drivers/)
- Check USB permissions if using Linux
  - [USB Permissions](https://quarch.com/support/faqs/usb/)

## Instructions

1. Install Python and quarchpy (`pip install quarchpy`, or `pip install --upgrade quarchpy` to update an existing install).
2. Connect the power module to the host PC via USB or LAN, connect the drive under test to its output, and power the module on.
3. Optionally edit the variables at the top of `PatternExample.py`:
   - `start_magnitude` / `end_magnitude` - the first and last ripple magnitude in mV, applied above and below the nominal voltage (so the peak-to-peak ripple is twice this value)
   - `incr_magniture` - the step in mV between test cycles
4. Run the script: `python PatternExample.py`
5. Select your module from the list. If the output mode is not set automatically by an HD fixture, enter the output voltage when prompted (3V3 or 5V).
6. The script writes and runs the pattern once for each magnitude, then closes the connection.

The resulting pattern can be viewed by recording the module in Quarch Power Studio (QPS).

## Provided Files

- `PatternExample.py` - Script that generates and runs a ripple pattern of increasing magnitude on an HD PPM.
- `AN-024 - HD PPM Pattern Example.docx` - The full application note, including setup steps and an example of the pattern viewed in QPS.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

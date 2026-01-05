# AN-004 - USB Control of Power Modules

## Overview
This application note explains how to control Quarch Programmable Power Modules (PPMs) using Python and a USB connection. It provides example scripts demonstrating basic commands, RAM capture, and streaming capture.

## Features
- Control Quarch **power modules** via USB
- Perform **basic commands, RAM capture, and streaming capture**
- Compatible with both **Windows and Linux**

## Requirements

### Hardware
- Supported Quarch Power Modules:
  - **Original Power Modules**: QTL1455, QTL1658, QTL1730, QTL1727
  - **XLC Power Modules**: QTL1824, QTL1847

### Software
- **Python 2.x** (legacy support; Python 3.x not supported)
- **Quarch USB Driver** (for Windows)
- **libusb1 Python package**

## Provided Example Scripts
- **BasicFunctionTest.py** - Lists connected USB devices and validates communication.
- **QuarchDumpExample.py** - Captures data to module RAM and exports a CSV file.
- **QuarchStreamExample.py** - Streams power data continuously to a CSV file.
- **SimpleCommandTest.py** - Runs a series of basic power module commands.

## Notes
- This method is **legacy**; for modern implementations, refer to **AN-012 (QIS-based control).**
- Installation steps and script usage are documented in the **accompanying Word document**.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
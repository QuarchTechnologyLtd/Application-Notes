# AN-017 - QPS Performance Test with FIO

## Overview
This application note demonstrates using FIO and Quarch Power Studio (QPS) to run performance tests on a drive, with power and performance data displayed. The example script allows users to configure test parameters, run FIO workloads, and visualize the results.

## Features
- Scanning for Quarch modules
- Connecting to a Quarch module via QPS
- Setting up power outputs
- Running FIO tests on selected targets
- Fetching and plotting performance data into QPS

## Requirements

### Hardware
- Quarch Power Module (PPM or PAM)
- Host PC
- Power supply for the relevant module
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
- FIO (Flexible I/O Tester)
  - [FIO GitHub](https://github.com/axboe/fio)

## Instructions

1. Install the required items listed above.
2. Connect a Quarch power module to your PC via USB or LAN.
3. Run the `performanceTestFIO.py` script and follow the instructions on the terminal.
   - Select the Quarch Power module you are streaming with from the table displayed in the console window.
   - Select the block device or the drive partition you wish to test.
   - Choose the folder location for FIO data.
   - Optionally, type an averaging rate for the Quarch Power Module (default is 1k).

## Provided Example Files

- `performanceTestFIO.py` - Main script to run FIO tests and display power and performance data.
- `jobFileExample.fio` - Example FIO job file for running 16k read tests.

## License
- This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
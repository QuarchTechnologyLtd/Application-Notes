# AN-034 - Multiple AC PAMs Synchronous Streaming

## Overview
This Application Note uses 2 AC Power Analysis Modules to stream synchronously, with the user choosing to stream
over QIS or over QPS. Either option will export a CSV, which is then merged, and opened in QPS.

The data recorded is from the same source, but due to the high power requirements, 2 AC PAMs are required. Recommended
TCP PoE connection rather than USB. 

This AN uses multicore processing to reduce the delay between one stream starting and the next stream starting. In testing
this was shown to be in the low ms range, typically less than 1 mains wave cycle (50Hz, 20ms). This is considered 
sufficient for this AN. Factors found to affect the delay: Network traffic and latency, CPU performance, internal PAM latency.

## Features
This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Post processing of CSV data
-Importing CSV data into QPS to display


## Requirements
### Hardware
- 2x AC PAMs 
- Host PC with firewall permissions (Windows or POSIX)
- LAN Connection to both modules

### Software
- Python (3.x recommended)
    [Download Python](https://www.python.org/downloads/)
- Quarchpy python package
    [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- GNU Compiler Collection - See below
- psutil python package [Psutil python package](https://pypi.org/project/psutil/)

## Instructions
- Connect AC PAMs to the same LAN as control PC
- Connect AC PAMs to load
- Configure the global variables - PAM_1_ADDRESS,PAM_2_ADDRESS, STREAM_LENGTH
- Run the script

## Provided Files
- `Multiple_AC_PAM_Synchronous_Stream.py` - Script demonstrating control of dual AC Power Analysis modules recording 
the same data, displayed in Quarch Power Studio

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

## GCC Installation Instructions
### If Windows:
Please install MinGW-w64
Download the MSYS2 Installer - https://www.msys2.org/
Open the MSYS2 Terminal and run the command
pacman -S mingw-64-86_64-gcc
Then add C:\msys64\mingw64\bin to the PATH
Once installed and added, please re-run

### If POSIX
Please install MinGW-w64
On ubuntu please run the command

sudo apt install build-essential

On fedora please run the command\n

sudo dnf install gcc glibc-devel

Once installed and added, please re-run
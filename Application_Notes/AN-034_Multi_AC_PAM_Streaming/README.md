# AN-034 - Multiple PAMs Synchronous Streaming - Simple

## Overview - MultiPAM_Stream_Simple
This is a more user-friendly version, which uses standard python, streams over QIS, and has the option to use a hardware trigger. This has fewer requirements
and is easier to use on different systems.
This demonstrates the use of the Quarchpy library, and how to control multiple units. Using USB to connect the PAMs is possible.

This will be heavily system dependent, but the delay between 1 stream starting and the next stream starting, using a hardware trigger,
is as little as 3ms apart, and using a software trigger, as little as 15.8ms apart. Starting the streams sequentially (the default option) 
had delays of as little as 37ms.

The PAMs will stream for a set amount of time, and save the recording into a CSV each. After the streams are complete, the user has the option
to automatically combine the CSVs, and import and display in QPS. 

## Features
This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Post processing of CSV data
-Importing CSV data into QPS to display

## Requirements
### Hardware
- 2x PAMs and PAM Fixtures
- Host PC 
  - Multiple cores (2 minimum)
  - firewall permissions (Windows or POSIX)

### Software
- Python (3.x recommended)
    [Download Python](https://www.python.org/downloads/)
- Quarchpy python package
    [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- 
## Instructions
- Connect PAM Fixtures
- Connect PAMs to control PC

## Provided Files
- `MultiPAM_Stream_Simple` - Script demonstrating more user-friendly version of two PAMs streaming
- `SyncUtils.py` - containing functions not directly related to controlling Quarch modules - e.g. merging CSV.



# AN-034 - Multiple PAMs Synchronous Streaming - Complex
## Overview - MultiPAM_Stream_Complex
This Application Note uses 2 Power Analysis Modules to stream synchronously, with the user choosing to stream over QIS or over QPS. This is better suited
to LAN connection over USB connection, due to lower latency.
Either option will export a CSV, which is then merged, and opened in QPS. These can be AC PAMs (e.g. QTL2843 IEC PAM) or can be DC PAMs (QTL2312). 
In testing, have found that the software trigger and compiled C in this complex version has less delay between the streams.

If using AC PAMs, suggested application is a singular high power requirement source, where one AC PAM is not enough to capture all power.
If using DC PAMs, suggested application is to measure the power used by different components of a single system. e.g. using a QTL2983 GPU PAM,
and a QTL3069 Gen6 EDSFF PAM, in the same system.

This AN uses multicore processing to reduce the delay between one stream starting and the next stream starting. In testing
this was shown to be in the low ms range, typically less than 1 millisecond.
Factors found to affect the delay: Network traffic and latency, CPU performance, internal PAM latency.

## Features
This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Post processing of CSV data
-Importing CSV data into QPS to display


## Requirements
### Hardware
- 2x AC PAMs 
- Host PC 
  - Multiple cores (2 minimum)
  - firewall permissions (Windows or POSIX)
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
- `Multiple_PAM_Sync_Stream_Complex.py` - Script demonstrating control of dual AC Power Analysis modules recording 
the same data, displayed in Quarch Power Studio


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

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

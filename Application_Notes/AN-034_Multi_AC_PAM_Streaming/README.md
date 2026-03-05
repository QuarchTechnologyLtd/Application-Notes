# AN-034 - Multiple PAMs Synchronous Streaming - Simple

## Overview - MultiPAM_Stream_Simple
This is a simpler, more user-friendly version of Sync Streaming, which uses standard python, streams over QIS, and has the option to use a hardware trigger. 
This demonstrates the use of the Quarchpy library, and how to control multiple units. Using USB to connect the PAMs is possible. 
This script works with both DC PAMs (QTL2312), and AC PAMs (e.g. QTL2582), or a combination of both.

This script has 3 ways of starting the streams. Option 1 is using an MCX triggering cable between the PAMs. 
PAM 1 trigger out, connected to PAM 2 trigger in. 
Option 2 is starting the PAM streams sequentially. 
Option 3 is using a software trigger, uses 2 CPU cores. 
The CPU cores are kept busy, until a set time, after which the stream is started. 
The PAM streams are executed on separate cores, which reduces the delay between stream 1 and stream 2 starting.

This will be heavily system dependent, but the delay between 1 stream starting and the next stream starting, using a hardware trigger, 
is as little as 3ms apart, and using a software trigger, as little as 15.8ms apart. 
Starting the streams sequentially (the default option) had delays of as little as 37ms.

The PAMs will stream for a set amount of time, and save the recording into a CSV each. 
After the streams are complete, the user has the option to automatically combine the CSVs, and import and display in QPS.

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
This Application Note uses 2 Power Analysis Modules to stream synchronously, over QIS.
This will export a CSV, which is then merged, and opened in QPS.

If using AC PAMs, suggested application is a singular high power requirement source, where one AC PAM is not enough to capture all power.
If using DC PAMs, suggested application is to measure the power used by different components of a single system. e.g. using a QTL2983 GPU PAM,
and a QTL3069 Gen6 EDSFF PAM, in the same system.

To reduce latency from one stream starting to the next stream starting, this script uses a compiled C file to spin
up 2 CPU cores, and keep them busy, until the start_stream command is called. This requires the use of a compiler -
GCC recommended. There is a check to not recompile, if the file is there

In testing, when connected over IP the desync was typically less than 5ms worst case scenario, with most being less than 1ms
between 1 stream starting and the next stream starting. This is likely related to network latency. USB is slower in testing

If you are running multiple times, rename the CSVs and saved QPS file, otherwise the CSVs will be overwritten, and automatic QPS import will fail.
In this script, there are various optional hardcodes - stream length, stream resample rate, number of pams, pam addresses, whether to display in QPS or not.
If running multiple times, it is suggested to hardcode these to speed up the time in between tests.

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
- Connect PAMs to the same LAN as control PC
- Connect PAMs to load
- Change the global variables: STREAM_LENGTH, STREAM_RESAMPLE_RATE
- Run the script

## Provided Files
- `Multiple_PAM_Sync_Stream_Complex.py` - Script demonstrating control of dual AC Power Analysis modules recording 
the same data, displayed in Quarch Power Studio
- `syncComplexClasses.py` - Separates out the more complex code, not directly related to controlling Quarch modules.
- `SyncUtils.py` - containing functions not directly related to controlling Quarch modules - e.g. merging CSV.


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

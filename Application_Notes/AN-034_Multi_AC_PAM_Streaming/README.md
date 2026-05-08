# AN-034 - Multiple PAMs Synchronous Streaming - Simple

## Overview - MultiPAM_Stream_Simple
This script can be used to stream from 2 PAMs simultaneously. 
This uses standard python, streams over QIS, and has the option to use a hardware trigger.
There is an alternate version, which can be used for up to 5 PAMs, and has less delay between streams.
This demonstrates the use of the Quarchpy library, and how to control multiple units.
Using USB to connect the PAMs is possible.
This script works with both DC PAMs (QTL2312), and AC PAMs (e.g. QTL2582), or a combination of both.

This script has 2 ways of starting the streams.
Option 1 is using an MCX triggering cable between the PAMs. PAM 1 trigger out, connected to PAM 2 trigger in. 
This is the preferred option if DC PAMS (QTL2312) are used.
Option 2 is using a software trigger, uses 2 CPU cores. 
The CPU cores are kept busy, until a set time, after which the stream is started.
The PAM streams are executed on separate cores, which reduces the delay between stream 1 and stream 2 starting.
This is intended for modules that don't have triggering - most AC PAMs.

This will be heavily system dependent, but the delay between 1 stream starting and the next stream starting, using a hardware trigger,
is as little as 3ms apart, and using a software trigger, as little as 15.8ms apart. Starting the streams sequentially (the default option)
had delays of as little as 37ms.

The PAMs will stream for a user selectable length of time, and save the recording into a CSV each. 
After the streams are complete, the user has the option
to postprocess the data, and view the data in QPS.

This script is designed for use with PAMs, and variables are named as such, but it should be possible to use with PPMs. 
There are some comments indicating where PPM setup can be done, and mid-stream commands can be run.

Suggested applications of this:
Measuring 2 devices concurrently: e.g. an SSD and a GPU
Measuring AC power where the host power is above the PAM's rating.

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
This version is much more complex. The simple version is the preferred option for most use cases.
This version is intended for power users, when 3 or more PAMs are required, or sub-millisecond delays between streams starting.
Each PAM will record into a CSV, which will then be optionally merged into a master CSV, and displayed in QPS.

Suggested application is for DC PAMs, to measure a GPU and up to 4 drives in a single system,
or for AC PAMs to measure power greater than the individual PAMs power rating. 

To reduce latency from one stream starting to the next stream starting, this script uses a compiled C file to spin
up 2 CPU cores, and keep them busy, until the start_stream command is called. This requires the use of a compiler -
GCC recommended, and instructions are provided to install it on Windows, and ubuntu and fedora distros of Linux.

In testing, when connected over IP the desync was typically less than 5ms worst case scenario, with most being less than 1ms
between 1 stream starting and the next stream starting. This is likely related to network latency. USB is slower in testing.
This was tested with 2 PAMs only, expect larger delays with 3 or more PAMs.

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
- 2 or more PAMs and PAM Fixtures
- Control PC 
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
- sudo apt install build-essential

On fedora please run the command\n

- sudo dnf install gcc glibc-devel

Once installed and added, please re-run

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

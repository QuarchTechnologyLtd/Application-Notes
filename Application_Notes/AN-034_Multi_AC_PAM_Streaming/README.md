# AN-034 - Multiple PAMs Synchronous Streaming - Simple

## Overview - MultiPAM_Stream_Simple
This is a relatively simple, user-friendly version, which uses standard python, streams over QIS, 
and has the option to use a hardware trigger.
This demonstrates the use of the Quarchpy library, and how to control multiple units. 
Using USB to connect the PAMs is possible.
This script works with both DC PAMs (QTL2312), and AC PAMs (e.g. QTL2582), or a combination of both.

This script has 3 ways of starting the streams. 
Option 1 is using an MCX triggering cable between the PAMs. PAM 1 trigger out, connected to PAM 2 trigger in
Option 2 is starting the PAM streams sequentially. 
Option 3 is using a software trigger, uses 2 CPU cores. The CPU cores are kept busy, until a set time, after which the stream is started.
The PAM streams are executed on separate cores, which reduces the delay between stream 1 and stream 2 starting.

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


## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

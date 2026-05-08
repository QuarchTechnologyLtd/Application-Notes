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


## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

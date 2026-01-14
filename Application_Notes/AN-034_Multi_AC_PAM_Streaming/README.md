# AN-034 - Multiple AC PAMs Synchronous Streaming

## Overview
This Application Note uses 2 AC Power Analysis Modules to stream synchronously, with the user choosing to stream
over QIS or over QPS. Either option will export a CSV, which is then merged, and opened in QPS.

The data recorded is from the same source, but due to the high power requirements, 2 AC PAMs are required. Recommended
TCP PoE connection rather than USB.

Both PAM data streams can be viewed side by side. Connecting to both PAMs via TCP has a current lag of approximately
63 milliseconds, between one trace starting recording and the second trace starting recording.

## Features
This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Post processing of CSV data
-Importing CSV data into QPS to display


## Requirements
### Hardware
- 2x AC PAMs 
- Host PC with firewall permissions
- LAN Connection to both modules

### Software
- Python (3.x recommended)
    [Download Python](https://www.python.org/downloads/)
- Quarchpy python package
    [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)
- tkinter python package (Used for GUI)
    [Tkinter](https://docs.python.org/3/library/tkinter.html#)

## Instructions
- Connect AC PAMs to the same LAN as control PC
- Connect AC PAMs to load
- Change the global variables: pam_1_address, pam_2_address, stream_length
- Run the script

## Provided Files
- `Multiple_AC_PAM_Synchronous_Stream.py` - Script demonstrating control of dual AC Power Analysis modules recording 
the same data, displayed in Quarch Power Studio
- 
## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
# AN-035 - RefClk delay from CLKREQ#

## Overview
This Application Note uses a breaker to delay RefClk from CLKREQ#, and a PAM to verify that this is happening correctly.
This requires a triggering breaker, and a loopback cable as we output CLKREQ#, and set up the trigger in to start a power up event.
The delay is set by the user, ranging from 1ms to 1 second. 

This app note was created using a QTL3238 Gen6 x16-0 AIC Breaker, and a QTL3216 Gen6 AIC PAM. As such, the signal names in this script are set for these.
To use with different modules, this may need different names set. The command _help names_ returns the names of signals on the module.
The PAM needs to be able to measure RefClk - most Gen6 modules are able to measure this.

This is intended to help verify compliance with the PCIe spec - the relevant sections of the spec are displayed in the terminal at the end of the script.

## Features
This AN-035 uses the quarchpy python package and demonstrates
-Connections to a breaker and a PAM
-Setup of a triggering breaker
-Setup of a PAM stream over QPS

## Requirements
### Hardware
- PAM and a PAM Fixture capable of measuring RefClk (Most Gen6 PAM fixtures)
- Triggering breaker
- MCX loopback cable
- Separate host and control PCs

### Software
- Python (3.x recommended)
    [Download Python](https://www.python.org/downloads/)
- Quarchpy python package
    [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)


## Instructions
- Insert the breaker into the host system, connect to the Torridon Interface Kit or Array Controller
- Insert the PAM into the breaker, connect to the PAM
- Connect the breaker and PAM to the control PC
- While the script is streaming, power up the host PC
- Review the QPS trace, confirm that the device functions
- Repeat the test with different delays

## Provided Files
- `RefClkDelayFromClkReq.py` - Script

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
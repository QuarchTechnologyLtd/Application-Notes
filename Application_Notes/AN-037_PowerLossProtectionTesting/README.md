# AN-037 - Power Loss Protection Testing

## Overview
This App Note is designed to test the PLP implementation of your drive, using a Quarch PPM (QTL1999,QTL1995,QTL3358) and a power injection fixture.

We start by finding the brownout threshold of the drive by running
Application Note 14, Voltage Margining. 

We can use FIO loads to write a load to the drive, and we can also check whether there is any data loss from when power is lost. 
We run different FIO loads to find edge cases and corner cases of where data may be lost.

Once this is found, we start a ramp test, ramping the voltage rails in steps around the brownout threshold,
to get PLP on the verge of kicking in. This is repeated with different timings, and different jumps above and below the threshold.

The next test is to crowbar the power rails, from nominal down to brownout, and also down to ground. We change over the slew rates.

We run the test with a number of different parameters, to get a more comprehensive test result. 
The default parameters were found during our testing,
as they gave us edge and corner cases, but this will vary significantly with drives, so you should consider changing the parameters as well.

After the test is completed, we save the QPS recording (displayed during test), 
and also save a CSV of any failed test results with their test parameters to re-test easily.

Please note: This is designed for Linux only. Windows is a lot less tolerant to hot-plugs.


## Features
This app note uses the quarchpy python package and demonstrates
- Connecting and streaming from a PPM
- PPM Patterns
- FIO Loads
- Pandas analysis

## Requirements
- Quarch PPM (QTL1999,QTL1995,QTL3358) connected over TCP
- Power Injection Fixture

### Hardware
- Local Linux PC that is hot-pluggable (either native or host card)
- Enterprise SSD with PLP

### Software
- Python 3.12 or later
- Quarchpy v2.2.23 or later
- FIO installed and added to the path
- Python Pandas "pip install pandas"

## Instructions
With the system off
- Connect the host to the power injection fixture
- Connect the drive to the power injection fixture
- Connect the power injection fixture to the PPM
- Connect the PPM via TCP to the host PC
- Connect power to the PPM
- Power on the system
- Ensure drive shows under lsblk
- With administrator rights, run AN-037_PLP_Test.py

## Provided Files
- AN-037_PLP_Test.py - Main script to run
- fio_functions.py - A separate script containing essential functions
- fio_configs.json - The FIO loads stored in a json
- Readme.md

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
# AN-005 - Perl Control of Quarch Modules

## Overview
This application note explains how to control Quarch Modules using Perl. It provides example scripts for issuing commands to Quarch modules via serial and Telnet connections, and covers the installation of necessary Perl libraries.

## Features
- Control Quarch modules via serial and Telnet connections
- Demonstrates connection setup and command execution
- Compatible with both Windows and Linux

## Requirements

### Hardware
- Supported Quarch Modules: Hot-plug Module, Switch Module, Power Margining Module
- Host PC
- Power supply for the relevant Module
- LAN/Serial Connection to the module

### Software
- Perl


## Provided Example Scripts
- `Perl Control Examples.pl` - Demonstrates issuing commands to a Quarch module using a Telnet connection.
- `TorridonCommon.pl` - Demonstrates issuing commands to multiple Quarch modules via a Torridon array controller using a serial connection. Logs data from the serial port to a specified file (Quarch.log).

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
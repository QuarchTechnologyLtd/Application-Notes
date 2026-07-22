# AN-036 - Injecting and Counting Errors

## Overview
This Application Note uses a cable tester to count errors in a link, and a breaker to inject errors.
We loop over error lengths, error types (PRBS), number of lanes being glitched, and the link speed.

We then save the errors counted in a CSV

## Features
This app note uses the quarchpy python package and demonstrates
- Automating manual testing
- Script control of cable tester, and breaker

## Requirements
- Control PC running Windows or Linux, with Python installed

### Hardware
- Cable tester (QTL2250), breaker (QTL2171) and cable all in the same form factor (QSFP28 was used in testing)
- Modules connected to the control PC

### Software
- Python (3.x recommended)
    [Download Python](https://www.python.org/downloads/)
- Quarchpy python package
    [Quarchpy Python Package](https://quarch.com/products/quarchpy-python-package/)

## Instructions
- Connect cable to cable tester via breaker
- Connect cable tester and breaker to control PC
- Run the script

## Provided Files
- 'InjectingAndCountingErrors.py'

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)
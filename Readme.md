# AN-002 - Simulating Physical Layer Faults

## Overview
This application note demonstrates the use of a Quarch breaker module to inject standard forms of physical layer faults onto a high-speed data bus such as SAS, SATA, or PCIe. The example is also relevant for other interfaces like USB, CAN, and RJ-45.

It will work with any Quarch breaker module, but you may need to tweak the signal names depending on the module you are using, as SAS and PCIe use different naming conventions.

## Features
- Simulate **physical layer faults** on high-speed data buses
- Modify signal behavior dynamically
- Automate testing with **Quarchpy Python API**

## Requirements

### Hardware
- Quarch Breaker Module (e.g., QTL2358 Gen5 x16 AIC Breaker)
- Device Under Test (DUT)
- Required cables and adapters

### Software
- Quarchpy Python API
- Python 3.x
- Quarch USB driver (Required for USB-connected devices on Windows)

## Getting Started

### 1️⃣ Read the Word Document
- Learn about **physical layer fault injection** using Quarch modules.

### 2️⃣ Run the Python Script and Step Through the Example
- Execute the provided Python script with the **instructions in the comments**.
- Step through the code to understand how each section works.
- Modify parameters and observe the effect on fault injection.

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

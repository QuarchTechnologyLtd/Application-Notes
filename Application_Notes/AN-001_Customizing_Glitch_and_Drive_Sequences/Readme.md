# AN-001 - Customizing Glitch and Drive Sequences

## Overview
This application note provides guidance on customizing power and sideband sequenceing using Quarch test automation tools. A customer had a specific timing sequence between PERST, REFCLK and 12V supply on a PCIe storage device that they needed to recreate.  This example makes use of the 'Breaker' range of products from Quarch, which allows inidvidual control of each active pin on the PCIe interdace.  

The example code can be used as a base for many other similar test scenarios and on other physical interfaces.  Setup instructions are given at the top of the python file.

The overview for these products are described here: https://quarch.com/solutions/hot-swap-and-fault-injection/

## Features
- Create a sequence of events using direct control over multiple pins on a PCIe device (or similar)
- Demonstrate simple control over power and sidebands sequences
- Use **driving** to force a sideband into the required state
- Compatible with Quarch test automation hardware

## Requirements

### Hardware
- Quarch Breaker Module such as a PCIe x16 Slot breaker: https://quarch.com/products/gen5-pcie-x16-breaker-module/
- Quarch interface kit or other controller: https://quarch.com/products/torridon-interface-kit/
- Device under test (SSD or similar)
- Host PC and and adaptors or cables required to connect to the device

### Software
- Quarchpy python API
- Python 3.x recommended
- Serial or USB drivers for hardware communication

## Getting Started

### 1️⃣ Read the word document
- Learn about the customers test case and how we re-created it

### 2️⃣ Run the python script and stepthrough the examle
- Run the python script with instructions included in comments at the top
- Now you can extend the code to run additonal tests, or target a different interface

## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

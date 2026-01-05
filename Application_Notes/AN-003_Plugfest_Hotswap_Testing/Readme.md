# AN-003 - Plugfest Hotswap Testing

## Overview
This application note provides guidance on performing **hotswap testing** for U.2 NVMe drives, following the UNH-IOL Plugfest test methodology. It utilizes **Quarch modules** in combination with the **QuarchPy** and **QuarchQCS** Python packages to automate the process.

This procedure ensures compliance with **Plugfest requirements**, validates **hot-plug performance**, and helps identify potential **drive or host issues**.

## Features
- Perform **hotswap testing** for **NVMe U.2 drives**
- Automate tests with **Python and PowerShell scripts**
- Supports **multiple plug speeds**: Standard, Fast, Slow, and Very Slow
- Compatible with **Linux and Windows**
- **Additional advanced tests**: Dual-port handling, pin-bounce scenarios

## Requirements

### Hardware
- **Quarch QTL1743** – PCIe Drive Control Module
- **QTL1260 Interface Kit**
- **Host System** (Linux or Windows)
- **NVMe Device** (PCIe SFF drive)
- Required cables (USB, power)

### Software
- **Python 3.x** (Recommended)
- **QuarchPy** Python package  
  Install with: `pip install quarchpy`
- **QuarchQCS** Python package  
  Install with: `pip install quarchqcs`
- **SmartCtl** (for drive detection)  
  Install from: [smartmontools](https://www.smartmontools.org/)
- **FTDI Driver** (for USB Virtual COM Port)  
  Download: [FTDI VCP Drivers](http://www.ftdichip.com/Drivers/VCP.htm)
- **Quarch USB Driver** (Windows only)  
  Download: [Quarch USB Driver](https://quarch.com/downloads/driver/)

### Linux Additional Requirements
- **PCIUTILS** (Required for PCIe device detection)  
  Install with:  
  ```bash
  sudo apt install pciutils
  

## Getting Started

### 1️⃣ Read the Word Document
- Learn about **hotswap testing** using Quarch modules.

### 2️⃣ Run the Python Script
- Follow the **instructions in the script** to execute tests.
- Modify parameters as needed to observe different behaviors.


### Additional Tests
- Dual-Port Testing: Validate drive handling with port A and B individually.
- Pin-Bounce Testing: Simulate real-world electrical issues in hotplug scenarios.
- Edge Cases: Modify plug speeds beyond Plugfest standards (e.g., 5ms or 250ms).


## License
This project is provided under the terms specified at:
[Quarch Legal](https://quarch.com/legal/)

"""
This script is designed to use a SerialCables host card, which can count errors at the physical layer, and a breaker

Write data to the drive using FIO, at ~30% load initially

Inject glitches onto a single Tx/Rx pair to see the effect

Once verified we can see errors, build a matrix of effects
Long glitches vs short glitched
    recoverable, non-recoverable, fatal errors
More glitches - PRBS and cycling
    Do we see IO rates fall off
Difference between glitching Tx/Rx to the entire lane, to the entire port
What do different FIO profiles show

Step 1
Verify how to count physical errors - SC Hostcard
"""
import os
import time

import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.user_interface import listSelection
from quarchpy.fio import *

import tkinter as tk
from tkinter import filedialog

from serialcables_atlas3 import Atlas3

# Path where stream will be saved to (defaults to current script path)
stream_path = os.path.dirname(os.path.realpath(__file__))

def main():
    requiredQuarchpyVersion("2.2.19")

    #Set up the host card
    host_card = setup_host_card()



    #Get user to specify FIO directory using TKInter
    root = tk.Tk()
    tkFileDialog = filedialog
    root.withdraw()

    print("\n>>> Select a folder for FIO Data:")
    #Request user to select the folder to use using TKInter
    try:
        testDirectory = tkFileDialog.askdirectory()

    # If TKInter didn't work, ask for filepath manually
    except Exception as e:
        print(f"Error opening file: {e}")
        testDirectory = input("Failed to open folder dialog, the enter the folder path for FIO to access\n>")

    #If no filepath was entered, raise an exception
    if testDirectory == "":
        raise Exception("No directory selected")

    print("Selected : " + testDirectory)

    # FIO needs colons escaped when passing "directory" or "filename" look at FIO documentation online for more info.
    testDirectory = testDirectory.replace(":", "\:")  # escape colons from tkinter input.
    # testDirectory='D\\:/Copy stuff here/fioData:' #You could hardcode the path.

    #Creates filename in the format YYMMDD-HHMMSS with current timestamp
    file_name = time.strftime("%Y%m%d-%H%M%S", time.gmtime())

    #We will run FIO using a pre-written file ('file' mode execution)
    #Note, the path for FIO testing must be specified within the file
    #Set this to a valid path first using the "directory=" parameter of the .fio file

    arguments = {"directory": testDirectory, "output": "testFile"}







    while True: #Error counting
        #Gets port status
        ports = host_card.get_port_status()
        counters = host_card.get_error_counters()

        #For each MCIO port, check if its degraded
        for port in ports.ext_mcio_ports:
            if port.is_degraded:
                print(f"WARNING: Port {port.port_number} is degraded")
                print(f"Speed: {port.speed} Max: {port.max_speed}")

        #If theres at least 1 error, display the error
        if counters.total_errors > 0:
            for c in counters.ports_with_errors:
                print(f"Port {c.port_number}: {c.total_errors} errors")

def fio():
    pass

def setup_host_card():
    com_port = "COM14"

    #Opens connection to Atlas host card
    with Atlas3(com_port) as card:
        #Gets version
        info = card.get_version()
        print(f"Model: {info.model}")
        print(f"SBR Version: {info.sbr_version}")
        print(f"MCU Version: {info.mcu_version}")

        #Gets info
        status = card.get_host_card_info()
        print(f"Temperature: {status.thermal.switch_temperature_celsius}")
        print(f"Power: {status.power.load_power}W")

        #Gets status per MCIO port connected
        ports = card.get_port_status()
        for port in ports.ext_mcio_ports:
            if port.is_linked:
                print(f"Port {port.port_number}: {port.speed} x {port.width}")

        #Built in self test
        bist = card.run_bist()
        print(f"BIST: {'PASS' if bist.all_passed else 'FAIL'}")

    return card


if __name__ == "__main__":
    main()
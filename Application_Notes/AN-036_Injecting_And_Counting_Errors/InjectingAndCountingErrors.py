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
import subprocess
import time

import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import scanDevices, userSelectDevice, get_quarch_device
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

    #Connect to the breaker
    device_list = scanDevices("all", favouriteOnly=True)

    module_str = userSelectDevice(device_list, additionalOptions=["Rescan", "All Conn Types", "Quit"], nice=True)

    #Optional hardcode - uncomment this, comment in lines above if you know the address of the module you want to connect to
    #module_str = "USB:QTL3238-01-001"

    #If Quit has been selected, close nicely
    if module_str == "Quit":
        return 0

    breaker = get_quarch_device(module_str)

    print(f"Connected to {breaker.send_command('hello?')}")

    #Set breaker into default state
    breaker.send_command("CONFig:DEFault STATE")

    #We setup the FIO command here, with the target directory specified above to a target file
    #Target rate is aimed towards a Gen5 x4 drive, with approximately a 40% load on the drive
    #Estimate max read/write of 14,000 MB/s in the real world - 40% gives 5600MB/s
    #This will run for 20 seconds (default) while we inject non-fatal errors

    setup_and_start_fio(5600)

    print("Starting FIO at ~40% load")

    #First glitch - single data lane, glitched once
    add_to_glitch(breaker, "PETP0")

    for i in range(0,4):
        # Set single 50ns glitch
        breaker.send_command("GLItch:SETup 50ns 1")
        # Run glitch once
        breaker.send_command("RUN:GLITch ONCE")

        #Wait for 0.5 seconds
        time.sleep(0.5)
        #TODO - COUNT ERRORS HERE

        #Set 50ns glitches to run 10 times
        breaker.send_command("GLITch:SETup 50ns 10")
        #Set 50ns delays between the glitches
        breaker.send_command("GLITch:CYCle:SETup 50ns 10")
        #Runs this group of 10 once
        breaker.send_command("RUN:GLITch ONCE")

        #Wait for 0.5 seconds
        time.sleep(0.5)
        #TODO - COUNT ERRORS HERE

        breaker.send_command("GLITch:CYCle 50ns 10")

        #Sleep 1 second between error injection
        time.sleep(1)


    # Set 50ns glitch
    breaker.send_command("GLItch:SETup 50ns 1")

    # Run glitch once
    breaker.send_command("RUN:GLITch ONCE")

    #TODO - COUNT ERRORS HERE
    #Sleep 1 second between error injection
    time.sleep(1)



    #Add PETN0 to the glitch - now all of PET0 is being glitched
    breaker.send_command("SIGnal:PETN0:GLITch:ENAble ON")

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


def add_to_glitch(breaker, signal_list):
    for signal_name in signal_list:
        breaker.send_command(f"SIGnal:{signal_name}:GLITch:ENAble ON")


def setup_and_start_fio(target_rate, fio_length:str = "20"):
    """
    This is to setup and start a FIO command on a directory
    The engine changes depending on OS
    We create a test file, command arguments and pass in the parameters
    Execute the command

    :param target_rate: Target Rate in MB/s
    :param fio_length: Length of the FIO command in seconds - default 20 seconds
    """

    #Get user to specify FIO directory using TKInter
    root = tk.Tk()
    tkFileDialog = filedialog
    root.withdraw()

    print("Select a folder for FIO Data:")
    #Request user to select the folder to use using TKInter
    try:
        test_directory = tkFileDialog.askdirectory()

    # If TKInter didn't work, ask for filepath manually
    except Exception as e:
        print(f"Error opening file: {e}")
        test_directory = input("Failed to open folder dialog, the enter the folder path for FIO to access\n")

    #If no filepath was entered, raise an exception
    if test_directory == "":
        raise Exception("No directory selected")

    print("Selected : " + test_directory)

    # FIO needs colons escaped when passing "directory" or "filename" look at FIO documentation online for more info.
    test_directory = test_directory.replace(":", "\:")  # escape colons from tkinter input.

    #Optional Hardcode for the path - uncomment this, comment in the line above
    #test_directory="D:/Temp/


    # Changes IO engine depending on OS
    if os.name == "nt":  # Windows
        engine = "windowsaio"
    elif os.name == "posix":  # Linux
        engine = "libaio"
    else:  # If not windows or linux, raise an error
        raise OSError(f"Unsupported operating system. Please try again on Windows or POSIX")

    # Create the path for the temp file
    test_file = os.path.join(test_directory, "temp_fio_test.bin")

    fio_args = {
        "name": "gen5_load_test",
        "ioengine": engine,
        "direct": "1",
        "rw": "randread",
        "bs": "16k",
        "size": "2G",
        "runtime": f"{fio_length}",
        "time_based": None,
        "group_reporting": None,
        "output-format": "json",
        "rate" : f"{target_rate}M" #Target rate is in MB/s
    }

    #Build the FIO command
    command = ["fio"]
    #For each line in the argument, add the key, and if applicable the value to the command
    for key, value in fio_args.items():
        if value is None: #e.g. time_based
            command.append(f"--{key}")
        else:#Has some value, include in command
            command.append(f"--{key}={value}")

    #Execute the command
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"FIO failed with exit code {e.returncode}")


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
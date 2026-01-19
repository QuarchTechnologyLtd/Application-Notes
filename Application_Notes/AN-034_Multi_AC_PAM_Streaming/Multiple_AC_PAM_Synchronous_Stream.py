"""AN-034
This Application Note uses 2 AC Power Analysis Modules to stream synchronously, with the user choosing to stream
over QIS or over QPS. Either option will export a CSV, which is then merged, and opened in QPS.

The application this has been designed for is for a high power environment, where a single AC PAM does not have the
capability to measure the full load, so 2 AC PAMs are used. Both PAM data streams can be viewed side by side.
Through testing the de-sync time ranges from 1.125ms to 20ms (Less than 1 cycle at 50Hz mains frequency). This will
vary with the system, and what programs are open on the machine.

To cut down latency between the stream starts, threading is used. Threading is a way of running multiple processes
concurrently. Before threading was implemented, there was a latency of between 60ms and 120ms, of 1 stream starting then
the next starting. A flag is used to start both processes. Through testing, this has been seen at sub 2ms latency.

This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Threading
-Combining multiple CSVs into a single CSV, with a shared column
-Manually importing CSVs into QPS for comparison.

########### VERSION HISTORY ###########
13/01/2026 - Andrew Steedman - Created
16/01/2026 - Stuart Boon - Multi-threading

########### REQUIREMENTS ##############

1 - Python (3.x recommended)
    https://www.python.org/downloads/
2 - Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3 - tkinter (Used for GUI)
    https://docs.python.org/3/library/tkinter.html#
4 - Control PC, with firewall permissions and admin rights

########### INSTRUCTIONS ##############

1 - Connect AC PAMs to the same LAN as control PC
2 - Connect AC PAMs to power
3 - Change the global variables: PAM_1_ADDRESS, PAM_2_ADDRESS,FILE_NAME_COMBINED, STREAM_LENGTH
4 - Run the script

#TODO
Quarchpy QPS API change - enable the scripting of multiple instances, with a separate QIS backend
Automate the CSV imports into QPS - Manual import works as expected
"""
import time
import pandas as pd #CSV manipulation
import psutil
import os
import threading #Used for synchronous processes


import multiprocessing
import ctypes
import subprocess
import tempfile
import numpy as np

import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

#The name of the file after the 2 pam streams have been combined
FILE_NAME_COMBINED = os.path.join(os.getcwd(),"CombinedPamData.csv")

#USER TO CHANGE - Constants, Should be static while program is running
# Hardcoded PAM Addresses
PAM_1_ADDRESS = "TCP:10.0.8.107"
PAM_2_ADDRESS = "TCP:10.0.8.59"

FILE_NAME_PAM_1 = os.path.join(os.getcwd(),"RawDataPam1.csv")
FILE_NAME_PAM_2 = os.path.join(os.getcwd(),"RawDataPam2.csv")

#Stream length in seconds - QIS call takes float parameter
STREAM_LENGTH = float(60)
#/USER TO CHANGE/

#Strips the TCP: from the Pam address - used for pinging the device to ensure its awake
ip_address_1 = PAM_1_ADDRESS.split(":")[1]
ip_address_2 = PAM_2_ADDRESS.split(":")[1]

C_CODE_WINDOWS = """
#include <windows.h>

void spin_until(long long target_ns) {
    // We use GetSystemTimePreciseAsFileTime to match Python's time.time_ns()
    // 134774 seconds offset is not needed if we just look at the raw trend.

    while (1) {
        FILETIME ft;
        GetSystemTimePreciseAsFileTime(&ft);
        unsigned __int64 now = (((unsigned __int64)ft.dwHighDateTime << 32) | ft.dwLowDateTime);

        // Windows returns 100-ns intervals. Convert to ns.
        // There is an offset between Windows FileTime and Unix Epoch, 
        // but since we call time.time_ns() in Python to set the target,
        // we will adjust the target in the worker function.
        if ((now * 100) >= target_ns) {
            break;
        }
    }
}
"""

C_CODE_POSIX = """
#include <time.h>

void spin_until(long long target_ns) {
    struct timespec ts;
    while (1) {
        clock_gettime(CLOCK_MONOTONIC, &ts);
        long long now_ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
        if (now_ns >= target_ns) {
            break;
        }
    }
}
"""


def main():
    if os.name == "nt": #Windows
        #Tells OS this python script is high priority
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)

        #Sets the code to be compiled as the windows variant
        C_CODE = C_CODE_WINDOWS

    elif os.name == "posix": #POSIX
        try:
            os.nice(-20) #Sets this script as highest priority
        except PermissionError:
            print("Warning: Run with sudo to enable high-priority timing.")
        C_CODE = C_CODE_POSIX

    #QPS is not currently working - remove option to use QPS
    connection_type = "QIS"

    #If QIS is not already running
    if not isQisRunning():
        #Start Local QIS Instance
        startLocalQis()

    #Connects to the localhost QIS instance
    QisInterface()

    #Compiles the C Script
    print("Compiling...")
    lib_path = compile_c_lib(C_CODE)

    #Pings the IP Addresses before starting the stream - Comment out if using USB
    ping_device(ip_address_1)
    ping_device(ip_address_2)

    if lib_path: #If the C_CODE has compiled correctly
        print("Compiled successfully, starting stream...")

        run_worker_func(lib_path, connection_type, FILE_NAME_PAM_1, FILE_NAME_PAM_2, STREAM_LENGTH)

        os.remove(lib_path)

    print("Stream completed\n")
    print("Combining CSV files...")

    #Merges the CSVs with a shared time column, adds prefix to other columns in 1_ and 2_
    csv_combiner("RawDataPam1.csv", "RawDataPam2.csv")

    print("\nStream completed successfully\n")

    #PLACEHOLDER
    print("Opening QPS and reconnecting to a PAM to view the traces\n...\n")

    #Opens QPS, ready for user to manually import CSV
    open_qps_to_view_csv()

    print("To open")
    print("File -> Import -> From CSV -> New Recording")
    print("Select the CSV named CombinedData.csv")
    print("PAM1 traces are prefixed with 1_, PAM2 traces are prefixed with 2_")

    return None

def compile_c_lib(C_CODE:str):
    """
    Compiles the C code to keep the CPU busy and ready to execute
    Args:
        C_CODE: The C Code to be compiled - different whether Windows or Linux

    Returns: so_file - The compiled C code

    """
    #If Windows, look for a .dll (dynamic link library) - else, look for a .so Shared Object file
    suffix = ".dll" if os.name == "Windows" else ".so"

    #Need to rename
    so_file = os.path.join(os.getcwd(), "timing_lib" + suffix)
    c_file = os.path.join(os.getcwd(), "timing_lib.c")

    with open(c_file, mode="w") as f:
        f.write(C_CODE)

    so_file = c_file.replace(".c", suffix)

    cmd = ["gcc", "-O3", "-shared", "-fPIC", "-o", so_file, c_file]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return so_file

    #Catches the potential exception
    except Exception as e:
        #If opening, writing and compiling the file hasn't worked
        print(f"Compilation Error: {e}")
        return None

def worker_function(target_ns,
                    so_file,
                    timestamp,
                    pam_address:str,
                    filename:str,
                    connection_type:str = "QIS",
                    stream_duration:float = STREAM_LENGTH):
    """
    This is the worker function. This is executed on different cores for different PAM devices
    Args:
        target_ns: The time the system aims to execute at
        so_file: The compiled C code
        timestamp: The shared timestamp
        pam_address: The address of the PAM to be connected to - in the format "TCP:1.1.1.1"
        filename: The file to write to
        connection_type: Default QIS, but can be overwritten to QPS
        stream_duration: Stream length - how long to stream for

    Returns None:

    """
    try:
        #Connects 1st pam device to the same QIS Instance
        pam = get_quarch_device(connectionTarget=pam_address, ConType=connection_type)
        #Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
        pam_power_device = quarchPPM(pam)
    except Exception as e:
        print(f"Could not connect to PAM: {e}")
        sys.stdout.flush()

    if os.name == "nt": #If windows correct for epoch differences
        # Windows FileTime epoch is different from Unix Epoch
        # Windows Epoch is 1601, Unix Epoch is 1970 - 11644473600
        # This is unix epoch (1970) since Windows epoch (1601), expressed in nanoseconds.
        target_ns = target_ns + (11644473600 * 1000000000)

    try:
        #Loads the compiled file
        lib = ctypes.CDLL(so_file)
        #Calls the spin_until function inside, keeps CPU busy and ready
        lib.spin_until(ctypes.c_int64(target_ns))

        #Starts stream
        pam_power_device.start_stream(file_name=filename, stream_duration=stream_duration)

        #Stores the time after the start_stream command is run successfully
        #Change for Linux
        timestamp.value = time.time_ns()

    #Catches potential exception
    except Exception as e:
        print(f"Worker function error: {e}")
        sys.stdout.flush()

def run_worker_func(
        so_file,
        connection_type:str = "QIS",
        filename_1:str = "RawDataPam1.csv",
        filename_2:str = "RawDataPam2.csv",
        stream_duration:float = STREAM_LENGTH):
    """
    The worker function to be called
    Args:
        so_file: The compiled C code
        connection_type: Default QIS, but can be overwritten to QPS
        filename_1: The file of the stream data for PAM 1
        filename_2: The file of the stream data for PAM 2
        stream_duration: Stream length

    Returns: The difference in start time between process 1 and process 2, in nanoseconds

    """
    #Returns a ctypes object allocated from shared memory - allows other processes
    result1 = multiprocessing.Value(ctypes.c_longlong, 0, lock=False)
    result2 = multiprocessing.Value(ctypes.c_longlong, 0, lock=False)

    #Time now in ns, plus 5 seconds in nanoseconds - Allows connection to form
    #Change for Linux
    target = time.time_ns() + int(5*1e9)

    #Creates Process objects
    process1 = multiprocessing.Process(target=worker_function, args=(target, so_file, result1, PAM_1_ADDRESS, filename_1, connection_type, stream_duration))
    process2 = multiprocessing.Process(target=worker_function, args=(target, so_file, result2, PAM_2_ADDRESS, filename_2, connection_type, stream_duration))

    #Starts the processes activity
    process1.start()
    process2.start()

    #Blocks the main script until both processes are done
    process1.join()
    process2.join()

    #Prints and returns the difference in start times between process 1 and process 2 in nanoseconds
    print(abs(result1.value - result2.value))
    return abs(result1.value - result2.value)

def ping_device(ip_address:str):
    """
    Pings the specified IP address, to ensure the device is awake and ready to connect
    1 ping only
    Args:
        ip_address: The IP address to ping

    Returns None:
    """
    #Command is in the form
    #ping -n 1 1.1.1.1 on windows
    #ping -c 1 1.1.1.1 on all other os's
    try:
        param = "-n" if os.name == "nt" else "-c"
        command = ["ping", param, "1", ip_address]
        subprocess.run(command, stdout=subprocess.PIPE)
    except Exception as e:
        print(f"IP Ping error: {e}")

def csv_combiner(csv_file_1:str = FILE_NAME_PAM_1, csv_file_2:str = FILE_NAME_PAM_2):
    """
    Merges the PAM Stream CSVs, keeps shared time column, renames and adds 1_ and 2_ to the column headers
    Args:
        csv_file_1: CSV file 1
        csv_file_2: CSV file 2

    Returns None:
    """

    #Uses pandas, and creates a dataframe of each csv
    csv1 = pd.read_csv(csv_file_1)
    csv2 = pd.read_csv(csv_file_2)

    #Column name of the time column - This will be the same in both CSVs, and should not be changed
    #Time uS may change according to sample time
    shared_time_column = "Time uS"

    #Adds the 1_ or 2_ prefix to each individual data frame, except the time column
    csv1_prefix = csv1.add_prefix("1_").rename(columns={"1_" + shared_time_column: shared_time_column})
    csv2_prefix = csv2.add_prefix("2_").rename(columns={"2_" + shared_time_column: shared_time_column})

    #Merge the two data frames - format being
    #time, 1_B,1_C,..., 1_XXX, 2_B,2_C,...,2_XXX
    merged_data = pd.merge(csv1_prefix, csv2_prefix, on=shared_time_column, how="outer")

    #Changes the dataframe to CSV
    merged_data.to_csv(FILE_NAME_COMBINED, index=False)

    #Prints the filename
    print("CSVs have been combined - filename = " + FILE_NAME_COMBINED)


def open_qps_to_view_csv():
    """
    Opens QPS and reconnects to PAM 1
    Used for user to view the CSVs as QPS Traces - currently semi-automated process

    Returns: None

    """
    #Starts Local QPS instance
    startLocalQps()

    #Connects to localhost QPS Instance
    qpsInterface()

    #Connect PAM1 (again), explicitly QPS
    pam_2_device = get_quarch_device(connectionTarget=PAM_2_ADDRESS, ConType="QPS")

    #Upgrade PAM1 to a QPS device
    my_qps_pam = quarchQPS(pam_2_device)

    #Opens connection to PAM - Required to convert a CSV to QPS
    my_qps_pam.open_connection()


if __name__ == "__main__":
    main()


"""AN-034
This Application Note uses 2 AC Power Analysis Modules to stream synchronously, with the user choosing to stream
over QIS or over QPS. Either option will export a CSV, which is then merged, and opened in QPS.

The application this has been designed for is for a high power environment, where a single AC PAM does not have the
capability to measure the full load, so 2 AC PAMs are used. Both PAM data streams can be viewed side by side.

To reduce latency from one stream starting to the next stream starting, this script uses a compiled C file to spin
up 2 CPU cores, and keep them busy, until the start_stream command is called. This requires the use of a compiler -
GCC recommended. The two streams from both PAMs should start relatively synchronously.

In testing, the desync was typically less than 5ms, with most being less than 1ms between 1 stream starting and the
next stream starting. This is likely related to network latency.

This AN-034 uses the quarchpy python package and demonstrates
-Streaming from multiple instruments at the same time
-Using multiple cores in parallel
-Combining multiple CSVs into a single CSV, with a shared column
-Manually importing CSVs into QPS for comparison.

########### VERSION HISTORY ###########
13/01/2026 - Andrew Steedman - Created
16/01/2026 - Stuart Boon - Multi-threading
20/01/2026 - Andrew Steedman - Working with QIS, and semi-automated

########### REQUIREMENTS ##############

1 - Python (3.x recommended)
    https://www.python.org/downloads/
2 - Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3 - GCC (GNU Compiler Collection) - See README.md
4 - Python packages - psutil, numpy, pandas
5- A multicore processor (2 minimum)

########### INSTRUCTIONS ##############

1 - Connect AC PAMs to the same LAN as control PC
2 - Connect AC PAMs to power
3 - Change the global variables: PAM_1_ADDRESS, PAM_2_ADDRESS, STREAM_LENGTH
4 - Run the script with admin permissions
"""
#To add package
import psutil #OS Priority Setting
import numpy as np
import pandas as pd #CSV manipulation

#To add package
import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

#Included in default installation
import time
import os
import shutil #Check GCC
import multiprocessing #Multicore processing
import ctypes #Allows calling functions into the compiled C code
import subprocess #Shell commands


#USER TO CHANGE - Constants, Should be static while program is running
# Hardcoded PAM Addresses
PAM_1_ADDRESS = "TCP:10.0.8.107"
PAM_2_ADDRESS = "TCP:10.0.8.59"

#Stream length in seconds - QIS call takes float parameter
STREAM_LENGTH = float(60)
#/USER TO CHANGE/

#All in Current Working Directory
#Filename of the CSV output from PAM1
FILE_NAME_PAM_1 = "RawDataPam1.csv"
#Absolute path of the CSV OUTPUT from PAM1
PATH_PAM_1 = os.path.join(os.getcwd(),FILE_NAME_PAM_1)

#Filename of the CSV output from PAM2
FILE_NAME_PAM_2 = "RawDataPam2.csv"
#Absolute path of the CSV output from PAM2
PATH_PAM_2 = os.path.join(os.getcwd(),FILE_NAME_PAM_2)

#The name of the file after the 2 pam streams have been combined
FILE_NAME_COMBINED = os.path.join(os.getcwd(),"CombinedPamData.csv")

#Checks if connecting over TCP. If so, create a variable with the IP address
if PAM_1_ADDRESS.split(":")[0] == "TCP":
    ip_address_1 = PAM_1_ADDRESS.split(":")[1]
if PAM_2_ADDRESS.split(":")[0] == "TCP":
    ip_address_2 = PAM_2_ADDRESS.split(":")[1]

#C Code is different for Windows or POSIX
C_CODE_WINDOWS = """
#include <windows.h>

void spin_until(long long target_ns) {
    // We use GetSystemTimePreciseAsFileTime to match Python's time.time_ns()

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
    //Data structure used to represent time with nanosecond precision
    //Has a seconds component, and nanoseconds component
    struct timespec ts;
    
    //Highest precision clock
    while (1) {
        //Used for unix absolute time
        clock_gettime(CLOCK_MONOTONIC, &ts);
        
        //Convert timespec to time now_ns
        //Convert the timespec seconds to nanoseconds, and add the timespec nanosecond
        long long now_ns = (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
        
        //If current time is the same as target time, break
        if (now_ns >= target_ns) {
            break;
        }
    }
}
"""


def main():
    #Checks if compiler is installed, and provides installation instructions if not
    gcc_check()

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

    else: #If not Windows or Linux, raise an error
        print("OS not currently supported. Please use a Windows or POSIX system")
        raise OSError("Unsupported operating system")

    #Currently QIS only. Next Quarchpy release will enable dual QPS streams
    connection_type = "QIS"
    #TODO - Enable option for synchronous stream over QPS

    #If QIS is not already running
    if not isQisRunning():
        #Start Local QIS Instance
        startLocalQis()

    #Connects to the localhost QIS instance
    QisInterface()

    #Compiles the C Script
    print("Compiling the C code...")
    lib_path = compile_c_lib(C_CODE)

    #Pings the IP Addresses before starting the stream - Comment out if using USB
    ping_device(ip_address_1)
    ping_device(ip_address_2)

    if lib_path: #If the C_CODE has compiled correctly
        print("Compiled successfully, starting stream in 5 seconds...")

        coordinate_multiproc_trigger(lib_path, connection_type, FILE_NAME_PAM_1, FILE_NAME_PAM_2, STREAM_LENGTH)

        os.remove(lib_path)

    print("Stream completed\n")
    print("Combining CSV files...")

    #Merges the CSVs with a shared time column, adds prefix to other columns in 1_ and 2_
    csv_combiner()

    #PLACEHOLDER
    print("Opening QPS and reconnecting to a PAM to view the traces\n...\n")

    #Opens QPS, ready for user to manually import CSV
    open_qps_to_view_csv()

    print("To open")
    print("File -> Import -> From CSV -> New Recording")
    print("Select the CSV named CombinedData.csv")
    print("PAM1 traces are prefixed with 1_, PAM2 traces are prefixed with 2_")

    return None

def gcc_check():
    """
    Checks if the GNU Compiler Collection is installed
    Returns None:
    Raises: ModuleNotFoundError if not installed
    """
    gcc_search_cmd = "where" if os.name == "nt" else "which"
    try:
        check = subprocess.run([gcc_search_cmd, "gcc"], capture_output=True, text=True)

        if check.returncode != 0: #Not Found
            print("******** GCC CHECK FAILED *********\n")
            print("Error: GNU Compiler Collection not found\n")

            if os.name == "nt": #Changes instructions based on OS
                print("Please install MinGW-w64")
                print("Download the MSYS2 Installer - https://www.msys2.org/")
                print("Open the MSYS2 Terminal and run the command")
                print("\npacman -S mingw-64-86_64-gcc\n")
                print(r"Then add C:\msys64\mingw64\bin to the PATH")
                print("Once installed and added, please re-run")
            else:
                print("Please install MinGW-w64")
                print("On ubuntu please run the command\n")
                print(r"sudo apt install build-essentia")
                print("\nOn fedora please run the command\n")
                print(r"sudo dnf install gcc glibc-devel")
                print("\nOnce installed and added, please re-run")
    except:
        raise ModuleNotFoundError

def compile_c_lib(C_CODE:str):
    """
    Compiles the C code to keep the CPU busy and ready to execute
    Args:
        C_CODE: The C Code to be compiled - different whether Windows or Linux

    Returns: so_file - The compiled C code

    """
    #If Windows, look for a .dll (dynamic link library) - else, look for a .so Shared Object file
    suffix = ".dll" if os.name == "nt" else ".so"

    #Creates the C file in the current working directory
    c_file = os.path.join(os.getcwd(), "spin_core.c")

    #Opens the c_file and writes the C_CODE to it
    with open(c_file, mode="w") as f:
        f.write(C_CODE)

    #Replaces the .c with .so or .dll
    so_file = c_file.replace(".c", suffix)

    #gcc -O3 -shared -fPIC -o spin_core.dll spin_core.c
    command = ["gcc", "-O3", "-shared", "-fPIC", "-o", so_file, c_file]

    try:
        #Attempts to compile, and records the output
        subprocess.run(command, check=True, capture_output=True, text=True)
        return so_file

    #Catches the potential exception
    except Exception as e:
        print(f"Compilation Error: {e}")
        return None

def sync_and_trigger_stream(target_ns,
                            so_file,
                            pam_address:str,
                            filename:str,
                            connection_type:str = "QIS",
                            stream_duration:float = STREAM_LENGTH):
    """
    This is a worker function. This is executed on different cores for different PAM devices
    Args:
        target_ns: The time the system aims to execute at
        so_file: The compiled C code
        pam_address: The address of the PAM to be connected to - in the format "TCP:1.1.1.1"
        filename: The file to write to
        connection_type: Default QIS, but can be overwritten to QPS
        stream_duration: Stream length - how long to stream for

    Returns None:
    """

    try:
        #Connects 1st pam device to the same QIS Instance - timeout of 20s
        pam = get_quarch_device(connectionTarget=pam_address, ConType=connection_type, timeout=str(20))

        #Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
        pam_power_device = quarchPPM(pam)

    except Exception as e:
        print(f"Could not connect to PAM: {e}")
        sys.stdout.flush() #Forces output

    try:
        #Loads the compiled file
        lib = ctypes.CDLL(so_file)

        #Calls the spin_until function inside, keeps CPU busy and ready
        lib.spin_until(ctypes.c_int64(target_ns))

        #Starts stream
        pam_power_device.start_stream(file_name=filename, stream_duration=stream_duration)

    #Catches potential exception
    except Exception as e:
        print(f"Error triggering stream: {e}")
        sys.stdout.flush() #Forces output

def coordinate_multiproc_trigger(
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

    Returns None:

    """
    if os.name == "nt": #If windows correct for epoch differences
        # Windows FileTime epoch is different from Unix Epoch
        # Windows Epoch is 1601, Unix Epoch is 1970 - The difference is 11 644 473 600 seconds
        # This is unix epoch (1970) since Windows epoch (1601), expressed in nanoseconds.
        epoch_correction_ns = (11644473600 * 1000000000)

        #Add a 5 seconds delay
        target = time.time_ns() + int(5*1e9) + epoch_correction_ns

    else:
        #CLOCK_MONOTONIC is the absolute elapsed time since system boot
        target = time.clock_gettime_ns(time.CLOCK_MONOTONIC) + int(5*1e9)

    #Creates Process objects
    process1 = multiprocessing.Process(target=sync_and_trigger_stream, args=(target, so_file, PAM_1_ADDRESS, filename_1, connection_type, stream_duration))
    process2 = multiprocessing.Process(target=sync_and_trigger_stream, args=(target, so_file, PAM_2_ADDRESS, filename_2, connection_type, stream_duration))

    #Starts the processes activity
    process1.start()
    process2.start()

    #Shows progress bar for stream length with an extra 5 seconds
    visual_sleep((STREAM_LENGTH+5), title="Stream in progress")

    #Blocks the main script until both processes are done
    process1.join()
    process2.join()

def ping_device(ip_address:str):
    """
    Pings the specified IP address, to ensure the device is awake and ready to connect
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
        #Execute the command, capture the output
        subprocess.run(command, capture_output=True, text=True)

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
    #TODO - Fully automate with next QPS release

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


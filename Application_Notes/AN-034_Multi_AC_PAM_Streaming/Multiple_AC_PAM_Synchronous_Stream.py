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
import platform


#Used for attempting automated CSV import
from tkinter import Tk #Used as a GUI
from tkinter.filedialog import askopenfilename #Used to open the CSV to reopen

import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

FILE_NAME_COMBINED = "CombinedPamData.csv"

#USER TO CHANGE - Constants, Should be static while program is running
# Hardcoded PAM Addresses
PAM_1_ADDRESS = "TCP:10.0.9.146"
PAM_2_ADDRESS = "TCP:10.0.9.204"

FILE_NAME_PAM_1 = "RawDataPam1.csv"
FILE_NAME_PAM_2 = "RawDataPam2.csv"

#Stream length in seconds - QIS call takes float parameter
STREAM_LENGTH = float(60)
#/USER TO CHANGE/

stream_start_time_unix = None

trigger = [False]

C_CODE = """
//Includes windows.header to access WinAPI
#include <windows.h>

//Returns nothing, spins up CPU Until ready to go
//long long target_ns - 64 bit
void spin_until(long long target_ns) {
    //FILETIME contains a 64 bit value representing the number of 100 nanosecond intervals since Windows Epoch
    //Each 100ns interval is known as a Tick. Windows Epoch is 01
    FILETIME ft;
    unsigned __int64 current_ns;
  
    while (1) {
          //Highest precision clock on windows
          //Retrieves current sys date and time in UTC - populates the FILETIME ft variable
          GetSystemTimePreciseAsFileTime(&ft);
          
          //Convert FILETIME to total nanoseconds
          //FILETIME is 100ns intervals (ticks) since 1 Jan 1601
          //Unsigned 64 bit integer - Combines the two separate halves of FILETIME ft
          current_ns = (((unsigned __int64)ft.dwHighDateTime << 32) | ft.dwLowDateTime);
          
          //Convert to nanoseconds (Approximate ot epoch-like scale for comparison)
          //Only care about relative difference
          //Python's time.time_ns() and Windows precise time both trend together
          //However, check the condition for comparison
          
          //Uses Windows high-performance counter (QueryPerformanceCounter) - standard for sub-microsecond timing on Windows
          //LARGE_INTEGER is a 64bit signed integer value - It is a union
          LARGE_INTEGER count, freq; //Initialise variables
          QueryPerformanceFrequency(&freq);
          QueryPerformanceCounter(&count);
          
          //We calculate target based on QPC to avoid epoch conversion
    }
}   
"""



def main():
    #Tells OS this python script is high priority
    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)

    #QPS is not currently working - remove option to use QPS
    connection_type = "QIS"

    #TO INDENT
    #If QIS is not already running
    if not isQisRunning():
        #Start Local QIS Instance
        startLocalQis()

    #Connects to the localhost QIS instance
    QisInterface()

    #Connects 1st pam device to the same QIS Instance
    pam_1_device = get_quarch_device(connectionTarget=PAM_1_ADDRESS, ConType=connection_type)
    #Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
    pam_1_power_device = quarchPPM(pam_1_device)

    #Connect the 2nd PAM device to same QIS Instance
    pam_2_device = get_quarch_device(connectionTarget=PAM_2_ADDRESS, ConType=connection_type)
    # Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
    pam_2_power_device = quarchPPM(pam_2_device)

    #Prints the identity of both
    print("PAM 1 is:")
    print(pam_1_device.send_command("*idn?"))

    print("\nPAM 2 is:")
    print(pam_2_device.send_command("*idn?"))

    print("Starting Stream")

    lib_path = compile_c_lib()
    if lib_path:
        print("Compiled successfully")
        run_test(lib_path, pam_1_power_device, FILE_NAME_PAM_1, pam_2_power_device, FILE_NAME_PAM_2, STREAM_LENGTH)

        #results = [run_test(lib_path, pam_1_power_device, FILE_NAME_PAM_1, pam_2_power_device,FILE_NAME_PAM_2, STREAM_LENGTH) for _ in range(10)]
        #print(f"Test Avg Delta: {np.mean(results):,.0f} ns")
        os.remove(lib_path)

    print("Stream completed\n")
    print("Combining CSV files...")

    #Merges the CSVs with a shared time column, adds prefix to other columns in 1_ and 2_
    csv_combiner("RawDataPam1.csv", "RawDataPam2.csv")

    #Closes connections
    pam_1_power_device.close_connection()
    pam_2_power_device.close_connection()

    print("\nStream completed successfully\n")

    #PLACEHOLDER
    print("Opening QPS and reconnecting to a PAM to view the traces\n...\n")

    #Opens QPS, ready for user to manually import CSV
    #open_qps_to_view_csv()

    print("To open")
    print("File -> Import -> From CSV -> New Recording")
    print("Select the CSV named CombinedData.csv")
    print("PAM1 traces are prefixed with 1_, PAM2 traces are prefixed with 2_")

    return None

def compile_c_lib():
    #If Windows, look for a .dll (dynamic link library) - else, look for a .so Shared Object file
    suffix = ".dll" if platform.system() == "Windows" else ".so"

    try: #Might fail
        #Attempts to open temporary file in write mode, will not delete after being opened
        #C file - C sourcecode
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as f:
            #Writes the global variable C_CODE into the file
            f.write(C_CODE)
            #Casts the C_file name to a variable called c_file
            c_file = f.name

        #Compiled file (so_file) is same, but .dll or .so rather than .c
        so_file = c_file.replace(".c", suffix)

        #Compiles - Uses the GNU Compiler Collection
        #Check is true - if process exits with a non-zero exit code, CalledProcessError will be raised
        #gcc -O3 -shared -o so_file.dll c_file.c   Or  gcc -O3 -shared -o so_file.so c_file.c
        subprocess.run(args=["gcc", "-O3", "-shared", "-o", so_file, c_file], check=True)

        #Returns the compiled file
        return so_file

    #Catches the potential exception
    except Exception as e:
        #If opening, writing and compiling the file hasn't worked
        print(f"Compilation Error: {e}")
        return None

def test_worker(target_ns, so_file, shared_val, pam, filename, duration):
    #Windows FileTime epoch is different from Unix Epoch
    #Windows Epoch is 1601, Unix Epoch is 1970 - 11644473600
    #This is unix epoch (1970) since Windows epoch (1601), expressed in nanoseconds.
    DELTA_UNIX_WIN_EPOCH_NS = 11644473600000000000

    # Adjust target to Windows ticks
    win_target_ns = target_ns + DELTA_UNIX_WIN_EPOCH_NS

    try:#Might fail
        #Ctypes is a foreign function library - allows calling functions in DLLs
        #Loads the compiled file
        lib = ctypes.CDLL(so_file)
        #Calls the spin_until function inside, keeps CPU busy and ready
        lib.spin_until(ctypes.c_int64(win_target_ns))

        shared_val.value = time.time_ns()

        start_pam_stream(pam, filename, duration)

    except Exception as e:
        print(f"Worker error: {e}")

def run_test(so_file, pam_1, filename_1, pam_2, filename_2, duration):
    #Returns a ctypes object allocated from shared memory - allows other processes
    result1 = multiprocessing.Value(ctypes.c_longlong, 0, lock=False)
    result2 = multiprocessing.Value(ctypes.c_longlong, 0, lock=False)

    #Time now in ns, plus 0.5 seconds in nanoseconds
    target = time.time_ns() + int(0.5*1e9)

    process1 = multiprocessing.Process(target=test_worker, args=(target, so_file, result1, pam_1, filename_1, duration))
    process2 = multiprocessing.Process(target=test_worker, args=(target, so_file, result2, pam_2, filename_2, duration))

    process1.start()
    process2.start()
    process1.join()
    process2.join()

    return abs(result1.value - result2.value)

def start_pam_stream(pam, filename, duration):
    """
    This is used for threading - split into a function to configure
    Starts a data stream from the PAM

    Args:
        pam: A QuarchPPM object - The PAM connected
        filename: The CSV to record to
        duration: The duration of the recording

    Returns: None
    """
    #Sets the recording flag as waiting
    stream_func = pam.start_stream

    #Polling loop
    while stream_start_time_unix == 0:
        time.sleep(0.05)

    stream_func(file_name=filename, stream_duration=duration)

def csv_combiner(csv_file_1, csv_file_2):
    """
    Merges CSVs exported, keeps shared time column, renames and adds 1_ and 2_ to the column headers
    Args:
        csv_file_1: The CSV export from PAM 1
        csv_file_2: The CSv export from PAM 2

    Returns None:
    """

    #Uses pandas - a data analysis and manipulation tool
    #Creates a dataframe of each csv
    csv1 = pd.read_csv(csv_file_1)
    csv2 = pd.read_csv(csv_file_2)

    #Column name of the time column - This will be the same in both CSVs, and should not be changed
    #Time uS may change according to sample time
    shared_time_column = "Time uS"

    #Adds the 1_ or 2_ prefix to each individual data frame, except the time column
    #Unresolved attribute is not an issue - runs fine
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
    myLocalInterface = qpsInterface()

    #Connect PAM1 (again), explicitly QPS
    pam_2_device = get_quarch_device(connectionTarget=PAM_2_ADDRESS, ConType="QPS")

    #Upgrade PAM1 to a QPS device
    my_qps_pam = quarchQPS(pam_2_device)

    #Opens connection to PAM
    my_qps_pam.open_connection()

    #The automated section
    """
    print("Please open the CSV to be displayed")

    #Tk is a python GUI package
    #Creates object for gui
    root = Tk()
    #Removes main gui window
    root.withdraw()
    #Forces the window to the top
    root.attributes('-topmost', True)

    #Get the filepath from file explorer, csv only
    csv_path = askopenfilename(title="Open the combined CSV", filetypes=(("CSV files", "*.csv"),))

    #Prints the CSV full file path
    print("CSV path = " + csv_path)

    #Creates QPS command as string
    command = "$stream import file=\"" + csv_path + "\""

    #Sends command to the QPS Interface, and stores result
    cmd_result = myLocalInterface.sendCmdVerbose(command)

    print("Importing of CSV Values: " + cmd_result)
    """


if __name__ == "__main__":
    main()


#TO UNCOMMENT
"""
#User selectable whether connection is done via QIS or via QPS
    connection_list = ["QIS", "QPS"]
#String, with the value either QIS or QPS
connection_type = listSelection(title="Connection: QIS or QPS", selectionList=connection_list, nice=True)
"""
 #/TO UNCOMMENT/

# TO UNCOMMENT
"""
#Use single instance of QIS
if connection_type == "QIS":
"""
# /TO UNCOMMENT/

# TO UNCOMMENT
"""
#Quarchpy API is likely to change

#Else - connection type is QPS, open 2 instances of QPS with a separate QIS backend
else:
    #First Instance - default ports, but left for clarity
    startLocalQis()
    my_qps_1 = startLocalQps()

    #Creates and returns a quarchDevice instance
    pam_1_device = get_quarch_device(connectionTarget=pam_1_address, ConType=connection_type)
    print(pam_1_device.send_command("*idn?"))

    pam_1_device.open_connection()

    #Second instance - Ports are incremented by 1
    startLocalQis(args=['-port=9723','restport=9781'])
    my_qps_2 = startLocalQps(args=['-port=9823','-qisport=9723','-qisrestport=9781'])

    #Creates and returns a quarchDevice instance
    pam_2_device = get_quarch_device(connectionTarget=pam_2_address, ConType=connection_type)
    print(pam_2_device.send_command("*idn?"))

    pam_2_device.open_connection()
"""
# /TO UNCOMMENT/
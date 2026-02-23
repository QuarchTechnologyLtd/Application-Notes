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

import SyncUtils
#To add package
import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.qis import *
from quarchpy.qps import *
from quarchpy.device import *
from quarchpy.user_interface import *
from quarchpy.connection_specific import *

#Included in default installation
import time
from datetime import datetime
import os
import shutil #Check GCC
import multiprocessing #Multicore processing
import ctypes #Allows calling functions into the compiled C code
import subprocess #Shell commands
from abc import ABC, abstractmethod


#USER TO CHANGE - Constants, Should be static while program is running
# Hardcoded PAM Addresses
PAM_1_ADDRESS = "TCP:10.0.9.226"
PAM_2_ADDRESS = "USB:QTL2312-01-035"

#Stream length in seconds - QIS call takes float parameter
STREAM_LENGTH = float(20)

#The rate at which to resample the stream - DC PAMs minimum is 4us, AC PAMs is 250us
STREAM_RESAMPLE_RATE = "1ms"

#Optional Hardcode - Change if you want to speed up time in between runs
HARDCODED_HARDWARE_TRIGGER=None #Valid answers are "Yes" or "No"
HARDCODED_CONNECTION_TYPE=None #Valid answers are "QIS" or "QPS"
HARDCODED_SPIN_LANGUAGE = None #Valid answers are "C" or "Python"
#/USER TO CHANGE/

#All in Current Working Directory
#Filename of the CSV output from PAM1
FILE_NAME_PAM_1 = "RawDataPam1.csv"

#Filename of the CSV output from PAM2
FILE_NAME_PAM_2 = "RawDataPam2.csv"

#The name of the file after the 2 pam streams have been combined
FILE_NAME_COMBINED = os.path.join(os.getcwd(),"CombinedPamData.csv")

#Checks if connecting over TCP. If so, create a variable with the IP address
if PAM_1_ADDRESS.split(":")[0] == "TCP":
    ip_address_1 = PAM_1_ADDRESS.split(":")[1]
if PAM_2_ADDRESS.split(":")[0] == "TCP":
    ip_address_2 = PAM_2_ADDRESS.split(":")[1]

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    #logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    print("*****************************************")
    print("*****************************************\n")
    print("AN-034 - Multiple PAM Synchronous Stream")
    print("Connect the devices over IP on the same network")
    print("\n*****************************************")
    print("*****************************************")

    #Requires features added in 2.2.17
    requiredQuarchpyVersion("2.2.17")

    #e.g. Standard DC PAMs (QTL2312)
    #Checks if optional hardcode is set
    if HARDCODED_CONNECTION_TYPE is not None:
        #if it is, assign local variable to global constant
        hardware_trigger = HARDCODED_HARDWARE_TRIGGER
    else: #Not hardcoded, so takes user input
        print("Are you using PAMs connected by a triggering cable?")
        hardware_trigger = showYesNoDialog(title="Triggering cable?", message="Yes for triggering cable, no for software trigger")

    if hardware_trigger == "Yes": #Using triggering cable

        #Checks if optional hardcode is set
        if HARDCODED_CONNECTION_TYPE is not None:
            # if it is, assign local variable to global constant
            connection_type = HARDCODED_CONNECTION_TYPE
        else:#Not hardcoded, so takes user input
            optionList = "QIS,QPS"
            connection_type = user_interface.listSelection(title="QIS or QPS", message="Select QIS or QPS",selectionList=optionList, nice=True)

        #If using QIS, call the setup function - response is different based on QIS or QPS
        if connection_type == "QIS":
            pam1, pam2, qis = launch_and_run(connection_type)

        else: #QPS
            pam1, pam2, qps1, qps2 = launch_and_run(connection_type)

        #Gets the serial number in the format XXXX-XX-XXX
        pam_1_name = "QTL" + pam1.sendCommand("*enclosure?")
        pam_2_name = "QTL" + pam2.sendCommand("*enclosure?")

        # Upgrades PAM to quarchPPM class
        pam_1_power_device = quarchPPM(pam1)
        pam_2_power_device = quarchPPM(pam2)

        #Resamples the PAMs so they are sampling at the same rate
        pam_1_power_device.send_command(f"stream mode resample {STREAM_RESAMPLE_RATE}")
        pam_2_power_device.send_command(f"stream mode resample {STREAM_RESAMPLE_RATE}")

        #Gives instructions of how to connect the PAM triggers
        print(f"Connect PAM 1 {pam_1_name} trigger out, to PAM 2 {pam_2_name} trigger in\n")
        showDialog(title="Select yes, when setup", message=f"Is it setup in this way?")

        print("\nConfiguring Trigger...\n")

        #Configure recording trigger on PAM2
        pam_2_power_device.send_command("RECord:RUN")
        pam_2_power_device.send_command("RECord:TRIGger:MODE EXTernal")

        #Gives time for it to be setup
        time.sleep(1)

        #Configure trigger out on pam 1
        pam_1_power_device.send_command("TRIGger:OUT:MODE RECORD")

        #Setups stream on PAM2, with the target CSV - waits on trigger
        pam_2_power_device.start_stream("RawDataPam2.csv")

        # Gives time for it to be setup
        time.sleep(1)

        print("Streaming...")

        #Starts stream on both devices
        pam_1_power_device.start_stream("RawDataPam1.csv", stream_duration=STREAM_LENGTH)

        #Waits stream_length
        time.sleep(STREAM_LENGTH)

        #Stop PAM2 after Stream Length - trigger only syncs the start
        pam_2_power_device.send_command("RECord:STOP")

        time.sleep(2)
        #Closes the connection 2 seconds after stream ended
        pam_2_power_device.close_connection()

    else: #Using software trigger (e.g. AC PAMs - both 3 phase and IEC PAMs)
        # Checks if optional hardcode is set
        if HARDCODED_CONNECTION_TYPE is not None:
            # if it is, assign local variable to global constant
            connection_type = HARDCODED_CONNECTION_TYPE
        else:#Not hardcoded, so takes user input
            optionList = "QIS,QPS"
            connection_type = user_interface.listSelection(title="QIS or QPS", message="Select QIS or QPS",selectionList=optionList, nice=True)

        if HARDCODED_SPIN_LANGUAGE is not None:
            # Checks if optional hardcode is set
            spin_language = HARDCODED_SPIN_LANGUAGE
        else:# if it is, assign local variable to global constant
            optionList = "C,Python"
            spin_language = user_interface.listSelection(title="Do you want to use a C backend?", message="Select C or Python", selectionList=optionList, nice=True)

        #Similar to switch case in other languages - reduces indents and easier to read
        match (connection_type, os.name, spin_language):
            case ("QIS", "nt", "C"): #QIS, Windows, C
                syncStreamObj = CWindows()
                syncStreamObj.compiler_check() #Checks compiler is present

            case ("QIS", "posix", "C"): #QIS, POSIX, C
                syncStreamObj = CPosix()
                syncStreamObj.compiler_check() #Checks compiler is present

            case ("QIS", "nt", "Python"): #QIS, Windows, Python
                syncStreamObj = PyWindows()

            case ("QIS", "posix", "Python"): #QIS, POSIX, Python
                syncStreamObj = PyPosix()

            case ("QPS", "nt", "C"): #QPS, Windows, C
                syncStreamObj = CWindows()
                syncStreamObj.compiler_check()#Checks compiler is present

            case ("QPS", "posix", "C"): #QPS, POSIX, C
                syncStreamObj = CPosix()
                syncStreamObj.compiler_check()

            case ("QPS", "nt", "Python"): #QPS, Windows, Python
                syncStreamObj = PyWindows()

            case ("QPS", "posix", "Python"):
                syncStreamObj = PyPosix()

            case _: #Catchall - OS is the only one that isn't binary - i.e. qis or qps, c or python
                print("OS not currently supported. Please use a Windows or POSIX system")
                raise OSError("Unsupported operating system")

        syncStreamObj.stream(connection_type)

    print("Stream completed\n")
    print("Combining CSV files...")

    #Merges the CSVs with a shared time column, adds prefix to other columns in 1_ and 2_
    combined_csv = SyncUtils.csv_combiner(FILE_NAME_PAM_1, FILE_NAME_PAM_2)

    #PLACEHOLDER
    print("Opening QPS and reconnecting to a PAM to view the traces\n...\n")

    #Opens QPS, ready for user to manually import CSV
    if connection_type == "QPS":
        #Passes in the already open instance of QPS used for PAM 1
        view_csv_in_qps(qps1, combined_csv)
        #Close the 2nd QPS instance
        closeQps(port=9823)

    else: #If QIS was used, open a QPS instance
        qps_instance = start_qps_and_connect()
        #Opens the CSV
        view_csv_in_qps(qps_instance, combined_csv)

    print("PAM1 traces are prefixed with 1_, PAM2 traces are prefixed with 2_")
    print("If running again, rename the QPS recording, and CSV")

    sys.exit(0)

class UsingC(ABC):
    def __init__(self):
        self.so_file = None

    @abstractmethod
    def compiler_check(self):
        pass

    def stream(self, connection_type):
        # Pings the IP Addresses before starting the stream - Comment out if using USB
        #ping_device(ip_address_1)
        #ping_device(ip_address_2)

        startLocalQis()
        print("Spinning up CPU...")

        self.coordinate_multiproc_trigger(connection_type, FILE_NAME_PAM_1, FILE_NAME_PAM_2, STREAM_LENGTH, self.so_file)

    @staticmethod
    def compile_c_lib(C_CODE: str):
        """
        Compiles the C code to keep the CPU busy and ready to execute
        Args:
            C_CODE: The C Code to be compiled - different whether Windows or Linux

        Returns: so_file - The compiled C code

        """
        # If Windows, look for a .dll (dynamic link library) - else, look for a .so Shared Object file
        suffix = ".dll" if os.name == "nt" else ".so"

        # Creates the C file in the current working directory
        c_file = os.path.join(os.getcwd(), "spin_core.c")

        # Replaces the .c with .so or .dll
        so_file = c_file.replace(".c", suffix)

        #If compiled file is already present, don't recompile
        if os.path.exists(so_file):
            return so_file

        # Opens the c_file and writes the C_CODE to it
        with open(c_file, mode="w") as f:
            f.write(C_CODE)

        # gcc -O3 -shared -fPIC -o spin_core.dll spin_core.c
        command = ["gcc", "-O3", "-shared", "-fPIC", "-o", so_file, c_file]

        try:
            # Attempts to compile, and records the output
            subprocess.run(command, check=True, capture_output=True, text=True)
            return so_file

        # Catches the potential exception
        except Exception as e:
            print(f"Compilation Error: {e}")
            return None

    @staticmethod
    def sync_and_trigger_stream(target_ns,
                                pam_address: str,
                                filename: str,
                                so_file: str = "spin_core.dll",
                                connection_type: str = "QIS",
                                stream_duration: float = STREAM_LENGTH):
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
            # Connects 1st pam device to the same QIS Instance - timeout of 20s
            pam = get_quarch_device(connectionTarget=pam_address, ConType=connection_type, timeout=str(20))

            # Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
            pam_power_device = quarchPPM(pam)

            pam_power_device.send_command(f"stream mode resample {STREAM_RESAMPLE_RATE}")

        except Exception as e:
            print(f"Could not connect to PAM: {e}")
            sys.stdout.flush()  # Forces output

        try:
            # Loads the compiled file
            lib = ctypes.CDLL(so_file)

            # Calls the spin_until function inside, keeps CPU busy and ready
            lib.spin_until(ctypes.c_int64(target_ns))

            # Starts stream
            pam_power_device.start_stream(file_name=filename, stream_duration=stream_duration)

        # Catches potential exception
        except Exception as e:
            print(f"Error triggering stream: {e}")
            sys.stdout.flush()  # Forces output

    def coordinate_multiproc_trigger(
            self,
            connection_type: str = "QIS",
            filename_1: str = "RawDataPam1.csv",
            filename_2: str = "RawDataPam2.csv",
            stream_duration: float = STREAM_LENGTH,
            so_file: str = "spin_core.dll"):
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
        if os.name == "nt":  # If windows correct for epoch differences
            # Windows FileTime epoch is different from Unix Epoch
            # Windows Epoch is 1601, Unix Epoch is 1970 - The difference is 11 644 473 600 seconds
            # This is unix epoch (1970) since Windows epoch (1601), expressed in nanoseconds.
            epoch_correction_ns = (11644473600 * 1000000000)

            # Add a 5 seconds delay
            target = time.time_ns() + int(5 * 1e9) + epoch_correction_ns

        else:
            # CLOCK_MONOTONIC is the absolute elapsed time since system boot
            target = time.clock_gettime_ns(time.CLOCK_MONOTONIC) + int(5 * 1e9)

        # Creates Process objects
        process1 = multiprocessing.Process(target=self.sync_and_trigger_stream,
                                           args=(target,  PAM_1_ADDRESS, filename_1, so_file, connection_type,
                                                 stream_duration))
        process2 = multiprocessing.Process(target=self.sync_and_trigger_stream,
                                           args=(target, PAM_2_ADDRESS, filename_2, so_file, connection_type,
                                                 stream_duration))
        try:
            # Starts the processes activity
            process1.start()
            process2.start()

            # Shows progress bar for stream length with an extra 5 seconds
            visual_sleep((STREAM_LENGTH + 5), title="Stream in progress")

            # Blocks the main script until both processes are done
            process1.join()
            process2.join()

        except KeyboardInterrupt:
            if process1.is_alive():
                process1.terminate()
            if process2.is_alive():
                process2.terminate()

            process1.join()
            process2.join()

            sys.exit(0)

class CWindows(UsingC):
    def __init__(self):
        super().__init__()

        # C Code is different for Windows or POSIX
        C_CODE = """
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

        # Tells OS this python script is high priority
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)

        #Compiles the C Script
        self.so_file = self.compile_c_lib(C_CODE)



    def compiler_check(self):
        gcc_search_cmd = "where"

        try:
            check = subprocess.run([gcc_search_cmd, "gcc"], capture_output=True, text=True)
            if check.returncode != 0:  # Not Found
                print("******** GCC CHECK FAILED *********\n")
                print("Error: GNU Compiler Collection not found\n")
                print("Please install MinGW-w64")
                print("Download the MSYS2 Installer - https://www.msys2.org/")
                print("Open the MSYS2 Terminal and run the command")
                print("\npacman -S mingw-64-86_64-gcc\n")
                print(r"Then add C:\msys64\mingw64\bin to the PATH")
                print("Once installed and added, please re-run")
        except:
            raise ModuleNotFoundError

class CPosix(UsingC):
    def __init__(self):
        super().__init__()

        C_CODE = """
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

        try:
            os.nice(-20)  # Sets this script as highest priority
        except PermissionError:
            print("Warning: Run with sudo to enable high-priority timing.")

        # Compiles the C Script
        self.so_file = self.compile_c_lib(C_CODE)

    def compiler_check(self):
        gcc_search_cmd = "which"
        try:
            check = subprocess.run([gcc_search_cmd, "gcc"], capture_output=True, text=True)
            if check.returncode != 0:  # Not Found
                print("Please install MinGW-w64")
                print("On ubuntu please run the command\n")
                print(r"sudo apt install build-essentia")
                print("\nOn fedora please run the command\n")
                print(r"sudo dnf install gcc glibc-devel")
                print("\nOnce installed and added, please re-run")

        except:
            raise ModuleNotFoundError

class UsingPython(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def python_spin_until(self, target_ns):
        pass


    def stream(self, connection_type):
        # Pings the IP Addresses before starting the stream - Comment out if using USB
        SyncUtils.ping_device(ip_address_1)
        #ping_device(ip_address_2)

        startLocalQis()

        print("Spinning up CPU...")
        self.coordinate_multiproc_trigger(connection_type, FILE_NAME_PAM_1, FILE_NAME_PAM_2, STREAM_LENGTH)


    def coordinate_multiproc_trigger(self,
                                    connection_type: str = "QIS",
                                    filename_1: str = "RawDataPam1.csv",
                                    filename_2: str = "RawDataPam2.csv",
                                    stream_duration: float = STREAM_LENGTH):
        # 1. Calculate Target Time (No epoch corrections needed for just Python)
        if os.name == "nt":
            #Time now, plus 5 seconds (all in nanoseconds)
            target = time.time_ns() + int(5 * 1e9)
        else:
            # POSIX uses CLOCK_MONOTONIC for the most robust high-precision timing
            target = time.clock_gettime_ns(time.CLOCK_MONOTONIC) + int(5 * 1e9)

        # 2. Create Process objects
        process1 = multiprocessing.Process(target=self.sync_and_trigger_stream,
                                           args=(target, PAM_1_ADDRESS, filename_1, connection_type,
                                                 stream_duration))

        process2 = multiprocessing.Process(target=self.sync_and_trigger_stream,
                                           args=(target, PAM_2_ADDRESS, filename_2, connection_type,
                                                 stream_duration))
        try:
            # 3. Start the processes
            process1.start()
            process2.start()

            # 4. Show progress bar for stream length with an extra 5 seconds
            visual_sleep((STREAM_LENGTH + 5), title="Stream in progress")

            # 5. Block the main script until both processes are done
            process1.join()
            process2.join()

        except KeyboardInterrupt:
            if process1.is_alive():
                process1.terminate()
            if process2.is_alive():
                process2.terminate()

            process1.join()
            process2.join()

            sys.exit(0)

    def sync_and_trigger_stream(self,
                                target_ns,
                                pam_address: str,
                                filename: str,
                                connection_type: str = "QIS",
                                stream_duration: float = STREAM_LENGTH):
        """
        This is a worker function. This is executed on different cores for different PAM devices
        Args:
            target_ns: The time the system aims to execute at
            pam_address: The address of the PAM to be connected to - in the format "TCP:1.1.1.1"
            filename: The file to write to
            connection_type: Default QIS, but can be overwritten to QPS
            stream_duration: Stream length - how long to stream for

        Returns None:
        """

        try:
            # Connects 1st pam device to the same QIS Instance - timeout of 20s
            pam = get_quarch_device(connectionTarget=pam_address, ConType=connection_type)

            # Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
            pam_power_device = quarchPPM(pam)

            pam_power_device.send_command(f"stream mode resample {STREAM_RESAMPLE_RATE}")

        except Exception as e:
            print(f"Could not connect to PAM: {e}")
            sys.stdout.flush()  # Forces output

        try:
            #spin
            self.python_spin_until(target_ns)

            # Starts stream
            pam_power_device.start_stream(file_name=filename, stream_duration=stream_duration)

        # Catches potential exception
        except Exception as e:
            print(f"Error triggering stream: {e}")
            sys.stdout.flush()  # Forces output

class PyWindows(UsingPython):
    def __init__(self):
        super().__init__()

    def python_spin_until(self, target_ns):
        clock_id = None

        while True:
            now_ns = time.time_ns()

            if now_ns >= target_ns:
                break

class PyPosix(UsingPython):
    def __init__(self):
        super().__init__()

    def python_spin_until(self, target_ns):
        clock_id = time.CLOCK_MONOTONIC

        while True:
            now_ns = time.clock_gettime_ns(clock_id)

            if now_ns >= target_ns:
                break

def launch_and_run(connection_type):

    if connection_type == "QPS":
        # QPS instance 1 is easy - use default ports
        qps1 = startLocalQps(startQPSMinimised=False)

        # Connects 1st pam device to the same QIS Instance - timeout of 20s timeout=str(20)
        pam1 = get_quarch_device(connectionTarget=PAM_1_ADDRESS, ConType=connection_type, qps_instance=qps1)

        #Create separate QIS backend
        startLocalQis(port=9723,rest_port=9781)
        #Creates separate QPS launch, connected to second QIS instance
        qps2 = startLocalQps(startQPSMinimised=False,port=9823, qis_port=9723, qis_rest_port=9781)

        #Connects the 2nd PAM to the 2nd QIS
        pam2 = get_quarch_device(connectionTarget=PAM_2_ADDRESS, ConType=connection_type, qps_instance=qps2)

        #Returns the pams, and qps objects
        return pam1, pam2, qps1, qps2

    else:  # QIS

        # If QIS is not already running
        if isQisRunning():
            qis = QisInterface()
        else:
            # Start Local QIS Instance
            print("Starting QIS...")
            qis = startLocalQis()

        # Connects 1st pam device to the same QIS Instance - timeout of 20s timeout=str(20)
        pam1 = get_quarch_device(connectionTarget=PAM_1_ADDRESS, ConType=connection_type)

        pam2 = get_quarch_device(connectionTarget=PAM_2_ADDRESS, ConType=connection_type)
        return pam1, pam2, qis







def start_qps_and_connect():
    startLocalQps()

    # Connects to localhost QPS Instance
    qps_instance = qpsInterface()

    # Connect PAM1 (again), explicitly QPS
    pam_1_device = get_quarch_device(connectionTarget=PAM_1_ADDRESS, ConType="QPS")

    # Upgrade PAM1 to a QPS device
    my_qps_pam = quarchQPS(pam_1_device)

    # Opens connection to PAM - Required to convert a CSV to QPS
    my_qps_pam.open_connection()
    return qps_instance

if __name__ == "__main__":
    main()

import ctypes
import multiprocessing
import subprocess
import sys
import time
from abc import ABC, abstractmethod
import os

import psutil
from quarchpy.device import get_quarch_device, quarchPPM
from quarchpy.user_interface import visual_sleep

import syncUtils

class UsingC(ABC):
    #Assigns constructor params to local params
    def __init__(self, pam_configs, stream_length: float, resample_rate: str, ):
        """
        Constructor for abstract class UsingC. Cannot be directly called, but is called when child is called
        """
        self.so_file = None
        self.pam_config = pam_configs
        self.stream_length = stream_length
        self.resample_rate = resample_rate

        self.ip_addresses = []

        #Checks if the PAMs are connected via IP, and therefore whether we can ping the device
        #pam_1_address is in the form "TCP:1.1.1.1"
        for pam in pam_configs:
            if pam["address"].split(":")[0] == "TCP":
                self.ping_allowed = True
                #Stores IP address as 1.1.1.1
                self.ip_address = pam["address"].split(":")[1]
                #Adds to list of IP addresses
                self.ip_addresses.append(self.ip_address)


    #Uses OS specific child method
    @abstractmethod
    def compiler_check(self):
        pass

    def stream(self, connection_type):
        """
        This is called in the main script. This sets up the multiprocessing, and worker function
        """

        print("Spinning up CPU...")

        # If both devices are connected via IP
        if self.ping_allowed:
            for ip_address in self.ip_addresses:
                syncUtils.ping_device(ip_address)


        self.coordinate_multiproc_trigger(self.stream_length, connection_type, self.so_file)

        """
                    stream_duration: float,
            pam_configs,
            connection_type: str = "QIS",
            so_file: str = "spin_core.dll"):"""

    @staticmethod
    def compile_c_lib(C_CODE: str):
        """
        Compiles the C code to keep the CPU busy and ready to execute.
        Checks whether compiled file is found already, and if it is then skips compiling
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
                                stream_duration: float,
                                resample_rate: str,
                                so_file: str = "spin_core.dll",
                                connection_type: str = "QIS"):
        """
        This is a worker function. This is executed on different cores for different PAM devices
        Args:
            target_ns: The time the system aims to execute at
            pam_address: The address of the PAM to be connected to - in the format "TCP:1.1.1.1"
            filename: The file to write to
            so_file: The compiled C code
            resample_rate: Rate at which to resample
            stream_duration: Stream length - how long to stream for
            connection_type: Default QIS, but can be overwritten to QPS


        Returns None:
        """

        try:
            # Connects 1st pam device to the same QIS Instance - timeout of 20s
            pam = get_quarch_device(connectionTarget=pam_address, ConType=connection_type)

            # Upgrades PAM to quarchPPM class - named before the PAM was created, works for all power products
            pam_power_device = quarchPPM(pam)

            #Resamples the stream to the same rate.
            pam_power_device.send_command(f"stream mode resample {resample_rate}")

            # Loads the compiled file
            lib = ctypes.CDLL(os.path.abspath(so_file))

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
            stream_duration: float,
            pam_configs,
            connection_type: str = "QIS",
            so_file: str = "spin_core.dll"):
        """
        The worker function to be called
        Args:
            stream_duration: Stream length
            pam_configs: List of PAMs connected and filenames
            so_file: The compiled C code
            connection_type: Default QIS, but can be overwritten to QPS


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

        processes = []

        common_args = {
            "target_ns": target,
            "stream_duration": stream_duration,
            "resample_rate": self.resample_rate,
            "so_file": so_file,
            "connection_type": connection_type
        }

        # If both devices are connected via IP
        if self.ping_allowed:
            for ip_address in self.ip_addresses:
                syncUtils.ping_device(ip_address)

        #Able to select how many PAMs are connected
        for pam in pam_configs:
            worker_kwargs = {**common_args,
                             "pam_address": pam["address"], "filename": pam["filename"]}

        # Create Process objects
            process = multiprocessing.Process(target=self.sync_and_trigger_stream, kwargs=worker_kwargs)

            # If both devices are connected over TCP, ping them to ensure they are awake and ready
            if self.ping_allowed:
                for ip_address in self.ip_addresses:
                    syncUtils.ping_device(ip_address)

            # Starts the processes activity
            process.start()

            processes.append(process)


        for process in processes:
            # Blocks the main script until both processes are done
            process.join()


class CWindows(UsingC):
    def __init__(self, filename1, filename2, stream_length, resample_rate, pam_1_address, pam_2_address):
        #Pass parameters to parents constructor
        super().__init__(filename1, filename2, stream_length,resample_rate, pam_1_address, pam_2_address)

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

        #Checks compiler is available
        self.compiler_check()

        self.ping_allowed = None


        #Compiles the C Script
        self.so_file = self.compile_c_lib(C_CODE)



    def compiler_check(self):
        """
        Checks if a C compiler is installed and added to the path of the system
        Provides instructions if not installed
        """

        try:
            check = subprocess.run(["where", "gcc"], capture_output=True, text=True)
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
    def __init__(self,filename1, filename2, stream_length,resample_rate, pam_1_address, pam_2_address):
        super().__init__(filename1, filename2, stream_length,resample_rate, pam_1_address, pam_2_address)

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

        self.ping_allowed = None

        #Checks compiler is installed and accessible
        self.compiler_check()

        # Compiles the C Script
        self.so_file = self.compile_c_lib(C_CODE)

    def compiler_check(self):
        """
        Checks if a C compiler is installed and added to the path of the system
        """
        try:
            check = subprocess.run(["which", "gcc"], capture_output=True, text=True)
            if check.returncode != 0:  # Not Found
                print("Please install MinGW-w64")
                print("On ubuntu please run the command\n")
                print(r"sudo apt install build-essentia")
                print("\nOn fedora please run the command\n")
                print(r"sudo dnf install gcc glibc-devel")
                print("\nOnce installed and added, please re-run")

        except:
            raise ModuleNotFoundError
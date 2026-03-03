import multiprocessing
from datetime import datetime
import subprocess
import time

import pandas as pd
import os

from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qps import startLocalQps
from quarchpy.device import quarchPPM, get_quarch_device

def csv_combiner(file_list):
    """
    Merges the PAM Stream CSVs, keeps shared time column, renames and adds 1_ and 2_ to the column headers
    Uses pandas
    Args:
        file_list: List of file paths

    Returns CSV of the combined data:
    """

    #Column name of the time column - This will be the same in both CSVs, and should not be changed
    #Time uS may change according to sample time
    shared_time_column = "Time uS"
    #Create empty dataframe
    master_df = None

    #For each file in the file list
    for i, file_path in enumerate(file_list):
        #Convert to a dataframe
        df = pd.read_csv(file_path)
        #Create the prefix of 1_xxx, 2_xxx...
        prefix = f"{i+1}_"
        #Add the prefix to the columns
        df = df.add_prefix(prefix).rename(columns={prefix + shared_time_column: shared_time_column})

        if master_df is None:
            #If this is the first file, it becomes the base of our master dataframe
            master_df = df
        else:
            #Merge subsequent files onto the master
            #'outer' merge ensures we don't lose data if one PAM has more samples than another
            master_df = pd.merge(master_df, df, on=shared_time_column, how="outer")

    #Convert the dataframe to CSV
    combined_csv = master_df.to_csv("CombinedData.csv", index=False)

    path = os.path.abspath("CombinedData.csv")
    #Changes the dataframe to CSV
    print(f"CSV can be found :{path}")
    return path

def view_csv_in_qps(csv_path:str, pam_address:str, qps_instance: QpsInterface = None):
    """
    Opens QPS and reconnects to PAM 1
    Used for user to view the CSVs as QPS Traces

    :parameter csv_path: The full CSV path to view
    :parameter pam_address: PAM - The address of the PAM to reconnect to
    :parameter qps_instance: QpsInterface - If QPS is already open, use that, otherwise a new instance will be launched

    Returns: None
    """

    if qps_instance is None:
        print("Opening QPS...")
        qps_instance = startLocalQps()

    #Connects to the pam specified
    qps_instance.connect(pam_address)

    #Get the current working directory, create new folder and target recording
    #If this folder exists already, will fail
    file_path = os.getcwd() + rf"\sync_stream\sync_stream.qps"

    print("Converting CSV file to QPS")

    #Formulates QPS command to convert CSV to QPS recording
    command = f'$convert csv from="{csv_path}" to="{file_path}"'
    #Sends the command
    qps_instance.sendCommand(command)

    print(f"Opening QPS Recording. Stored: {file_path}")

    #Formulates QPS command to open the QPS file created
    command = f'$open recording qpsFile="{file_path}"'
    qps_instance.sendCommand(command)


def spin_cpu_simple(pam_address: str, filename: str, target_ns: int, resample_rate:str, stream_length: int):
    """
    Simple version to spin up the CPU core, using python only, and then start stream when a time has passed
    :param pam_address: PAM - The IP address of the PAM to stream
    :param filename: The filename to save data to
    :param target_ns: Target time to spin up until
    :param resample_rate: Resampling rate to use
    :param stream_length: Stream length to use

    Returns: None
    """
    # Change the clock to account for epoch differences on OSs
    clock_id = time.CLOCK_MONOTONIC if os.name == "POSIX" else None

    #Connects to the PAM - Pickling error otherwise
    pam = get_quarch_device(pam_address, ConType="QIS")
    #Upgrades to PPM class
    pam = quarchPPM(pam)

    pam.send_command(f"stream mode resample {resample_rate}")

    while True:  # Keep the CPU busy
        # Get current time in nanoseconds
        now = time.clock_gettime_ns(clock_id) if clock_id else time.time_ns()

        #If we have reached the time we are waiting for
        if now >= target_ns:
            #Start stream
            pam.start_stream(filename, stream_duration=stream_length)
            #Exit loop
            break

def spin_cpu_and_start_stream(pam_1_address: str, pam_2_address: str, resample_rate: str, stream_length: int):
    """
    Uses multiple CPU cores to keep busy, and then release at a set point, in effort to reduce the time needed to start stream

    :param pam_1_address: PAM1
    :param pam_2_address: PAM2
    :param resample_rate: Resampling rate to use
    :param stream_length: Stream length to use

    Returns: None
    """
    # More complex but much quicker
    # Changes what clock is used depending on windows or posix
    clock_id = time.CLOCK_MONOTONIC if os.name == "POSIX" else None

    # Gets the current time in nanoseconds
    now = time.clock_gettime_ns(clock_id) if clock_id else time.time_ns()

    # 3 seconds in the future (in nanoseconds)
    target_ns = now + int(3 * 1e9)

    # Uses 1 core per PAM, keeps CPU busy until time starts
    #Passes in the PAM, file to save data to, and the time to spin until
    process1 = multiprocessing.Process(target=spin_cpu_simple,
                                       args=(pam_1_address, "RawDataPam1.csv", target_ns, resample_rate, stream_length))
    process2 = multiprocessing.Process(target=spin_cpu_simple,
                                       args=(pam_2_address, "RawDataPam2.csv", target_ns, resample_rate, stream_length))

    time.sleep(2)

    try:
        #Starts the process's activity
        process1.start()
        process2.start()

        #Blocks the main script until both processes are done
        process1.join()
        process2.join()

    #If user exits (e.g. Ctrl+C) safely close the processes
    except KeyboardInterrupt:
        #Checks if alive
        if process1.is_alive():
            #Close the process
            process1.terminate()
        if process2.is_alive():
            process2.terminate()

        #Exit the script
        exit(0)

def ping_device(ip_address:str):
    """
    Pings the specified IP address, to ensure the device is awake and ready to connect. In testing this saved a few milliseconds
    Likely due to Address Resolution Protocol
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
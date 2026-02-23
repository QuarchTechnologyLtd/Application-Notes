from datetime import datetime
import subprocess
import time

import pandas as pd
import os

from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qps import startLocalQps
from quarchpy.device import quarchPPM




def csv_combiner(csv_file_1:str, csv_file_2:str):
    """
    Merges the PAM Stream CSVs, keeps shared time column, renames and adds 1_ and 2_ to the column headers
    Args:
        csv_file_1: CSV file 1
        csv_file_2: CSV file 2

    Returns CSV of the combined data:
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
    return merged_data.to_csv("CombinedData.csv", index=False)

def spin_cpu_simple(pam: quarchPPM, filename: str, target_ns: int):
    """
    Used in the simple version to spin up the CPU core, using python only, and then start stream when a time has passed
    :param pam: PAM - The PAM to stream
    :param filename: The filename to save data to
    :param target_ns: Target time to spin up until
    Returns: None
    """
    # Change the clock to account for epoch differences on OSs
    clock_id = time.CLOCK_MONOTONIC if os.name == "POSIX" else None


    while True:  # Keep the CPU busy
        # Get current time in nanoseconds
        now = time.clock_gettime_ns(clock_id) if clock_id else time.time_ns()

        #If we have reached the time we are waiting for
        if now >= target_ns:
            #Start stream
            pam.start_stream(filename, stream_duration=60)
            #Exit loop
            break

def view_csv_in_qps(csv_file:str, qps_instance: QpsInterface = None):
    """
    Opens QPS and reconnects to PAM 1
    Used for user to view the CSVs as QPS Traces

    :parameter csv_file: The CSV to view
    :parameter qps_instance: QpsInterface - If QPS is already open, use that, otherwise a new instance will be launched

    Returns: None
    """

    if qps_instance is None:
        qps_instance = startLocalQps()

    current_time = datetime.now()
    formatted_time = current_time.strftime("_%H_%M_%S")

    file_path = os.getcwd() + rf"\sync_stream\sync_stream.qps"

    print("Converting CSV file to QPS")

    command = f'$convert csv from="{csv_file}" to="{file_path}"'
    response = qps_instance.sendCommand(command)
    print(response)

    print(f"Opening QPS Recording. Stored: {file_path}")

    command = f'$open recording qpsFile="{file_path}"'
    response = qps_instance.sendCommand(command)
    print(response)

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
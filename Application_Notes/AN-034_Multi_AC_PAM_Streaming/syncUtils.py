import multiprocessing
import re
from datetime import datetime
import subprocess
import time

import pandas as pd
import os

from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.qps import startLocalQps
from quarchpy.device import quarchPPM, get_quarch_device
from quarchpy.user_interface import showYesNoDialog, visual_sleep


def csv_combiner(file_list, timestamp, trigger_times_ns):
    """
    Merges the PAM Stream CSVs, keeps shared time column, renames and adds 1_ and 2_ to the column headers
    We adjust the data to align as much as possible. There will be empty data at either end
    Uses pandas
    Args:
        file_list: List of file paths
        timestamp: Timestamp of the start of the stream for filenames
        trigger_times_ns: Array of timestamps used for time alignment in the CSVs

    Returns: csv_path
    The path of the merged csv
    """

    #Column name of the time column - This will be the same in both CSVs, and should not be changed
    shared_time_column = "Time uS"
    #Create empty dataframe
    master_df = None

    #We now compare the timestamps for alignment
    #Calculate the difference between the trigger times
    base_time_ns = min(trigger_times_ns)
    #Gets the offset in microseconds
    list_offsets_us = [(t - base_time_ns) / 1000.0 for t in trigger_times_ns]

    print("Saving data...")

    #Display the offset to the user - one will be 0.00us as it will be the base
    for i, offset in enumerate(list_offsets_us):
        print(f"RawDataPAM{i+1}.csv offset +{offset:.2f} uS")

    #For each file in the file list
    for i, file_path in enumerate(file_list):
        #Convert to a dataframe
        df = pd.read_csv(file_path)

        print("Aligning timestamps")

        #Calculate the sample rate by  - (time uS cell 2 - time uS cell 1)
        sample_interval_us = df[shared_time_column].iloc[1] - df[shared_time_column].iloc[0]

        #Get the offset from the list we made earlier
        raw_offset = list_offsets_us[i]

        #Round the offset
        rounded_offset = round(raw_offset / sample_interval_us)

        #Multiply back into microseconds
        rounded_offset_us = rounded_offset  * sample_interval_us

        #Adjust the calculated offset to align the data on the combined doc
        df[shared_time_column] = df[shared_time_column] + rounded_offset_us

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

    #Convert the dataframe to CSV with a timestamped name
    master_df.to_csv(f"CombinedData_{timestamp}.csv", index=False)

    path = os.path.abspath(f"CombinedData_{timestamp}.csv")
    #Changes the dataframe to CSV
    print(f"CSV can be found :{path}")
    return path

def view_csv_in_qps(pam_address:str, stream_length, timestamp, file_list, trigger_times_ns, qps_instance: QpsInterface = None):
    """
    Calls the function to merge the CSVs together
    Opens QPS and reconnects to PAM 1
    Used for user to view the CSVs as QPS Traces

    :parameter pam_address: PAM - The address of the PAM to reconnect to
    :parameter stream_length: Stream length - used for changing the chart view
    :parameter timestamp: Timestamp of the start of the stream for filenames
    :parameter file_list: List of CSV files to merge - passed into csv_combiner
    :parameter trigger_times_ns: Array of timestamps used for time alignment in the CSVs
    :parameter qps_instance: QpsInterface - Optional. If QPS is already open, use that, otherwise a new instance will be launched

    Returns: csv_path - the path of the CSVs
    """
    #Calls the function to combine the CSVs
    csv_path = csv_combiner(file_list, timestamp, trigger_times_ns)

    #If QPS is not already running (passed in), launch it
    if qps_instance is None:
        print("Opening QPS...")
        qps_instance = startLocalQps()

    #Connects to the pam specified
    qps_instance.connect(pam_address)

    #Get the current working directory, create new folder and target recording, timestamped
    file_path = os.path.join(os.getcwd(), os.path.join(f"sync_stream_{timestamp}", f"sync_stream_{timestamp}.qps"))

    print("Converting CSV file to QPS")

    #Formulates QPS command to convert CSV to QPS recording
    command = f'$convert csv from="{csv_path}" to="{file_path}"'
    #Sends the command
    qps_instance.sendCommand(command)

    print(f"Opening QPS Recording. Stored: {file_path}")

    #Creates QPS command to open the QPS file created and sends it
    command = f'$open recording qpsFile="{file_path}"'
    qps_instance.sendCommand(command)

    print("Adjusting chart to width...")
    #Sleeps for 1 seconds to open recording and for QPS timeline to adjust
    time.sleep(1)

    # Set chart width to desired chart width or the full stream
    # If we have a stream for more than the default of 100S, display 100S
    desired_chart_width = 100

    if stream_length > desired_chart_width:
        cmd = f"$chart reposition 0S {desired_chart_width}S"
    else:  # Otherwise, display the full stream that we have
        # The -1 is to fix a minor issue in case the recording is e.g. 19.995s rather than 20s
        cmd = f"$chart reposition 0S {stream_length - 1}S"

    #Polled to fix the issue of sending the repositioning command too fast and failing
    response = None
    #Poll the response
    while response != "OK":
        #Send the chart reposition command
        response = qps_instance.sendCommand(cmd)
        #Sleeps for 0.1 seconds so we don't poll too fast
        time.sleep(0.1)

    print(f"Chart width adjusted: {response}")

    #Release the PAM connection
    qps_instance.disconnect(pam_address)

    return csv_path


def spin_cpu_simple(pam_address: str, filename: str, target_ns: int, resample_rate: str, stream_length: int, pam_event, trigger_times, index):
    """
    This is to spin up the CPU using Python. This specific function is called once for each PAM

    :params pam_address: Address of the PAM
    :params filename: Filename of the CSV to save to
    :params target_ns: Target time to trigger
    :params resample_rate: Resampling rate to use
    :params stream_length: Stream length in seconds
    :params pam_event: A Multiprocessing Event object - This is a flag management object
    :params trigger_times: A shared Multiprocessing object of times to start streaming
    :params index: Which PAM we are using - used for the time alignment

    :Returns None

    """
    # Change the clock to account for epoch differences on OSs
    clock_id = time.CLOCK_MONOTONIC if os.name == "POSIX" else None

    print('\nConnecting to ' + pam_address + '...')

    # Connects to the PAM via QIS
    pam = get_quarch_device(pam_address, ConType="QIS")

    # Upgrades to PPM class - adds more features
    pam = quarchPPM(pam)

    #Shows the user we are connected to the PAM
    pam_name = pam.send_command("hello?")
    print(f"PAM is {pam_name}")

    #Resample the PAM to the user input
    pam.send_command(f"stream mode resample {resample_rate}")

    #Use the shared Event flag to tell the spin function that this PAM is connected and ready to spin
    pam_event.set()

    while True:  # Keep the CPU busy until current time = target time, then we will start the stream
        # Get current time in nanoseconds
        now = time.clock_gettime_ns(clock_id) if clock_id else time.time_ns()

        #If we are at target time
        if now >= target_ns:
            #Starts stream
            pam.start_stream(filename, stream_duration=stream_length)

            #Stores the current time in an index, adjusted for OS differences
            trigger_times[index] = time.clock_gettime_ns(clock_id) if clock_id else time.time_ns()

            # Sleep with a progress bar, with a 7-second buffer, to make sure we start and finish the stream in time
            #2 progress bars will be displayed, 1 for each PAM
            print(f"Stream in progress for module: Name: {pam_name} IP Address: {pam_address}")
            visual_sleep(stream_length + 7)

            #Stream is done, close connection to PAM
            pam.close_connection()

            # Exit loop
            break

def spin_cpu_and_start_stream(pam_1_address: str, pam_2_address: str, resample_rate: str, stream_length: int):
    """
    Coordinates the streams starting

    :params pam_1_address: Address of PAM 1
    :params pam_2_address: Address of PAM 2
    :params resample_rate: Resampling rate to use
    :params stream_length: Stream length in seconds

    Returns: trigger_times: A list of the time the streams started
    """
    #Adjust clock for OS differences.
    clock_id = time.CLOCK_MONOTONIC if os.name == "POSIX" else None

    #Create multiprocessing events - shared flag between the two processes
    pam_1_event = multiprocessing.Event()
    pam_2_event = multiprocessing.Event()

    #Shared array to capture the timestamps of the recording
    #q is a signed 64 bit integer - equivalent to long long. Used to store time in nanoseconds where we need the size
    #2 means we reserve 2 64 bit slots in the shared memory. [0] for PAM1, [1] for PAM 2
    trigger_times = multiprocessing.Array("q", 2)

    # Gets the current time in nanoseconds
    now = time.clock_gettime_ns(clock_id) if clock_id else time.time_ns()

    #Set target 5 seconds (in nanoseconds) in the future
    target_ns = now + int(5 * 1e9)

    #Create the processes, pass in the arguments
    process1 = multiprocessing.Process(target=spin_cpu_simple,
                                       args=(pam_1_address, "RawDataPam1.csv", target_ns, resample_rate, stream_length, pam_1_event, trigger_times, 0))
    process2 = multiprocessing.Process(target=spin_cpu_simple,
                                       args=(pam_2_address, "RawDataPam2.csv", target_ns, resample_rate, stream_length, pam_2_event, trigger_times, 1))

    try:
        #Start the processes
        process1.start()
        process2.start()

        #Wait for the connection - flag to change
        print("Waiting for PAM connections")
        pam_1_event.wait()
        pam_2_event.wait()

        print(f"\nBoth PAMs ready. Spinning up CPU - triggering in 5 seconds...")

        # Blocks the main script until both processes are done, with 5 second buffer so we don't end too early
        process1.join(timeout=stream_length + 5)
        process2.join(timeout=stream_length + 5)

        # Once the stream is done, we check if the processes are alive and terminate them
        if process1.is_alive():
            process1.terminate()
            process1.join()

        if process2.is_alive():
            process2.terminate()
            process2.join()

    # If user exits (e.g. Ctrl+C) safely close the processes
    except KeyboardInterrupt:
        if process1.is_alive():
            process1.terminate()
        if process2.is_alive():
            process2.terminate()
        exit(0)

    #Returns the time in nanosecond the streams started
    return list(trigger_times)

def validate_resample_rate(resample_rate_input: str, allow_4us_sampling: bool = False) -> str:
    """
    Used to take a user input, and check that it is valid
    If the inputted value is faster than we can sample, we set the PAM to the fastest rate
    Otherwise, if it is 125us or slower, we accept the value

    :param resample_rate_input: The user inputted resample rate to use
    :param allow_4us_sampling: True if we can sample at up to 4us, False otherwise - Will be true if both PAMs are DC PAMs

    :Returns: validated resample rate
    """

    #Validation - Force lower case
    resample_rate_input = resample_rate_input.lower()
    #Remove any whitespace
    resample_rate_input = resample_rate_input.replace(" ", "")

    # If nothing is entered, use the default of 1ms
    if resample_rate_input == "":
        print("No resample rate selected, using default of 1ms")
        resample_rate = "1ms"

    else:  #Some value has been entered
        # Regex to extract number and letter
        #If e.g. 500us is entered, this pattern will catch 500 and us as two indices
        match = re.match(r"(\d+)([a-zA-Z]+)", resample_rate_input)

        #Get the number and store it - e.g. 500
        number_resample = int(match.group(1))

        #Gets the suffix and store it - e.g. us
        suffix = match.group(2)

        #Validation - Checks that the number is positive
        if number_resample > 0:
            #If the suffix is microseconds, we need to check that we aren't attempting to sample faster than we actually can
            if suffix == "us":
                #If both PAMs are DC PAMs, we can sample at up to 4us.
                if allow_4us_sampling:
                    #If something like 2us is entered, we will set it to the minimum of 4us
                    if number_resample < 4:
                        print("Number entered is faster than the maximum rate, using 4us (fastest rate)")
                        resample_rate = "4us"
                    else: #If we are not trying to sample faster than we are able to, we accept the inputted number
                        resample_rate = resample_rate_input

                else: #If at least 1 PAM is not a DC PAM, we will limit the sample rate to 125us. This assumes we want to sample both PAMs at the same rate
                    if number_resample < 125:
                        print("Number entered is faster than the maximum rate, using 125us (fastest rate)")
                        resample_rate = "125us"
                    else:  #If we are not trying to sample faster than we are able to, we accept the inputted number
                        resample_rate = resample_rate_input

            #Otherwise, if the suffix is milliseconds or seconds, we assume its valid
            elif suffix == "ms" or suffix == "s":
                resample_rate = resample_rate_input

            else: #This means something that wasn't us, ms or s is entered. We assume this is invalid, so use the default
                print("Value entered is invalid. Using default of 1ms")
                resample_rate = "1ms"
        else: #If the number entered is negative (invalid), we will use the default
            print("Cannot have a negative resample rate, using default of 1ms")
            resample_rate = "1ms"

    #After our checks have been done, we will return the validated resample rate
    return resample_rate

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
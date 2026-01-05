#!/usr/bin/env python
"""
This example demonstrates basic automation with QIS and post-processing of raw data after recording.
We will record at a high rate and post-process down to a lower rate, ending with 100uS and 500uS sample rates

The resampling implementation is basic and currently coded for a PPM Plus which has a fixed number of
columns in the CSV file.  It could be expanded for a PAM with a higher number of channels.

########### REQUIREMENTS ###########

1- Python 3, a recent version is recommended
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

########### INSTRUCTIONS ###########

1- Connect a Quarch PPM connected to your PC via USB or LAN and power it on
2- Ensure quarcypy is installed
3- Run the script

####################################
"""


import os, time
import logging
import quarchpy
from quarchpy.device import *
from quarchpy.qis import *
from quarchpy.user_interface import visual_sleep

# Path where stream will be saved to (defaults to the current script path)
stream_path = os.path.dirname(os.path.realpath(__file__))

def main() -> None:
    """
    Simple main function to run the example code

    Returns:
        None

    """

    # If required, you can enable python logging, quarchpy supports this, and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

    # Required min version for this application note
    quarchpy.requiredQuarchpyVersion ("2.0.9")

    print("\n\nQuarch application note example: AN-022")
    print("-------------------------------------------")

    # Start QIS (if it is already running, skip this step and also avoid closing it at the end)
    # This is just to be helpful as you may want to run against an already loaded instance of QIS
    print("Checking for QIS...")
    close_qis_at_end_of_test = False
    if not isQisRunning():
        print("Starting QIS")
        startLocalQis()
        close_qis_at_end_of_test = True
    else:
        print("QIS already running. Using this instance.")

    # Connect to the localhost QIS instance and demonstrate a simple command which in this case
    # returns the QIS version string
    my_qis = QisInterface()
    print("QIS Version: " + my_qis.sendCommand('$version') + "\n\n")

    # Use the module selection helper dialog which prompts the user to select a module to talk to.
    # We can supply additional options to the dialog, such as 'quit' (which we can handle), the others
    # are handled internally to give additional options (rescanning after you remember to turn the power on to the
    # device, for example!)
    my_device_id = my_qis.GetQisModuleSelection(additionalOptions=['Rescan', 'All Con Types', 'Ip Scan', 'Quit'])
    # Exit cleanly on quit request
    if my_device_id.lower() == "quit":
        print("User Selected Quit.")
        if close_qis_at_end_of_test:
            closeQis()
        return

    # The return from the module selection is a device ID string that we can use to connect to.
    # If you know the name of the module you would like to talk to, then you can skip module selection and
    # hardcode the string using the serial number or IP address
    print("Module Selected: " + my_device_id + "\n")
    # my_device_id = "USB:QTL1999-05-005"
    # my_device_id = "TCP:192168.1.25"

    # Connect to the module, we request a QIS type connection
    my_quarch_device = getQuarchDevice(my_device_id, ConType="QIS")

    # Convert the base device class to a power device, which provides additional controls, such as data streaming
    my_power_device = quarchPPM(my_quarch_device)

    # Some quarch devices have a power output which is disabled by default, so we can enable it here using a helper
    # function that will work for all standard devices.  You could also send the "run:power up" command directly
    # which will work for most devices.
    my_power_device.setupPowerOutput()
    # (OPTIONAL) Wait for your device to power up and become ready (you can also start your workloads here if needed)
    # time.sleep(5)

    print ("-Setting up module record parameters")

    msg = my_power_device.sendCommand ("stream mode resample 100uS")
    if msg != "OK":
        print ("Failed to set software resampling: " + msg)

    print ("-Recording data...")
    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    file_name = "RawData100us.csv"
    my_power_device.start_stream (stream_path + "\\" + file_name)
           
    # Wait for a few seconds to record data then stop the stream     
    visual_sleep(10, title="Recording at 100uS")    # VGives you a visual indication of the delay time

    # INSERT YOUR CODE HERE?
    # Instead of just sleeping, you can run workloads to your drive or any other action required to complete the test
    # The data will continue to be streamed to file in the background

    # Check the stream status, so we know if anything went wrong during the capture period
    # This is not essential, but some tests may need you to ensure that all data across the
    # full stream period has been captured correctly
    print("Checking the stream is running (all data has been captured)")
    stream_status = my_power_device.streamRunningStatus()
    if "running" not in stream_status:
        print("\tStream terminated early: " + stream_status)
    else:
        print("\tStream ran correctly across the full test")

    # Stop the stream.  This function is blocking and will wait until all remaining data has
    # been downloaded from the module. This may take a couple of seconds.
    print("\nStopping the stream...")
    my_power_device.stopStream()

    # Request raw CSV data from the stream, into the local folder
    raw_output_path = stream_path + "\\RawData100us.csv"

    # Run the post-process step.  The first one is purely for the stats calculations, as we already have it in the correct sample rate
    print ("-Post processing step 1 - Calc Stats")
    post_process_resample (raw_output_path, 1, stream_path + "\\PostData100us.csv")
    print ("-Post processing step 2 - Resample to 500uS")
    post_process_resample (raw_output_path, 5, stream_path + "\\PostData500us.csv")
    print ("-Post processing step 3 - Resample to 1mS")
    post_process_resample (raw_output_path, 10, stream_path + "\\PostData1ms.csv")

    print ("\nAll processing complete!\n\n")

    if close_qis_at_end_of_test:
        closeQis()

def post_process_resample (raw_file_path: str, resample_count: int, output_file_path: str) -> None:
    """
    Post process and resamples a CSV file output by combining multiple stripes of data into one
    Assumes standard PPM channels are enabled for this quick example.  The resample process uses
    averaging to ensure that

    We also calculate the maximum, minimum and average values for each channel and write them
    to the bottom of the output file

    Args:
        raw_file_path:
            Input file path to read
        resample_count:
            Number of stripes to combine into one
        output_file_path:
            New output file path to create
    Returns:

    """
    # Init variables
    header_lines = 0
    stripe_count = 0
    delimiter = ","
    number_of_columns = 9
    averaged_stripe_count = 0
    # Storage for the accumulating data (9 columns of data)
    proc_data = [0,0,0,0,0,0,0,0,0]
    # Storage for the summary data (8 columns as time is note processed)
    max_data = [0,0,0,0,0,0,0,0]
    min_data = [999999,999999,999999,999999,999999,999999,999999,999999]
    ave_data = [0,0,0,0,0,0,0,0]
    # Open both the input and output files in appropriate access modes
    with open(raw_file_path, 'r') as rawFile:
        with open (output_file_path, 'w') as postFile:
            # Iterate through all input files
            for fileLine in rawFile:
                # The header line is unique, copy it directly
                if header_lines < 2:
                    postFile.write (fileLine + "\n")
                    header_lines = header_lines + 1
                    continue

                # Accumulate the required number of lines                
                line_sections = fileLine.split(delimiter)
                # Update to the latest time point
                proc_data[0] = line_sections[0]
                # Sum the values for all other columns
                for i in range (1, number_of_columns):                                    
                    proc_data[i] += int(line_sections[i])
                stripe_count += 1

                # When we have enough data to complete one output line we can process it
                if stripe_count == resample_count:
                    # Track the number of output stripes
                    averaged_stripe_count += 1

                    # Divide down the averaged columns to get the final result
                    for i in range (1, number_of_columns):                                    
                        proc_data[i] /= resample_count
                    # Generate the single line for the output file
                    out_str = delimiter.join (str(x) for x in proc_data)
                    postFile.write (out_str + "\n")
                    # Track maximums
                    for i in range (1, number_of_columns):       
                        if proc_data[i] > max_data[i - 1]:
                            max_data[i-1] = proc_data[i]
                    # Track minimums
                    for i in range (1, number_of_columns):
                        if proc_data[i] < min_data[i - 1]:
                            min_data[i-1] = proc_data[i]
                    # Track averages (Note: large datasets may overflow this simple averaging mechanism)
                    for i in range (1, number_of_columns):                       
                        ave_data[i-1] += proc_data[i]

                    # Reset the accumulating data buffer
                    proc_data = [0,0,0,0,0,0,0,0,0]
                    stripe_count = 0

            # Complete the calculation of the average values
            for i in range (1, number_of_columns):                       
                ave_data[i-1] /= averaged_stripe_count

            # Add the stats data to the bottom of the output file
            postFile.write ("\n\nSTATISTICS\n")
            postFile.write ("MAX," + delimiter.join(str(x) for x in max_data) + "\n")
            postFile.write ("MIN," + delimiter.join(str(x) for x in min_data) + "\n")
            postFile.write ("AVE," + delimiter.join(str(x) for x in ave_data) + "\n")

if __name__=="__main__":
    main()

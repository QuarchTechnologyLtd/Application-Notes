#!/usr/bin/env python
'''
This example demonstrates post-processing calculation of a standard QPS output CSV file, to calculate 
worst case active power consumption, using a user specified averaging window

########### VERSION HISTORY ###########

07/09/2021 - Andy Norrie     - First Version
20/10/2021 - Andy Norrie     - Significant speed increase by avoiding summing the deque
28/10/2021 - Andy Norrie     - Added additional parameter options and cross-checks


########### INSTRUCTIONS ###########

1- Export a trace from QPS or similar in standard CSV format
2- Specify the path of the file in the script and run it

####################################
'''


import os, time
import logging
import quarchpy
from quarchpy.device import *
from collections import deque
from datetime import datetime

'''
Main function, containing the example code to execute
'''
def main():

    # Enable logging
    logging.basicConfig (filename="app.log", filemode='w', level=logging.DEBUG)

    # Required min version for this application note
    quarchpy.requiredQuarchpyVersion ("2.0.20")
        
    # Display title text
    print ("\n################################################################################\n")
    print ("\n                           QUARCH TECHNOLOGY                                  \n\n")
    print ("                        Power Data post-processing                                  ")
    print ("\n################################################################################\n")    
    print ("\n\n")

    ######################################################
    # Specify the file to process
    ######################################################

    data_path="test_data.csv"

    ######################################################
    # Run the averaging process
    ######################################################
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("Start Time =", current_time)
    
    # Request the worst case 1S average across the trace.  Time specified in same units as the CSV recording (nS)
    print ("Processing CSV file...")
    worst_case = active_power_calc (data_path, col_name="5V power uW", window=1000000000, expected_sample_time=4096000)
    print ("Active power over window: " + str(worst_case) + "uW")
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("End Time =", current_time)

    print ("ALL DONE!")

'''
Reads the CSV and calculated a single worst case value for any window of the specified length
Return value is in the same units as the colum data. Window time is in the same unit as the time column
Assumes the first column is the time data

data_path = The path of the CSV file to read
col_name = The name of the column containing the data to process
window = The time span of the averaging window in the same units as the CSV time column
csv_delimiter = The delimiter character used in the CSV
max_calc_time = Optional value for the end time, if you you do not wish to process the whole file
expected_sample_time = Optional value for the expected sample time of the file.  If set then the script will error if it does not match the measured value
'''
def active_power_calc (data_path, col_name="5V power uW", window=1000000000, csv_delimiter=",",max_calc_time=-1,expected_sample_time=-1):
    
    worst_case = 0    
    sum_value = 0
    debug_counter = 0
    samples_processed = 0
    stop_at_sample = 0        
    
    # Open the file
    file = open (data_path, "r")
    
    # Read the column header, which must contain the specified column name
    data_line = file.readline ()
    headers = data_line.split (csv_delimiter)
    if col_name not in headers:
        # Quote out the column name, and try again
        col_name = "\"" + col_name + "\""        
        if col_name not in headers:
            raise ValueError ("File does not contain the specified column name")
    header_pos =   headers.index(col_name)  
    
    # May be blank line(s) between the header and the data, so skip these
    data_line = ""
    while (len(data_line) == 0):
        data_line = data_line = file.readline ()
        data_line = data_line.strip()
        
    # Get the time from the first 2 lines to calculate the step between samples
    data_line2 = file.readline ()
    time1 = int(data_line.split(csv_delimiter)[0])
    time2 = int(data_line2.split(csv_delimiter)[0])
    time_step = time2 - time1
    
    # Check the sample time is what we expect (if it is specified by the user)
    if (expected_sample_time != -1):
        if (expected_sample_time != time_step):
            raise ValueError ("Calculated sample time from the file does not match the specified value")
    
    # Calculate the window size to the nearest number of samples
    window_samples = int(window / time_step)     
    if (window_samples == 0):
        raise ValueError ("Window size of 0 stripes calculated, check your window parameter")
    window_sample_data = deque(maxlen = window_samples)
    
    # If a processing time limit is specified, prepare for it
    if (max_calc_time != -1):
        stop_at_sample = max_calc_time / time_step
        if (max_calc_time < window):
            raise ValueError ("Window size is greater than the data to process")
    
    # Deal with unusual cases that window is 2 samples or less
    value1 = (int(data_line.split(csv_delimiter)[header_pos]))
    value2 = (int(data_line2.split(csv_delimiter)[header_pos]))
    if (window_samples == 2):
        worst_case = (value1 + value2)
    elif (window_samples == 1):
        worst_case = Value1        
        if (value2 > worst_case):
            worst_case = value2
    # Otherwise push the samples onto the window queue and track the total
    else:
        window_sample_data.appendleft (value1)
        window_sample_data.appendleft (value2)  
        sum_value = value1 + value2
    
    # Loop until the file is complete   
    data_line = data_line = file.readline ()
    while (data_line is not None):  
        samples_processed = samples_processed + 1
        window_len = len(window_sample_data)

        # If the sample window is full, we have to pop the oldest value now
        # We also subtract this from the sum of all points (this avoids summing the whole window every cycle)
        if (window_len == window_samples):            
            sum_value = sum_value - window_sample_data.pop()
    
        # Read the next data element
        value1 = int(data_line.split (csv_delimiter)[header_pos])
        # Add it to the window data
        window_sample_data.appendleft (value1)
        sum_value = sum_value + value1
        
        # Only calculate worst case if the window is filled (skips data at start)
        if (window_len == window_samples):
            if (sum_value > worst_case):
                worst_case = sum_value                  

        # Read the next line in, exit if no data
        data_line = file.readline ()
        if (data_line == ''):
            break      

        # If user has specified a stop time, exit when it is reached
        if (stop_at_sample != 0):
            if (samples_processed >= stop_at_sample):
                break
            
    # Show the samples processed
    print ("Samples Processed: " + str(samples_processed))
    recording_time = samples_processed * time_step
    print ("Processed Time: " + str(recording_time))
    # If max time is specified, check we had enough data to meet it
    if (max_calc_time != -1):
        if (recording_time < max_calc_time):
            print ("ERROR - Source data is shorter that the requested processing time!")
        
    # Calculate the average as the final operation
    return worst_case / window_samples
        

if __name__=="__main__":
    main()

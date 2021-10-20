#!/usr/bin/env python
'''
This example demonstrates post-processing calculation of a standard QPS output CSV file, to calculate 
worst case active power consumption, using a user specified averaging window

########### VERSION HISTORY ###########

07/09/2021 - Andy Norrie     - First Version

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
    
    # Request the worst case 1 second average across the trace.  Time specified in same units as the CSV recording (nS)
    print ("Processing CSV file...")
    worst_case = active_power_calc (data_path, col_name="5V power uW", window=1000000000)
    print ("Active power over window: " + str(worst_case) + "uW")

    print ("ALL DONE!")

'''
Reads the CSV and calculated a single worst case value for any window of the specified length
Return value is in the same units as the colum data. Window time is in the same unit as the time column
Assumes the first column is the time data
'''
def active_power_calc (data_path, col_name="5V power uW", window=1000000000, csv_delimiter=","):
    
    worst_case = 0    
    sum_value = 0
    
    # Quote out the column name, as in the csv
    col_name = "\"" + col_name + "\""
    
    # Open the file
    file = open (data_path, "r")
    
    # Read the column header, which must contain the specified column name
    data_line = file.readline ()
    headers = data_line.split (csv_delimiter)
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
    
    # Calculate the window size to the nearest number of samples
    window_samples = int(window / time_step)     
    if (window_samples == 0):
        raise ValueError ("Window size of 0 stripes calculated, check your window parameter")
    window_sample_data = deque(maxlen = window_samples)
    
    # Deal with unusual cases that window is 2 samples or less
    value1 = (int(data_line.split(csv_delimiter)[header_pos]))
    value2 = (int(data_line2.split(csv_delimiter)[header_pos]))
    if (window_samples == 2):
        worst_case = ((value1 + value2) / 2)
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

        # If the sample window is full, we have to pop the oldest value now
        # We also subtract this from the sum of all points (this avoids summing the whole window every cycle)
        if (len(window_sample_data) == window_samples):            
            sum_value = sum_value - window_sample_data.pop()
    
        # Read the next data element
        value1 = int(data_line.split (csv_delimiter)[header_pos])
        # Add it to the window data
        window_sample_data.appendleft (value1)
        sum_value = sum_value + value1
                
        # Sum the values in the queue and track the worst case average       
        window_average = sum_value / len(window_sample_data)
        if (window_average > worst_case):
            worst_case = window_average                   

        # Read the next line in       
        data_line = file.readline ()
        if (data_line == ''):
            break                
            
    return worst_case
        

if __name__=="__main__":
    main()

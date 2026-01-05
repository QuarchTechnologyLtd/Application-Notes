#!/usr/bin/env python
'''
This example demonstrates basic automation with QIS and post processing of raw data after recording.
We will record at a high rate and post process down to a lower rate, ending with 100uS and 500uS sample rates

########### VERSION HISTORY ###########

03/10/2019 - Andy Norrie     - First Version

########### INSTRUCTIONS ###########

1- Connect a Quarch power module to your PC via USB or LAN and power it on
2- Ensure quarcypy is installed
3- Set the text ID of the PPM you want to connect to in myDeviceID


####################################
'''


import os

import pandas as pd
# Timing to check how long it takes to end the stream
from intel_custom import HdStreamer
from quarchpy.device import *

# Path where stream will be saved to (defaults to current script path)
streamPath = os.path.dirname(os.path.realpath(__file__))

'''
Main function, containing the example code to execute
'''
def main():


    counter = 0
    baseline_file_name = "baseline_file_v3"
    workload_file_name = "workload_file_v3"
    run_baseline = True

    while counter < 10:
        # NOTE - Using only Python and starting the drive format and drive_prep.ini from in here
        # os.system("nvme format -lbaf 0 -ses=1 /dev/nvme0n1 -t 999999999 &> formatOutput.txt")
        os.system("fio drive_prep.ini --output=drive_prep_results")

        # FIO command to be run - Started after stream is started
        fio_command = "fio rd_qd_256_128k_1w.ini.ini --output-format=json+"
        # fio_command = "fio fioTest.ini --output-format=json+"

        # CHANGE VARIABLE TO YOUR DEVICE
        myDeviceID = "TCP:192.168.1.215"
        myQuarchDevice = getQuarchDevice(myDeviceID)
        # Convert the base device to a power device class
        myPpmDevice = quarchPPM(myQuarchDevice)

        # Prints out connected module information
        print ("MODULE CONNECTED: \n" + myPpmDevice.sendCommand ("*idn?"))

        print ("-Waiting for drive to be ready")

        # CHANGE TO REQUIRED DRIVE VOLTAGE
        drive_voltage = "3V3"
        myPpmDevice.sendCommand("config:output:mode:" + drive_voltage)

        # (OPTIONAL) Wait for device to power up and become ready (you can also start your workloads here if needed)
        # time.sleep(5)

        ######################################################
        # Now we set up the PPM streaming parameters
        ######################################################

        print ("-Setting up module record parameters")
        # Sets for a manual record trigger, so we can start the stream from the script
        msg = myPpmDevice.sendCommand("record:trigger:mode manual")
        if (msg != "OK"):
            print ("Failed to set trigger mode: " + msg)
        # Set the averaging rate to the module to 16 (64uS) as the closest to 100uS
        msg = myPpmDevice.sendCommand ("record:averaging 16")
        if (msg != "OK"):
            print ("Failed to set hardware averaging: " + msg)
        else:
            print ("Averaging: " + myPpmDevice.sendCommand ("record:averaging?"))

        ######################################################
        # Here we set the output paths and begin streaming
        # data is held in RAM until the stream is complete.
        # This reduces processing overhead for other tasks running
        ######################################################


        if run_baseline:
            # Append baseline output file to fio command
            fio_command += " --output=" + baseline_file_name + str(counter)
            # run fio command
            os.system(fio_command)
            # Swap flag to allow workload run
            run_baseline = False

        else:
            # append workload output file to fio command
            fio_command += " --output=" + workload_file_name + str(counter)

            print("-Recording data...")
            # Start a stream, using the local folder of the script and a time-stamp file name in this example
            fileName = "RawData_64us_raw_data_run2_" + str(counter) + ".csv"
            fileName100 = "RawData_100us_resampled_run2_" + str(counter) + ".csv"
            outputPath = streamPath + "/" + fileName
            outputPath100 = streamPath + "/" + fileName100
            # Use the streamer class to stream for a set period of time, outputing to CSV
            MyStream = HdStreamer(myPpmDevice)

            streamTime = 915
            MyStream.start_stream(int(streamTime), streamPath + "/" + fileName, fio_command)

            counter += 1
            # swap flag back to baseline
            run_baseline = True

            ######################################################
            # Finally we can post process the data and resample as
            # required. We're using 'pandas' which is very common
            # for data processing of this type
            ######################################################

            # Read the raw power file in that we just created above
            print ("-Reading into Pandas")
            raw_data = pd.read_csv(outputPath, sep=',', index_col=0)
            # Convert the simple uS integer index to the correct format for resampling
            raw_data.index = pd.to_timedelta(raw_data.index, unit='us')
            # Resample to your required rate (100uS here)
            print ("-Resampling data")
            raw_data = raw_data.resample('100us').mean()
            # Convert the index back to the same form we read in from
            raw_data.reset_index(level=0, inplace=True)
            raw_data["Time us"] = pd.to_numeric(raw_data["Time us"], downcast='integer')/1000
            # Write to new CSV file
            print ("-Writing new CSV")
            raw_data.to_csv (outputPath100, sep=',', encoding='utf-8', index=False)

        # Close connection to the module now we're done with it.
        print("-Closing module")
        myPpmDevice.closeConnection()

        print ("ALL DONE!")

'''
Function to check the output state of the module and prompt to select an output mode if not set already
'''
def setupPowerOutput (myModule):
    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    if "DISABLED" in myModule.sendCommand("config:output Mode?"):
        try:
            drive_voltage = raw_input("\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"
        except NameError:
            drive_voltage = input("\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3, 5V]: ") or "3V3" or "5V"

        myModule.sendCommand("config:output:mode:"+ drive_voltage)
    
    # Check the state of the module and power up if necessary
    powerState = myModule.sendCommand ("run power?")
    # If outputs are off
    if "OFF" in powerState:
        # Power Up
        print ("\n Turning the outputs on:"), myModule.sendCommand ("run:power up"), "!"


if __name__=="__main__":
    main()

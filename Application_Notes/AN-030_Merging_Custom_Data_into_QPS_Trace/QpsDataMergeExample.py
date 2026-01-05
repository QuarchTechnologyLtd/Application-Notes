"""
AN-030 - Application note demonstrating merging of custom data into a QPS trace

This example is based on our blog: analysing the energy and water consumption of a dishwasher.
This example pulls in custom user data from another source (a water meter in this case) and creates new channels in QPS

It them imports the data into those channels.  Note that the files supplied here will import volume/flow data into
any QPS trace that is at least 10 seconds long.  You can use this as a tool, pick your own qps streams and edit the csv
file or provide your own.

########### VERSION HISTORY ###########

23/04/2024 - Andy Norrie    - First Version
10/12/2024 - Graham Seed    - Use of "$stream import" command to speedup loading CSV data
23/12/2024 - Stuart Boon    - Making the script more generic and providing a qps stream and csv file

########### REQUIREMENTS ##############

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on Windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/
5- Java 8, with JaxaFX
    https://quarch.com/support/faqs/java/

########### INSTRUCTIONS ##############

1- Run the script and follow the instructions on screen.
2- Select your trace when prompted and choose if you want to make a copy to add the data to or add to the original file
3- Select the csv data to add
4- Look at the QPS main chart with the newly added data.
    Try hiding all channels except the newly added ones to see them clearly.
5- End the script and look through the code and comment for a better understandin of how it works.

#######################################
"""

# Import Libs
import time
import datetime
import shutil
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Import QPS functions
from quarchpy.qps import closeQps
from quarchpy import qpsInterface, requiredQuarchpyVersion,isQpsRunning, startLocalQps


def main():
    # If required you can enable python logging, quarchpy supports this and your log file
    # will show the process of scanning devices and sending the commands.  Just comment out
    # the line below.  This can be useful to send to quarch if you encounter errors
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    print("\n\nQuarch application note example: AN-030")
    print("---------------------------------------\n\n")

    # This is the file containing the user data that we will merge into the trace
    # Version 2.1.24 or higher expected for this application note
    requiredQuarchpyVersion("2.3.0")

    #Start QPS if it is not already running, Do this first to allow plenty start up time.
    if not isQpsRunning():
        startLocalQps()
        time.sleep(1)

    # Ask the user to select the QPS recording to open. This is the one that we will merge the data into
    root = Tk()
    root.withdraw()
    print("Please open the recording.")
    file_path = askopenfilename(title="Open the recording",filetypes=(("QPS files", "*.qps"),))
    if input('This recording file will be overwritten by default.'
             '\n Would you like to make a copy? (y/n): ').lower().strip() == 'y':
        file_path=copy_recording_folder_add_timestamp(file_path)
    merge_filename = askopenfilename(title="Open csv file",filetypes=(("csv files","*.csv"),))

    # Connect to local QPS
    myQPS = qpsInterface()
    # Open the archived recording
    open_rec = myQPS.open_recording(file_path=file_path)
    print("Open recording response: " + open_rec)

    # Create new channels to for water input, measured in L (for liters) and allowing auto unit scaling (milli/micro)
    use_prefix = 'No'

    # Create the new channels.  These should be unique names.  The 'names' here are Rate and Total.
    # The 'axes' that the data will be added to are the 'flow' and 'volume' and the units for each of the axes is given.
    # You can add multiple unique named channels to an axis group but only if they have the same units of measure.
    print("Adding 2 user channels")
    cmd_result = myQPS.sendCmdVerbose("$create channel " + 'Rate' + " " + 'Flow' + " " + 'mL/s' + " " + use_prefix)
    print("Creation of channel Rate / Flow: " + cmd_result)
    cmd_result = myQPS.sendCmdVerbose("$create channel " + 'Total' + " " + 'Volume' + " " + 'L' + " " + use_prefix)
    print("Creation of channel Total / Volume: " + cmd_result)

    # Our data to merge comes from a water meter, this produces a digital pulse for each unit of water.
    # The data has already been formatted into a rate and total amount channel, to be added to the chart
    # If you want to see how we created this, check out 'WaterProcessor.py'
    print("Adding custom data")
    command = "$stream import file=\"" + merge_filename + "\""
    cmd_result = myQPS.sendCmdVerbose(command)
    print("Importing of CSV values: " + cmd_result)

    input("Take a minute to look at the QPS window and the new channels that have been added"
          "\nPress Enter to close QPS and exit the script.")
    input("Are you sure?")
    closeQps() # Close QPS at the end of the script.

    return # END MAIN


def copy_recording_folder_add_timestamp(file_path):
    ''' A utility function to copy the recoding folder and point to the new recording file '''
    # Get the folder containing the selected file
    folder_path = os.path.dirname(file_path)

    # Generate a new folder name with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    new_folder_name = f"{os.path.basename(folder_path)}_{timestamp}"
    parent_dir = os.path.dirname(folder_path) #whats this todo
    destination_folder = os.path.join(parent_dir, new_folder_name)

    # Copy the folder
    shutil.copytree(folder_path, destination_folder)

    # Compute the path to the copied file
    new_file_path = os.path.join(destination_folder, os.path.basename(file_path))
    return new_file_path


# Calling the main() function
if __name__ == "__main__":
    main()

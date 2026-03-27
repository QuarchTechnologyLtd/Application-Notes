"""
AN-012 - Application note demonstrating control of power modules via QIS

Automating via QIS is a lower overhead that running QPS (Quarch Power Studio) in full but still
provides easy access to data for custom processing.  This example uses quarchpy functions to 
stream data from a quarch power module and dump it into a CSV file.

In this example we find and connect to an instrument.  We then record a short period of data
to file in CSV format.  The stream process is repeated twice, at different averaging rates,
so you can see the difference in file size and understand how to capture multiple streams in series.

module.startStream() is non-blocking, so you can continue to run your own commands/scripts
while the stream is recording in the background.  You can also connect to multiple modules
simultaneously and start them streaming in parallel, each to a different file, with multiple
calls to module1.startStream(), module2.startStream(), etc.

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

1. Connect a PPM/PAM device via USB or LAN and power it up
2. Run the script and follow any instructions on the terminal

####################################
"""


# Import other libraries used in the examples
import logging
import quarchpy
from quarchpy.device import *
from quarchpy.qis import *
from quarchpy.user_interface import visual_sleep

def main():

    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    print ("\n\nQuarch application note example: AN-012")
    print ("---------------------------------------")

    # Validate the version of quarchpy you have installed
    quarchpy.requiredQuarchpyVersion ("2.0.9")

    # Start QIS (if it is already running, skip this step and also avoid closing it at the end)
    # This is just to be helpful as you may want to run against an already loaded instance of QIS
    print ("Checking for QIS...")
    close_qis_at_end_of_test=False
    if not isQisRunning():
        print("Starting QIS")
        startLocalQis()
        close_qis_at_end_of_test=True
    else:
        print("QIS already running. Using this instance.")

    # Connect to the localhost QIS instance and demonstrate a simple command which in this case
    # returns the QIS version string
    my_qis = QisInterface()
    print ("QIS Version: " + my_qis.sendCommand('$version')+"\n\n")

    # Use the module selection helper dialog which prompts the user to select a module to talk to.
    # We can supply additional options to the dialog, such as 'quit' (which we can handle), the others
    # are handled internally to give additional options (rescanning after you remember to turn the power on to the
    # device, for example!)
    my_device_id = my_qis.GetQisModuleSelection(additionalOptions=['Rescan', 'All Con Types', 'Ip Scan','Quit'])
    # Exit cleanly on quit request
    if my_device_id.lower()=="quit":
        print("User Selected Quit.")
        if close_qis_at_end_of_test:
            closeQis()
        return

    # The return from the module selection is a device ID string that we can use to connect to.
    # If you know the name of the module you would like to talk to, then you can skip module selection and
    # hardcode the string using the serial number or IP address
    print ("Module Selected: " + my_device_id + "\n")
    # my_device_id = "USB:QTL1999-05-005"
    # my_device_id = "TCP:192168.1.25"

    # Connect to the module, we request a QIS type connection
    my_quarch_device = getQuarchDevice(my_device_id, ConType = "QIS")
   
    # Convert the base device class to a power device, which provides additional controls, such as data streaming
    my_power_device = quarchPPM(my_quarch_device)
    
    # Now we will run an example function to capture stream data from this devices
    simple_stream_example (my_power_device)

    if close_qis_at_end_of_test:
        closeQis()

def simple_stream_example(module: quarchPPM) -> None:
    """
    This example streams measurement data to file, by default in the same folder as the script

    Args:
        module:
            The previously connected Quarch device to stream data from

    Returns:
        None

    """
    # Prints out connected module information
    print ("Running QIS SIMPLE STREAM Example")
    print ("Module Name: " + module.sendCommand ("hello?"))

    # Go back to default settings, incase this instrument was set to a different state
    print ("Ensure we are in the default state: " + module.sendCommand ("config:default state"))

    # Setup must be done before starting the stream.  Here we choose our resampling rate
    print("Setting QIS resampling to 1KHz / 1mS per sample: ")
    print (module.streamResampleMode("1ms"))

    # In this example we write to a fixed path for simplicity
    print ("\nStarting Recording!")
    module.startStream('Stream-1ms.csv')

    # Delay for a few seconds while the stream is running.  You can also continue
    # to run your own commands/scripts here while the stream is recording in the background  
    print ("\nWait a while, for a period of data to record\n")
    visual_sleep(10, title="1mS Stream test")    # Gives you a visual indication of the delay time
    
    # Check the stream status, so we know if anything went wrong during the capture period
    # This is not essential, but some tests may need you to ensure that all data across the
    # full stream period has been captured correctly
    print ("Checking the stream is running (all data has been captured)")
    stream_status = module.streamRunningStatus()
    if "running" not in stream_status:
            print("\tStream terminated early: " + stream_status)
    else:
        print("\tStream ran correctly across the full test")

    # Stop the stream.  This function is blocking and will wait until all remaining data has
    # been downloaded from the module. This may take a couple of seconds.
    print ("\nStopping the stream...")
    module.stopStream()

    # Now we will repeat and run a second stream at a different resampling rate.
    # You can run as many streams in sequence as you like.
    module.streamResampleMode("100ms")
    module.startStream('Stream-100ms.csv')
    visual_sleep(10, title="100mS Stream test")
    module.stopStream()

    print ("\nQIS SIMPLE STREAM Example - Complete!\n\n")

# Calling the main() function
if __name__=="__main__":
    main()

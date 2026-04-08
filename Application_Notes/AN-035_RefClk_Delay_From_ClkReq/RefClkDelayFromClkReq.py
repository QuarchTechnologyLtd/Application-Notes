"""
This application note is to demonstrate RefClk coming active after ClkReq# has been asserted. This using a triggering breaker
with a loopback connection, and a PAM to verify what is happening. We are aiming to delay RefClk for different lengths of time,
to check whether the device still functions with delays between CLKREQ# and RefClk.

This script will setup the breaker to trigger out from ClKReq#, and after a delay after being triggered, close the RefClk switches.
It is suggested to use a system startup rather than exiting a low power state to drive CLKREQ#, as the breaker will plug when ClkReq# is asserted.
It is best suited to use separate host and control PCs, so that we can record the start-up, when ClkReq# is likely to change.
We output CLKREQ# to trigger out, which is looped back to trigger in, and the trigger in action is to alter the hot plug state - i.e. plug the device.

This was written using a QTL3238 Gen6 x16-0 AIC Breaker, and a QTL3216 Gen6 AIC PAM. As such, the signal names are written for these,
so minor variations might be needed to work with other modules. You will need a breaker that can break CLKREQ# and RefClk, and a PAM that can measure RefClk.

The commands sent to the device are in the format
RUN:POWer UP
The commands are based on SCPI control system, but not all SCPI has been implemented
Commands are not case-sensitive. Most commands will have short forms - e.g. POWer shortens to POW

########### VERSION HISTORY ###########
06/04/2025 -  Andrew S - First Release

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

########### INSTRUCTIONS ###########

1- Install the required items above
2- Connect PCIe Triggering Breaker
3- Connect PCIe PAM that is able to measure RefClk
4- Connect PAM and Quarch Interface Unit with USB to control PC
5- Connect Power cables to PAM and Quarch Interface Unit
6- Run the script and follow the instructions on screen

Section 2.10 of the PCI Express Card Electromechanical Specification. Revision 6 summarises to:
ClkReq# is an optional, active low signal driven low by the add-in card to request RefClk.

PCIe Base Specification Revision 6.3:
Section 5.5.5 states T(L10_REFCLK_ON) is the time between CLKREQ# assertion to RefClk Valid when exiting L1.2

Section 5.5.3.3.1 states for an L1.2 Exit, RefClk must be turned on no earlier than T(L10_REFCLK_ON) minimum time,
                        and may take up to the amount of time allowed according to LTR before becoming valid.
                        T(L10_REFCLK_ON) is minimum of T(POWER_ON).

Section 7.8.3.4 states T_POWER_ON has a default of 10us, and a maximum of (100us * 31) = 31ms.

Section 6.18 Latency Tolerance Reporting (LTR Mechanism) is set by the endpoint (device) to report latency requirement.
                        This is optional, and does not have a default.
                        This states that if a latency requirement is set by the device, this is in the range of
                        1 nanosecond to 34.3 seconds.
"""

import quarchpy
from quarchpy.connection_specific.connection_QPS import QpsInterface
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import scanDevices, userSelectDevice, get_quarch_device, quarchQPS
from quarchpy.qps import isQpsRunning, startLocalQps, GetQpsModuleSelection
from quarchpy.user_interface import *


stream_path = os.path.join(os.getcwd(), "QPS_Traces")

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    #Displays the title as a list
    displayTable("AN-035 Delay RefClk from CLKREQ#", printToConsole=True, align="c")

    print("While the stream is running, CLKREQ# should be asserted. This could be power up, or exiting a sleep state")
    print("This stream will run for 60 seconds")

    #Checks that the customer is on a relatively recent version of Quarchpy
    requiredQuarchpyVersion("2.2.19")

    print("It is suggested for a first test to use 100ms delay. Please select the delay in millseconds")
    #This is a list of delays that the user can select
    delay_list = "1,10,50,100,500,1000"

    #User selects the delays, shown in a table
    delay_selected = listSelection(title="", message="Select the delay between CLKREQ# and RefClk - in milliseconds", selectionList=delay_list, nice=True)

    #Most pins will have a 25ms delay so we will add 25ms onto the delay the user selects
    delay = str(int(delay_selected) + 25)

    #Optional Hardcode - uncomment this, and comment in the lines above if you want to hardcode the delay in ms
    #delay_selected = "125"

    #We need to sample faster than the delay, so at 1ms or 10ms delay we will use a 100us resample rate
    if delay_selected == "1ms" or delay_selected == "10ms":
        resample_rate = "100us"
    else: #With a 50ms or longer delay, we will use a 1ms resample rate
        resample_rate = "1ms"

    #Provides instructions about how to set-up the module
    showDialog(title="", message="Connect the breaker trigger out, to the breaker trigger in with an MCX loopback cable.\n")

    print("Connecting to Breaker...")

    #Scans devices
    device_list = scanDevices()
    #Displays devices along with rescan, quit, all conn types
    module_str = userSelectDevice(device_list, additionalOptions = ["Rescan", "All Conn Types", "Quit"], nice=True)

    #Optional Hardcode - If you know the address of the breaker you want to connect to, uncomment ths, comment in the 2 lines above
    #module_str = "USB::QTL3238-01-001"

    #If user has selected quit, quit and close nicely
    if module_str == "Quit":
        return 0

    #Connect to the breaker
    breaker = get_quarch_device(module_str)

    # Print the device name after the selection to confirm connection
    print("Breaker Name:")
    print(breaker.send_command("hello?"))

    #PAM Connection
    #Start QPS if not already running
    if not isQpsRunning():
        #Launches QPS and creates an interface
        print("Launching QPS")
        my_qps = startLocalQps()
    else:
        #If QPS is already running, connect the running QPS instance to local interface
        my_qps = QpsInterface()

    #Asks user to select the PAM to be used
    pam_id = GetQpsModuleSelection(my_qps)

    # Optional Hardcode - If you know the address of the PAM you want to connect to, uncomment ths, comment in the line above
    #pam_id = "USB::QTL2312-01-477"

    #Upgrade PAM to a quarch device, connected via QPS
    my_quarch_device = get_quarch_device(pam_id, ConType="QPS")

    #Upgrade Quarch Device to QPS Device - adds more features
    pam = quarchQPS(my_quarch_device)

    #Opens connection to PAM
    pam.open_connection()

    #Resamples the PAM via the QIS command stream mode resample
    pam.sendCommand(f"stream mode resample {resample_rate}")

    #Sets breaker to default state
    breaker.send_command("CONFig:DEFault STATE")

    #Power down the breaker
    breaker.send_command("RUN:POWer DOWN")

    #Set trigger out to sideband monitor
    breaker.send_command("TRIGger:OUT:MODE:SIDEband")

    #Sets CLKREQ# to sideband monitor - CLKREQ# is now being outputted over trigger out
    breaker.send_command("TRIGger:MONitor OUT:CLKREQ:DEVICE")

    #When trigger in received (CLKREQ# changing), hot plug will be performed, and after the delay, RefCLk switches will close
    breaker.send_command("TRIGger:IN:MODE:POWER")

    #CLKREQ# is active low so we invert the triggering logic
    breaker.send_command("TRIG:IN:INVERT ON")

    #Source 4 is unused by default, so we will use that for RefClk
    breaker.send_command(f"SOURce:4:DELAY {delay}")

    #Assign signal group RefClk to Source 4 with our assigned delay
    breaker.send_command("SIGnal:REFCLK:SOURce 4")

    #Sleeps to ensure commands are set properly
    time.sleep(1)

    print("Breaker configured")

    #Creates filename with timestamp - QPS recording will be saved here
    file_name = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

    #Sleeps to ensure filepath is made
    time.sleep(1)

    #Start QPS Stream to record in the current working directory, with a timestamped filename
    #This will stream for 60 seconds, but the breaker will remain configured after this time is up
    pam.start_stream(directory=(stream_path + "\\" + file_name), stream_duration="60")

    print("Streaming...")

    #Streams for 60 seconds, so we will sleep for 63 seconds so we don't end the stream early
    visual_sleep(63)

    print("\nStream Completed")

    print(f"\nRecording saved to {stream_path}\\{file_name}")

    print("\nTo verify compliance with the PCIe specification, review the Quarch Power Studio trace. ")
    print("The PCIe specification does not provide a maximum time between CLKREQ# assertion and RefClk becoming valid, leaving it to the device to specify this\n")


    print("PCIe Base Specification Revision 6.3:\n")

    print("Section 5.5.5 states T(L10_REFCLK_ON) is the time between CLKREQ# assertion to RefClk Valid when exiting L1.2\n")

    print("Section 5.5.3.3.1 states for an L1.2 Exit, RefClk must be turned on no earlier than T(L10_REFCLK_ON) minimum time,and may take up to the amount of time allowed according to LTR before becoming valid.")
    print("T(L10_REFCLK_ON) is minimum of T(POWER_ON).\n")

    print("Section 7.8.3.4 states T_POWER_ON has a default of 10us, and a maximum of (100us * 31) = 31ms.\n")

    print("Section 6.18 Latency Tolerance Reporting (LTR Mechanism) is set by the endpoint (device) to report their latency requirement to the root complex.")
    print("This is optional, and does not have a default.")
    print("This states that if a latency requirement is set by the device, this is in the range of1 nanosecond to 34.3 seconds.\n")

    print("There is a range of delays to set between CLKREQ# assertion and RefClk being valid. This is likely greater than most device implemented maximums.")
    print("It is suggested to repeat this test, and adjust the delays.\n")
    return 0

if __name__ == "__main__":
    main()
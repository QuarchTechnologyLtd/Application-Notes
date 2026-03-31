"""
This application note is to demonstrate RefClk coming active after ClkReq has come active. This using a triggering breaker
with a loopback connection, and a PAM to verify what is happening. It is suggested to use the AIC form factor, as this references the
CEM Spec directly.

It is recommended to have a separate host and control PC, so the control PC can record while the host PC boots. This script can be used
without a PAM, and just used to configure the breaker to delay the refclk. If this is desired, comment out PAM sections.

This configures the breaker to have ClkReq as trigger out, and trigger in as the action to power up from, so the module triggers from
ClkReq. This script is aimed towards the Gen6 AIC Breakers, and as such the signal names may change.

This was written using a QTL3238 Gen6 x16-0 AIC Breaker, and a QTL3216 Gen6 AIC PAM. As such, the signal names are written for these,
so minor variations might be needed to work with other modules

Section 2.10 of the PCI Express Card Electromechanical Specification. Revision 6 summarises to:

ClkReq# is an optional, open drain, active low signal driven low by the add-in card to request RefClk.
CLKREQ# is driven low by the card to request the reference clock
Here we are delaying CLKREQ#, and verifying that the device still functions

This script will set a delay of 100ms on the RefClk, and keep all other signals as their default delays

For testing purposes, we are using a test fixture to drive individual GPIO pins

we will drive ClkReq, and will use PAM

Clock generator pin is GPIO 88
ClkReq pin is B12 GPIO 216


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

    requiredQuarchpyVersion("2.2.18")

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
        #Connect the current running QPS instance to local interface
        my_qps = QpsInterface()

    #Asks user to select the PAM to be used
    pam_id = GetQpsModuleSelection(my_qps)

    # Optional Hardcode - If you know the address of the breaker you want to connect to, uncomment ths, comment in the 2 lines above
    #pam_id = "USB::QTL2312-01-477"

    #Upgrade PAM to a quarch device
    my_quarch_device = get_quarch_device(pam_id, ConType="QPS")

    #Upgrade Quarch Device to QPS Device
    pam = quarchQPS(my_quarch_device)

    #Opens connection
    pam.open_connection()


    #Sets breaker to default state
    breaker.send_command("CONFig:DEFault STATE")

    breaker.send_command("RUN:POWer DOWN")

    #Provides instructions about how to setup the module
    #showDialog(title="", message="Connect the breaker trigger out, to the breaker trigger in with a loopback cable")

    print("When the stream is running, power up the host system")

    #Set Trigger out to sideband monitor
    breaker.send_command("TRIGger:OUT:MODE:SIDEband")

    #Sets CLKREQ to sideband monitor - CLKREQ is now being outputted over trigger out
    breaker.send_command("TRIGger:MONitor OUT:CLKREQ:DEVICE")

    #When trigger in received (CLKREQ changing), hot plug will be performed, and 100ms later refclk will be connected
    breaker.send_command("TRIGger:IN:MODE:POWER")

    #Configure RefClk delay to 100ms
    #Source 4 is unused by default
    breaker.send_command("SOURce:4:DELAY 100")

    #Assign signal group RefClk to Source 4 - Source 4 is not a default source
    breaker.send_command("SIGnal:REFCLK:SOURce 4")

    #Resamples to 1ms
    pam.sendCommand("stream mode resample 1ms")

    #Sleeps to ensure commands are set properly
    time.sleep(1)

    #Creates filename with timestamp
    file_name = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

    #Sleeps to ensure filepath is made
    time.sleep(1)

    #Start QPS Stream to record in the current working directory
    #This will stream for 60 seconds, but the breaker will remain configured after this time is up
    pam.start_stream(directory=(stream_path + "\\" + file_name), stream_duration="60")

    #Streams for 60 seconds, enough for a power up or power down on most systems
    visual_sleep(20)


    print("Stream Completed")

    print(f"\nRecording saved to {stream_path}\\{file_name}")

    print("\nRelevant sections of the PCIe CEM Spec Rev6")
    print("Section 2.1 - Reference Clock")
    print("Figure 2-9. CLKREQ# Clock Control Timings")
    print("Section 2.10 - CLKREQ# Signal (Optional)")


    print("Look for the power up event in the QPS trace")
    print("In particular, look for CLKREQ# changing, and 100ms later REFCLK0_LOS changing")
    print("If your device functions after this delay")

    return 0



if __name__ == "__main__":
    main()
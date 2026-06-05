"""Using a QSFP cable tester and a QSFP breaker, we will inject glitches and count the BER"""

import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.user_interface import displayTable


def main():
    displayTable("AN-036 Injecting Glitches with a Cable Tester", printToConsole=True, align="c")

    #Check we are on a recent version of quarchpy
    requiredQuarchpyVersion("2.2.21")

    #Find devices available
    device_list = scanDevices()

    print("Please select the Cable Tester")
    #Takes user input for the cable tester to be used
    cable_tester_str = userSelectDevice(device_list, additionalOptions=["Rescan", "All Conn Types", "Quit"], nice=True)

    #If quit is selected, exit nicely
    if cable_tester_str == "Quit":
        return 0

    #Create a quarch_device
    cable_tester = get_quarch_device(cable_tester_str)
    #Set to default state
    cable_tester.send_command("CONFig:DEFault STATE")

    #Stop any currently running test
    cable_tester.send_command("RUN:STOP")

    #Stop tests from automatically running when cable is plugged in
    cable_tester.send_command("AUTO:ENAble OFF")

    #Print the *idn? string
    print(f"Connected to :\n{cable_tester.send_command('*idn?')}\n")

    print("Please select the QSFP breaker")
    device_list = scanDevices()

    breaker_str = userSelectDevice(device_list, additionalOptions=["Rescan", "All Conn Types", "Quit"])

    if breaker_str == "Quit":
        return 0

    #Create a quarch_device
    breaker = get_quarch_device(breaker_str)
    #Set to default state
    breaker.send_command("CONFig:DEFault STATE")

    print(f"Connected to :\n{breaker.send_command('*idn?')}\n")

    #Before we inject any glitches, Create a 24G link
    cable_tester.send_command("LINK:SPEED 24G")

    #Reset the BERT
    cable_tester.send_command("BERT:TX_0:RESet")



    return 0
if __name__ == "__main__":
    main()
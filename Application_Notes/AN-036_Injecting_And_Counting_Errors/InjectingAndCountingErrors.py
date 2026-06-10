"""Using a QSFP cable tester and a QSFP breaker, we will inject glitches and count the BER"""
import time

import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.user_interface import displayTable


def main():
    displayTable("AN-036 Injecting Glitches with a Cable Tester", printToConsole=True, align="c")

    print("\nInsert the breaker to the A port of the cable tester")
    print("Then insert the cable into to the breaker on the A side, and into the cable tester on the B side\n")


    #Check we are on a recent version of quarchpy
    requiredQuarchpyVersion("2.2.21")

    # #Find devices available
    # device_list = scanDevices()
    #
    # print("Please select the Cable Tester")
    # #Takes user input for the cable tester to be used
    # cable_tester_str = userSelectDevice(device_list, additionalOptions=["Rescan", "All Conn Types", "Quit"], nice=True)
    #
    # #If quit is selected, exit nicely
    # if cable_tester_str == "Quit":
    #     return 0

    cable_tester_str = "USB::QTL2250-01-014"

    #Create a quarch_device
    cable_tester = get_quarch_device(cable_tester_str)
    #Set to default state
    #cable_tester.send_command("CONFig:DEFault STATE")

    #Stop any currently running test
    #cable_tester.send_command("RUN:STOP")

    #Stop tests from automatically running when cable is plugged in
    #cable_tester.send_command("AUTO:ENAble ON")

    #Print the *idn? string
    print(f"Connected to :\n{cable_tester.send_command('*idn?')}\n")

    # print("Please select the QSFP breaker")
    # device_list = scanDevices()
    #
    # breaker_str = userSelectDevice(device_list, additionalOptions=["Rescan", "All Conn Types", "Quit"])
    #
    # if breaker_str == "Quit":
    #     return 0

    #Optional hardcode
    breaker_str = "USB::QTL2171-02-041"

    #Create a quarch_device
    breaker = get_quarch_device(breaker_str)
    #Set to default state
    breaker.send_command("CONFig:DEFault STATE")

    print(f"Connected to :\n{breaker.send_command('*idn?')}\n")

    #Test the link and the cable
    response = cable_tester.send_command("RUN TEST")
    print(f"Run Test: {response}")

    # print("Running initial test")
    # #Poll the device while we are running the initial test
    # response = None
    # while response != "COMPLETE":
    #     #Response will be COMPLETE once the test is complete, and we will exit the loop
    #     response = cable_tester.send_command("RUN:TEST?")

    #Enable glitching on both p and n of TX1
    breaker.send_command("SIGnal:TX1_PL:GLITch:ENAble ON")
    breaker.send_command("SIGnal:TX1_MN:GLITch:ENAble ON")

    #Sleep to ensure commands are set
    time.sleep(1)

    #Reset BERT counters, and enable link a1 BERT test
    cable_tester.send_command("BERT:A3:ENAble ON")

    #Reset the counter before we begin
    cable_tester.send_command("BERT:A3:RESet")

    #List of glitch lengths as sent to the breaker 50ns, 100ns, 1us, 10us, 100us, 1ms, 10ms, 100ms, 1s
    glitch_lengths_breaker = ["50ns 1", "50ns 2", "500ns 2", "5us 2", "50us 2", "500us 2", "5ms 2", "50ms 2", "500ms 2"]
    #Keep the glitch lengths in a more readable format
    actual_glitch_lengths = ["50ns", "100ns", "1us", "10us", "100us", "1ms", "10ms", "100ms", "1s"]

    #Start with smaller ratio (few error bits) and build up
    prbs_ratios = ["65536", "8192", "2048", "1024", "256", "128", "64", "32", "16", "8", "4", "2"]

    # Equivalent of PCIe Gen3, Gen4, and approximately Gen5
    link_speeds = ["8G", "16G", "24G"]


    error_dict = {}

    for link_speed in link_speeds:
        #Create a nested dictionary for link speed
        error_dict[link_speed] = {}
        cable_tester.send_command(f"LINK:SPEED {link_speed}")

        response = None
        #Poll after we change the link speed to check whether its trained
        while response != "TRAINED":
            response = cable_tester.send_command('LINK:A3:STAT?')
            print(response)
            time.sleep(0.1)

        #zip the lists together
        for glitch_length, actual_glitch in zip(glitch_lengths_breaker, actual_glitch_lengths):
            #Set a glitch up
            breaker.send_command(f"GLITch:SETup {glitch_length}")

            #Sleep to ensure glitch is set
            time.sleep(1)

            errors_before = cable_tester.send_command("BERT:A3:ERRors?")
            rate_before = cable_tester.send_command("BERT:A3:RATE?")

            # Run glitch once
            breaker.send_command("RUN:GLITch ONCE")

            time.sleep(1.2) #Sleep for just longer than the longest glitch

            errors_after = None
            final_error_count = 0
            attempts = 0

            while attempts < 5: #Only try 5 times
                # Query the BERT Count
                errors_after = cable_tester.send_command("BERT:A3:ERRors?")
                rate_after = cable_tester.send_command("BERT:A3:RATE?")

                errors = int(errors_after) - int(errors_before)

                #If no errors_after have been detected, run another glitch
                if errors == 0:
                    breaker.send_command("RUN:GLITch ONCE")
                    attempts += 1
                    continue
                #We have some errors_after, print and exit the loop
                if errors > 1:
                    print(f"A {actual_glitch} glitch on one differential pair at {link_speed} link caused {errors} errors")
                    final_error_count = errors
                    break

            #Store the error in our nested dictionary
            error_dict[link_speed][actual_glitch] = final_error_count

            #Reset the BERT counter before we increase the glitch
            cable_tester.send_command("BERT:A3:RESet")

            time.sleep(0.5)

        #After the time - length glitches have been ran through, run through some PRBS glitches
        for prbs_ratio in prbs_ratios:
            # Set a glitch up
            breaker.send_command(f"GLITch:PRBS {prbs_ratio}")

            # Sleep to ensure glitch is set
            time.sleep(1)

            errors_before = cable_tester.send_command("BERT:A3:ERRors?")
            rate_before = cable_tester.send_command("BERT:A3:RATE?")

            # Run glitch once
            breaker.send_command("RUN:GLITch PRBS")

            #Sleep for 1 second
            time.sleep(1)

            #Stop the glitch
            breaker.send_command("RUN:GLITch STOP")

            errors_after = None
            final_error_count = 0
            attempts = 0

            while attempts < 5:  # Only try 5 times
                # Query the BERT Count
                errors_after = cable_tester.send_command("BERT:A3:ERRors?")
                #Get the BERT rate
                rate_after = cable_tester.send_command("BERT:A3:RATE?")
                #Calculate the errors caused by the glitch alone
                errors = int(errors_after) - int(errors_before)

                # If no errors_after have been detected, run another glitch
                if errors == 0:
                    breaker.send_command("RUN:GLITch PRBS")
                    #Increment the attempts so we don't run too many times
                    attempts += 1
                    continue
                # We have some errors introduced by the glitch, store, print and exit the loop
                if errors > 1:
                    print(
                        f"A PRBS Ratio {prbs_ratios} glitch on one differential pair at {link_speed} link caused {errors} errors")
                    final_error_count = errors
                    break

            # Store the error in our nested dictionary
            error_dict[link_speed][prbs_ratio] = final_error_count

            # Reset the BERT counter before we increase the glitch
            cable_tester.send_command("BERT:A3:RESet")

            time.sleep(0.5)

    print(f"Error count: {error_dict}")

    time.sleep(1)
    print("exiting")

    return 0
if __name__ == "__main__":
    main()
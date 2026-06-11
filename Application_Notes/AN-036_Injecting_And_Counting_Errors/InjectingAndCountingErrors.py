"""Using a QSFP cable tester and a QSFP breaker, we will inject glitches and count the BER

We assume the modules are in a cold state where they have just been plugged in, with no cable training
"""
import time

import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.user_interface import displayTable
import pandas as pd


def main():
    displayTable("AN-036 Injecting Glitches with a Cable Tester", printToConsole=True, align="c")

    print("\nInsert the breaker to the A port of the cable tester")
    print("Then insert the cable into to the breaker on the A side, and into the cable tester on the B side\n")


    #Check we are on a recent version of quarchpy
    requiredQuarchpyVersion("2.2.21")

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
    #Print the *idn? string
    print(f"Connected to :\n{cable_tester.send_command('*idn?')}\n")
    print(f"Cable tester *tst?: {cable_tester.send_command('*tst?')}\n")

    cable_tester.send_command("AUTO:EEDECODE:ENA OFF")
    cable_tester.send_command("AUTO:EYEHEIGHT:ENA OFF")
    cable_tester.send_command("AUTO:EYESCAN:ENA OFF")

    #Test the link and the cable
    response = cable_tester.send_command("RUN TEST")
    if response == "FAIL: 0x61 -Unit is busy, wait then try again":
        cable_tester.send_command("RUN:STOP")
        cable_tester.send_command("RUN:TEST")

    print("Training and mapping cable")
    #Poll the device while we are running the initial test
    response = None
    while response != "TRAINED":
        #Response will be COMPLETE once the test is complete, and we will exit the loop
        response = cable_tester.send_command("LINK:A3:STATus?")

    #Enable glitching on both p and n of TX1
    breaker.send_command("SIGnal:TX1_PL:GLITch:ENAble ON")
    breaker.send_command("SIGnal:TX1_MN:GLITch:ENAble ON")

    #Sleep to ensure commands are set
    time.sleep(1)

    #Reset BERT counters, and enable link a1 BERT test
    cable_tester.send_command("BERT:A3:ENAble ON")

    #Reset the counter before we begin
    cable_tester.send_command("BERT:A3:RESet")

    #List of glitch lengths as sent to the breaker 50ns, 100ns, 1us, 10us, 100us, 1ms, 10ms, 100ms, 1s, and PRBS ratios
    #Include the keyword to properly set the glitch
    glitch_lengths_breaker = ["SETup 50ns 1", "SETup 50ns 2", "SETup 500ns 2", "SETup 5us 2", "SETup 50us 2", "SETup 500us 2", "SETup 5ms 2", "SETup 50ms 2", "SETup 500ms 2", "PRBS 32", "PRBS 16", "PRBS 8", "PRBS 2"]
    #Number of timed glitches - timed glitches and PRBS glitches are run in different ways
    timed_glitch_count = 8
    #Keep the glitches in a more readable format used for printing to user
    actual_glitch_lengths = ["50ns", "100ns", "1us", "10us", "100us", "1ms", "10ms", "100ms", "1s", "PRBS Ratio 1:32", "PRBS Ratio 1:16", "PRBS Ratio 1:8", "PRBS Ratio 1:2"]

    # Equivalent of PCIe Gen4.5 (fastest we can run), Gen4 and Gen3
    link_speeds = ["24G", "16G", "8G"]

    error_dict = {}
    time_dict = {}

    for link_speed in link_speeds:
        #Create a nested dictionary for link speed
        error_dict[link_speed] = {}
        #Create a time dictionary so we can calculate BER
        time_dict[link_speed] = {}

        #Stop any glitches that may still be present
        breaker.send_command("RUN:GLITch STOP")

        #Set the link speed
        cable_tester.send_command(f"LINK:SPEED {link_speed}")
        #Reset the counter
        cable_tester.send_command("RUN:TEST")

        #Wait for the link to train to the new level, with 5 attempts
        attempts = 0
        #Poll after we change the link speed to check whether the cable has passed initial tests
        while attempts < 5:
            response = cable_tester.send_command("RUN:TEST?")
            # Sleep so we don't poll too fast
            time.sleep(1)
            #If we have passed the test
            if response == "PASS":
                break
            else:
                attempts += 1
                continue

        print(f"Link speed successfully set to: {cable_tester.send_command(f'LINK:SPEED?')}")
        time.sleep(2)

        #index i to determine timed glitch or PRBS glitch
        #Glitch length is in the format that is sent to the breaker, actual_glitch is in a nicer format which is printed to the user
        for i, (glitch_length, actual_glitch) in enumerate(zip(glitch_lengths_breaker, actual_glitch_lengths)):
            #Get a timestamp so we can calculate BER
            start_time = time.time()

            #Set a glitch up
            breaker.send_command(f"GLITch:{glitch_length}")

            #Reset the error counter
            cable_tester.send_command("BERT:A3:RESet")

            #Sleep to ensure commands are set
            time.sleep(2)

            #Get the error count 1 second after it was reset - we will skip measurement if unstable link
            errors_before = cable_tester.send_command("BERT:A3:ERRors?")
            if int(errors_before) > 0:
                print(f"Unstable link, waiting then skipping glitch")
                #Stop any glitch
                breaker.send_command("RUN:GLITch STOP")
                #Sleep for 2 seconds to hopefully stabilise the link
                time.sleep(2)
                continue

            #If this is a low index, this is a timed glitch, not a PRBS
            if i <= timed_glitch_count:
                breaker.send_command("RUN:GLITch ONCE")
                time.sleep(2)  # Sleep for longer than the longest glitch

            #If this is a high index, this is a PRBS glitch
            if i >= (timed_glitch_count+1):
                #Run PRBS glitch for 5 seconds, then stop the PRBS glitch
                breaker.send_command("RUN:GLITch PRBS")
                time.sleep(5)
                breaker.send_command("RUN:GLITch STOP")

            final_error_count = 0
            attempts = 0

            while attempts < 3: #Only try 3 times so we don't get stuck
                # Query the error count
                errors_after = cable_tester.send_command("BERT:A3:ERRors?")

                #Get the delta of errors caused by the glitch
                errors = int(errors_after) - int(errors_before)

                #Assuming we have some errors, display the effect of the glitch
                if errors > 0:
                    print(f"\nA {actual_glitch} glitch on one differential pair at {link_speed} link caused {errors} errors")
                    final_error_count = errors
                    break

                #If no errors  have been detected, run another glitch
                else:
                    #If this is the third attempt, print message, and exit the loop
                    if attempts == 2:
                        print(f"Glitch {actual_glitch} caused no detectable errors after 3 attempts")
                        break
                    #We have some more attempts
                    else:
                        print(f"No errors detected for {actual_glitch}, retrying")
                        #Attempting glitch again
                        # If this is a low index, this is a timed glitch
                        if i <= timed_glitch_count:
                            breaker.send_command("RUN:GLITch ONCE")
                            time.sleep(1.2)  # Sleep for just longer than the longest glitch

                        # If this is a high index, this is a PRBS glitch
                        if i >= (timed_glitch_count+1):
                            # Run PRBS glitch for a second, then stop the PRBS glitch
                            breaker.send_command("RUN:GLITch PRBS")
                            time.sleep(1)
                            breaker.send_command("RUN:GLITch STOP")

                        #Increment the counters
                        attempts += 1
                        continue

            #Get a timestamp after the glitch has finished
            end_time = time.time()
            #Calculate the test duration
            test_duration = end_time - start_time
            #Store the time duration so we can calculate BER
            time_dict[link_speed][actual_glitch] = test_duration

            #Store the error in our nested dictionary
            error_dict[link_speed][actual_glitch] = final_error_count

            #Reset the BERT counter before we increase the glitch
            cable_tester.send_command("BERT:A3:RESet")

            time.sleep(0.5)
        print(f"Glitches at {link_speed} link complete")

    #Store both nested lists in a dataframe
    df_errors = pd.DataFrame(error_dict)
    df_times = pd.DataFrame(time_dict)

    #Get column names
    original_speeds = list(df_errors.columns)
    #For each column name, merge in the timestamp labelled as e.g. 24G_Time(s)
    for speed in original_speeds:
        df_errors[f"{speed}_Time(s)"] = df_times[speed].round(2)

    #Make the first column (glitch_length) the index
    df_errors.index.name = "Glitch_Length"
    #Give it a filename
    filename = "glitch_test_results.csv"
    #Save into a CSV
    df_errors.to_csv(filename)

    #Set back to default state
    breaker.send_command("CONFig:DEFault STATE")
    cable_tester.send_command("CONFig:DEFault STATE")

    #Close the module connections
    breaker.close_connection()
    cable_tester.close_connection()

    print("Test complete, exiting script")

    return 0

if __name__ == "__main__":
    main()
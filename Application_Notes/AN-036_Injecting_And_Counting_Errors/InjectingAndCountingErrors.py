"""Using a QSFP cable tester and a QSFP breaker, we will inject glitches and count the BER
We loop over link speed, number of lanes glitched, and glitched length.

Steps:
Change the cable mapping dependent on your cable used, and optionally reduce the link speed if this is too great for the cable
Connect the cable and the breaker to the cable tester, then connect the breaker and cable tester via USB or LAN to this PC
Run the script, which will generate a CSV with the data.
"""
import time

import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.user_interface import displayTable, visual_sleep
import pandas as pd

#Tester map - Change this for different cables, and whether the breaker is plugged into A side or B side
lanes_to_test = [
    {"tx_pair": "TX1", "tester_port": "B1"},
    {"tx_pair": "TX2", "tester_port": "B3"},
    {"tx_pair": "TX3", "tester_port": "B0"},
    {"tx_pair": "TX4", "tester_port": "B2"}]

# Length of time to sleep for, and length of time for PRBS - If this is too short this can misrepresent the true number of errors so suggested to keep at 5
test_length = 10
#Number of tries to get the error count from the glitch
attempts_allowed = 5

# List of glitch lengths
glitch_lengths_breaker = ["SETup 50ns 2", "SETup 500ns 2", "SETup 5us 2", "SETup 50us 2", "SETup 500us 2", "SETup 5ms 2", "SETup 50ms 2", "SETup 500ms 2", "PRBS 32", "PRBS 16", "PRBS 8", "PRBS 2"]
# More readable format of glitch lengths - with these values, we'd expect error count to increase at 10x between each glitch
actual_glitch_lengths = ["100ns", "1us", "10us", "100us", "1ms", "10ms", "100ms", "1s", "PRBS Ratio 1:32", "PRBS Ratio 1:16", "PRBS Ratio 1:8", "PRBS Ratio 1:2"]

# Counts the number of timed glitches by checking whether SETup is in the glitch name
timed_glitch_count = sum(1 for glitch in glitch_lengths_breaker if "SETup" in glitch)

def main():
    displayTable("AN-036 Injecting Glitches with a Cable Tester", printToConsole=True, align="c")

    print("\nInsert the breaker to the A port of the cable tester")
    print("Then insert the cable into to the breaker on the A side, and into the cable tester on the B side\n")

    # Check we are on a recent version of quarchpy
    requiredQuarchpyVersion("2.2.21")

    # #Scans devices
    # device_list = scanDevices()
    # #Displays devices along with rescan, quit, all conn types
    # breaker_str = userSelectDevice(device_list, additionalOptions = ["Rescan", "All Conn Types", "Quit"], nice=True)

    #Optional hardcode
    breaker_str = "USB::QTL2171-02-041"

    #Create a quarch_device
    breaker = get_quarch_device(breaker_str)
    #Set to default state
    breaker.send_command("CONFig:DEFault STATE")
    print(f"Connected to :\n{breaker.send_command('*idn?')}\n")

    # #Scans devices
    # device_list = scanDevices()
    # #Displays devices along with rescan, quit, all conn types
    # cable_tester_str = userSelectDevice(device_list, additionalOptions = ["Rescan", "All Conn Types", "Quit"], nice=True)

    #Optional hardcode
    cable_tester_str = "USB::QTL2250-01-014"

    #Connect to the cable tester
    cable_tester = get_quarch_device(cable_tester_str)
    print(f"Connected to :\n{cable_tester.send_command('*idn?')}\n")

    # We will be glitching 1 lane, 2 lanes and all 4 lanes
    test_groupings = {
        "1 Lane": lanes_to_test[:1],
        "2 Lanes": lanes_to_test[:2],
        "4 Lanes": lanes_to_test[:4]}

    # Equivalent of PCIe Gen4.5 (fastest we can run), Gen4 and Gen3
    link_speeds = ["24G", "16G", "8G"]

    #Empty list to store results in
    results_list = []

    #Setup the CSV with a timestamped filename
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"lane_glitch_results_{timestamp}.csv"
    print(f"Results will be saved to: {filename}\n")

    #For each link speed we have set
    for link_speed in link_speeds:
        print(f"SETTING UP LINK FOR {link_speed}")

        # Stop any pre-running glitches and set link speed before initial training
        breaker.send_command("RUN:GLITch STOP")
        cable_tester.send_command(f"LINK:SPEED {link_speed}")

        retrain_link(cable_tester, breaker, link_speed)

        print(f"Link speed successfully set to: {cable_tester.send_command('LINK:SPEED?')}")
        time.sleep(2)

        #We will loop over each combination of 1 lane, 2 lane, 4 lane
        for group_name, active_lanes in test_groupings.items():
            #Get the TX pair for the breaker, and the tester port
            active_tx_pairs = [lane["tx_pair"] for lane in active_lanes]
            active_tester_ports = [lane["tester_port"] for lane in active_lanes]

            print(f"\nSTARTING {group_name.upper()} TEST AT {link_speed}")
            print(f"Glitching TX: {', '.join(active_tx_pairs)}")
            print(f"Checking Ports: {', '.join(active_tester_ports)}")

            #Check that all lanes are not able to glitch
            for pair in ["TX1", "TX2", "TX3", "TX4"]:
                breaker.send_command(f"SIGnal:{pair}_pl:GLITch:ENAble OFF")
                breaker.send_command(f"SIGnal:{pair}_mn:GLITch:ENAble OFF")

            time.sleep(1)

            #For the pairs we are glitching, enable glitching for both pl and mn
            for tx_pair in active_tx_pairs:
                breaker.send_command(f"SIGnal:{tx_pair}_pl:GLITch:ENAble ON")
                breaker.send_command(f"SIGnal:{tx_pair}_mn:GLITch:ENAble ON")

            #Ensure that BERT test is enabled on the port(s) we are testing
            for port in active_tester_ports:
                cable_tester.send_command(f"BERT:{port}:ENAble ON")

            #Reset the BERT for all link lanes
            reset_all_berts(cable_tester)
            time.sleep(1)

            #For each glitch length and actual glitch, glitched together, get an index as well
            for i, (glitch_length, actual_glitch) in enumerate(zip(glitch_lengths_breaker, actual_glitch_lengths)):
                #Reset the error counts to 0 as a precaution
                errors_before = 0
                errors_after = 0

                #Get a timestamp for the start of the test
                start_time = time.time()

                #Set the glitch length, or the PRBS ratio
                breaker.send_command(f"GLITch:{glitch_length}")
                #Reset the BERT counter
                reset_all_berts(cable_tester)

                #Sleep for 2 seconds to allow BERTs to count up if there is a dodgy link
                time.sleep(2)

                #Get error count before we start glitching
                errors_before = get_total_errors(cable_tester, active_tester_ports)

                # If we have some errors or an error getting error count, then we will retrain the link and run again
                if errors_before == "LINK_DEAD":
                    print(f"Unstable link, retraining and retrying...")
                    # Pass the active ports so retrain_link can turn them back on
                    retrain_link(cable_tester, breaker, link_speed,active_tester_ports)

                if errors_before != "LINK_DEAD" and errors_before > 0:
                    # Reset the BERT counter
                    reset_all_berts(cable_tester)
                    errors_before = 0
                    time.sleep(1)

                #Run the glitch
                run_glitch(breaker, i)

                #Sleep for 1 second to give time before we count the glitches
                time.sleep(1)

                errors_after = get_total_errors(cable_tester, active_tester_ports)

                #Set variables to be used as 0
                final_error_count = 0
                attempts = 0

                #Attempt to get a error count attempts_allowed times (default 5)
                while attempts < attempts_allowed:

                    #If we get LINK_DEAD from errors after, we retrain the link and try again
                    if errors_after == "LINK_DEAD":
                        print(f"\n{actual_glitch} glitch crashed the link. Recovering for next test...")
                        retrain_link(cable_tester, breaker, link_speed, active_tester_ports)

                        run_glitch(breaker, i)

                        attempts += 1
                        continue

                    #Get the error count - we expect errors_before to be 0
                    errors = errors_after - errors_before

                    #Assuming we have some errors, we display a message and move on to the next loop
                    if errors > 0:
                        print(f"\n{actual_glitch} glitch across {len(active_tx_pairs)} lane(s) at {link_speed} caused {errors} total errors")
                        final_error_count = errors
                        break
                    #If we haven't detected any errors, try again
                    else:

                        #If on the last attempt we still don't have any glitches, we print a message and exit this loop
                        if attempts == (attempts_allowed - 1):
                            print(f"Glitch {actual_glitch} caused no detectable errors after {attempts_allowed} attempts")
                            break
                        else:
                            #If we can't detect errors from the glitch run earlier, run it again
                            print(f"No errors detected for {actual_glitch}, retrying")
                            run_glitch(breaker, i)

                            attempts += 1
                            continue

                #Get a timestamp for the end, and store how long each test took in test_duration
                end_time = time.time()
                test_duration = end_time - start_time

                # Append data to the flat list
                results_list.append({
                    "Test_Configuration": group_name,
                    "Active_Lane_Count": len(active_tx_pairs),
                    "Active_Breaker_TX": "+".join(active_tx_pairs),
                    "Active_Tester_Ports": "+".join(active_tester_ports),
                    "Link_Speed": link_speed,
                    "Glitch_Length": actual_glitch,
                    "Total_Errors": final_error_count,
                    "Test_Duration_Sec": round(test_duration, 2)
                })

                #Save to CSV
                df_results = pd.DataFrame(results_list)
                df_results.to_csv(filename, index=False)


                #After the data has been successfully stored, reset BERT counters
                reset_all_berts(cable_tester)
                #Sleep for 2 seconds between each glitch length, to keep the link up
                time.sleep(2)

            print(f"Glitches at {link_speed} complete for {group_name}")

    #Set breaker and cable tester to default state
    breaker.send_command("CONFig:DEFault STATE")
    cable_tester.send_command("CONFig:DEFault STATE")
    #Close connections
    breaker.close_connection()
    cable_tester.close_connection()

    print(f"\nTest complete, results successfully saved to {filename}")

    return 0

# Get errors across all ports
def get_total_errors(cable_tester, ports):
    total = 0
    #For all 4 ports we have
    for p in ports:
        #Query the errors
        response = cable_tester.send_command(f"BERT:{p}:ERRors?")
        try:
            #Attempt to convert into int and add it to running total
            total += int(response)
        except ValueError:
            print(f"Failure getting error count :{response}")
            # Pass a flag to the main loop indicating the link dropped
            return "LINK_DEAD"
    return total

def reset_all_berts(cable_tester):
    """
    Reset all BERT counters to 0
    :param cable_tester: cable tester
    """
    #Reset the BERT counter for all counters
    ports = ["A0", "A1", "A2", "A3", "B0", "B1", "B2", "B3"]
    for port in ports:
        cable_tester.send_command(f"BERT:{port}:RESet")

def retrain_link(cable_tester, breaker, link_speed, ports=None):
    """Called when the link needs to be trained or retrained
    :param cable_tester: cable tester
    :param breaker: breaker
    :param link_speed: link speed we are running currently
    :param ports: Pass in the ports array optionally to reset the BERT counter"""
    #This is called at the start, or when we change link speed, or the link has errors without any glitches being run
    print("Retraining link...")
    #Stop any test, or any glitches running
    cable_tester.send_command("RUN:STOP")
    breaker.send_command("RUN:GLITch STOP")

    time.sleep(2)

    #Set the cable tester to the link it should be
    cable_tester.send_command(f"LINK:SPEED {link_speed}")
    time.sleep(1)

    #TODO REMOVE THIS
    cable_tester.send_command("CONFig:FAULT:RESet")

    #Start running the test
    cable_tester.send_command("RUN:TEST")

    print("Checking cable state...")

    #Query the test state, and poll it until we pass the test
    response = cable_tester.send_command("RUN:INT?")
    while "COMPLETE" not in response:
        #Query the interrupt flags
        response = cable_tester.send_command("RUN:INT?")

        #Sleep so we don't poll too fast
        time.sleep(1)

    print("Cable trained, tests passed")

    #Ensure that the BERT counters are reset
    if ports:
        print("Resetting error counters")
        for p in ports:
            cable_tester.send_command(f"BERT:{p}:ENAble ON")

    #Sleep for 2 seconds to give time for the cable to come back online
    time.sleep(2)

def run_glitch(breaker, i):
    """
    Runs glitch
    :param breaker: the breaker we are using
    :param i: glitch index, as PRBS and timed glitches are run in different ways
    """
    #If this is a timed glitch, run it once
    if i <= timed_glitch_count:
        breaker.send_command("RUN:GLITch ONCE")
        time.sleep(test_length)

    #If this is a PRBS glitch, run it for test_length then stop it
    if i >= (timed_glitch_count + 1):
        breaker.send_command("RUN:GLITch PRBS")
        time.sleep(test_length)
        breaker.send_command("RUN:GLITch STOP")

if __name__ == "__main__":
    main()
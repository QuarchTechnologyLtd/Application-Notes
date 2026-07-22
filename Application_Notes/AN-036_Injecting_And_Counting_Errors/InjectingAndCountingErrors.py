"""
AN-036 - Application note demonstrating fault injection and error counting

This example injects glitches with a breaker and counts the errors with a cable tester. QSFP28 was used in testing, but should work for any form factors we have modules for.
Using a QSFP28 cable tester (QTL2250) and a QSFP28 breaker (QTL2171), we will inject glitches and count the BER
We loop over link speed, number of lanes glitched, and glitched length.
This will output a CSV containing the recorded data, which can be used for estimating the errors at faster speeds

########### VERSION HISTORY ###########
25/06/2026 - Andrew Steedman - First Version.

########### REQUIREMENTS ###########
1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
3- Quarch USB driver (Required for USB connected devices on Windows only)
    https://quarch.com/downloads/driver/
4- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

########### INSTRUCTIONS ###########
Change the cable mapping dependent on your cable used, and optionally reduce the link speed depending on the cable you are using
Connect the cable and the breaker to the cable tester, then connect the breaker and cable tester via USB or LAN to this PC
Run the script, which will generate a CSV with the data.

1- Check the cable mapping of your cable
2- Connect the cable and the breaker to the cable tester
3- Connect the cable tester and breaker to the PC via LAN or USB
4- Run the script and follow the instructions on screen.
"""
import time #Used for timing each test
import pandas as pd #We save the data into a CSV for easy further analysis

import quarchpy
from quarchpy.debug.versionCompare import requiredQuarchpyVersion
from quarchpy.device import *
from quarchpy.user_interface import displayTable, visual_sleep, showYesNoDialog

#Tester map - Change this for different cables, and whether the breaker is plugged into A side or B side
lanes_to_test = [
    {"tx_pair": "TX1", "tester_port": "A3"},
    {"tx_pair": "TX2", "tester_port": "A1"},
    {"tx_pair": "TX3", "tester_port": "A2"},
    {"tx_pair": "TX4", "tester_port": "A0"}]

# Length of time to sleep for, and length of time for PRBS - If this is too short this can misrepresent the true number of errors so suggested to keep at 10
test_length = 10
#Number of tries to get the error count from the glitch
attempts_allowed = 5

# List of glitch lengths in the format sent to the breaker
glitch_lengths_breaker = ["SETup 50ns 2", "SETup 500ns 2", "SETup 5us 2", "SETup 50us 2", "SETup 500us 2", "SETup 5ms 2", "SETup 50ms 2", "SETup 500ms 2", "PRBS 32", "PRBS 16", "PRBS 8", "PRBS 2"]
# More readable format of glitch lengths - with these values, we'd expect error count to increase at 10x between each glitch
actual_glitch_lengths = ["100ns", "1us", "10us", "100us", "1ms", "10ms", "100ms", "1s", "PRBS Ratio 1:32", "PRBS Ratio 1:16", "PRBS Ratio 1:8", "PRBS Ratio 1:2"]
# Counts the number of timed glitches by checking whether SETup is in the glitch name
timed_glitch_count = sum(1 for glitch in glitch_lengths_breaker if "SETup" in glitch)

def main():
    # # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
    # # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
    # logging.basicConfig(level=logging.DEBUG)
    # # To control specifically the quarchpy console log level use the following line:
    # quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
    # # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.

    displayTable("AN-036 Injecting Glitches with a Cable Tester", printToConsole=True, align="c")

    print("\nInsert the breaker to the A port of the cable tester")
    print("Then insert the cable into to the breaker on the A side, and into the cable tester on the B side\n")

    # Check we are on a recent version of quarchpy
    requiredQuarchpyVersion("2.2.21")
    
    #Display the current mapping
    print("\nDefault cable mapping is set as ")
    for lane in lanes_to_test:
        tx = lane["tx_pair"]
        port = lane["tester_port"]
        #Print the current mapping
        print(f"{tx} pair is connected to Port {port} on the tester")

    #Asks user if mapping is correct
    mapping_correct = showYesNoDialog(title="", message="Is this mapping correct for your cable and setup?")

    if mapping_correct == "No":
        print("\nPlease enter the correct mapping for the cable and setup")

        #Update the port for each tx pair
        for lane in lanes_to_test:
            tx = lane["tx_pair"]
            port = input(f"Please enter the port {tx} pairs to on your cable: ")

            #Change the vlue in the dictionary
            lane["tester_port"] = port

        #Display the updated mapping
        print("\nUpdated Mapping")
        for lane in lanes_to_test:
            tx = lane["tx_pair"]
            port = lane["tester_port"]
            print(f"TX pair {tx} is connected to Port {port} on the tester")

    #Scans devices
    device_list = scanDevices()
    print("Please select the breaker to be used")
    #Displays devices along with rescan, quit, all conn types
    breaker_str = userSelectDevice(device_list, additionalOptions = ["Rescan", "All Conn Types", "Quit"], nice=True)

    if breaker_str == "Quit":
        print("User selected quit, exiting script")
        return 0

    #Optional hardcode - Uncomment this, and comment in the selection lines above to hardcode this
    #breaker_str = "USB::QTL2171-02-041"

    #Create a quarch_device
    breaker = get_quarch_device(breaker_str)
    #Set to default state
    breaker.send_command("CONFig:DEFault STATE")
    print(f"Connected to :\n{breaker.send_command('*idn?')}\n")

    #Scans devices
    device_list = scanDevices()
    #Displays devices along with rescan, quit, all conn types
    print("Please select the Cable Tester")
    cable_tester_str = userSelectDevice(device_list, additionalOptions = ["Rescan", "All Conn Types", "Quit"], nice=True)

    if cable_tester_str == "Quit":
        print("User selected quit, exiting script")
        return 0

    #Optional hardcode - Uncomment this, and comment in the selection lines above to hardcode this
    #cable_tester_str = "USB::QTL2250-01-014"

    #Connect to the cable tester
    cable_tester = get_quarch_device(cable_tester_str)
    print(f"Connected to :\n{cable_tester.send_command('*idn?')}\n")

    # We will be glitching 1 lane, 2 lanes and all 4 lanes
    lane_widths = {
        "1 Lane": lanes_to_test[:1],
        "2 Lanes": lanes_to_test[:2],
        "4 Lanes": lanes_to_test[:4]}

    # Equivalent of PCIe Gen4.5 (fastest we can run), Gen4 and Gen3
    link_speeds = ["24G","16G","8G"]

    #Empty list to store results in
    results_list = []

    #Setup the CSV with a timestamped filename
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"lane_glitch_results_{timestamp}.csv"
    print(f"Results will be saved to: {filename}\n")

    #For each link speed we have set
    for link_speed in link_speeds:
        print(f"Setting up link at {link_speed}")

        # Stop any pre-running glitches and set link speed before initial training
        breaker.send_command("RUN:GLITch STOP")
        cable_tester.send_command(f"LINK:SPEED {link_speed}")

        #Retrain the link
        retrain_link(cable_tester, breaker, link_speed)

        print(f"Link speed successfully set to: {cable_tester.send_command('LINK:SPEED?')}")
        time.sleep(2)

        #We will loop over each combination of 1 lane, 2 lane, 4 lane
        for lane_count, active_lanes in lane_widths.items():
            #Get the TX pair for the breaker, and the tester port a0 etc
            active_tx_pairs = [lane["tx_pair"] for lane in active_lanes]
            active_tester_ports = [lane["tester_port"] for lane in active_lanes]

            print(f"\nStarting {lane_count} test at {link_speed}")

            #Disable glitches on all lanes to start
            for pair in ["TX1", "TX2", "TX3", "TX4"]:
                breaker.send_command(f"SIGnal:{pair}_pl:GLITch:ENAble OFF")
                breaker.send_command(f"SIGnal:{pair}_mn:GLITch:ENAble OFF")

            #For the pairs we are glitching, enable glitching for both pl and mn
            for tx_pair in active_tx_pairs:
                breaker.send_command(f"SIGnal:{tx_pair}_pl:GLITch:ENAble ON")
                breaker.send_command(f"SIGnal:{tx_pair}_mn:GLITch:ENAble ON")

            #Ensure that BERT test is enabled on the port(s) we are testing
            for port in active_tester_ports:
                cable_tester.send_command(f"BERT:{port}:ENAble ON")

            #Reset the BER counters for all link lanes
            reset_all_ber(cable_tester)
            time.sleep(1)

            #Loop over each glitch length and actual glitch, zipped together, and get an index for the glitch_type.
            for glitch_index, (glitch_length, actual_glitch) in enumerate(zip(glitch_lengths_breaker, actual_glitch_lengths)):
                #Get a timestamp for the start of the test
                start_time = time.time()

                #Set the glitch length, or the PRBS ratio
                breaker.send_command(f"GLITch:{glitch_length}")
                #Reset the BERT counter
                reset_all_ber(cable_tester)

                #Sleep for 3 seconds to allow BERTs to count up if there is a dodgy link
                time.sleep(3)

                #Get error count before we start glitching
                errors_before = get_total_errors(cable_tester, active_tester_ports)

                # If we have some errors or an error getting error count, then we will retrain the link and run again
                if errors_before == "LINK_DEAD":
                    print(f"Unstable link, retraining and retrying...")
                    # Pass the active ports so retrain_link can turn them back on
                    retrain_link(cable_tester, breaker, link_speed,active_tester_ports)

                if errors_before != "LINK_DEAD" and errors_before > 0:
                    # Reset the BERT counter
                    reset_all_ber(cable_tester)
                    errors_before = 0
                    time.sleep(1)

                #Run the glitch
                time.sleep(1)
                run_glitch(breaker, glitch_index)

                #Sleep for 1 second to give time before we count the glitches
                time.sleep(1)

                errors_after = get_total_errors(cable_tester, active_tester_ports)

                #Set variables to be used as 0
                final_error_count = 0
                attempts = 0

                #Try to get error count attempts_allowed times (default 5)
                while attempts < attempts_allowed:

                    #If we get LINK_DEAD from errors after, we retrain the link and try again
                    if errors_after == "LINK_DEAD":
                        print(f"\n{actual_glitch} glitch crashed the link. Attempting to retrain and retry...")
                        retrain_link(cable_tester, breaker, link_speed, active_tester_ports)

                        time.sleep(1)

                        run_glitch(breaker, glitch_index)

                        attempts += 1
                        continue

                    #Get the error count - we expect errors_before to be 0
                    errors = errors_after - errors_before

                    #Assuming we have some errors, we display a message and move on to the next loop
                    #Check whether its more than 200, as a non-functioning tests return low error counts
                    if errors > 200:
                        print(f"\n{actual_glitch} glitch across {len(active_tx_pairs)} lane(s) at {link_speed} caused {errors} total errors")
                        final_error_count = errors
                        break

                    #If we haven't detected any errors above the threshold, try again
                    else:
                        #If on the last attempt we still don't have any glitches, we print a message and exit this loop
                        if attempts == (attempts_allowed - 1):
                            print(f"Glitch {actual_glitch} caused no detectable errors after {attempts_allowed} attempts")
                            break
                        else:
                            #If we can't detect errors from the glitch run earlier, run it again and increment attempts
                            print(f"No errors detected for {actual_glitch}, retrying")
                            run_glitch(breaker, glitch_index)
                            attempts += 1
                            continue

                #Get a timestamp for the end, and store how long each test took in test_duration
                #Can be used to calculate BER
                end_time = time.time()
                test_duration = end_time - start_time

                # Append data to the flat list
                results_list.append({
                    "Test_Configuration": lane_count,
                    "Active_Lane_Count": len(active_tx_pairs),
                    "Link_Speed": link_speed,
                    "Glitch_Length": actual_glitch,
                    "Total_Errors": final_error_count,
                    "Test_Duration_Sec": round(test_duration, 2)
                })

                #Save to CSV
                df_results = pd.DataFrame(results_list)
                df_results.to_csv(filename, index=False)

                #Sleep for 2 seconds between each glitch length, to keep the link up
                time.sleep(2)

            print(f"Glitches at {link_speed} complete for {lane_count}")

    #Stop any test running
    cable_tester.send_command("RUN:STOP")

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
    """
    Count the errors for the ports we are actively testing

    :param cable_tester: cable tester
    :param ports: ports we are actively testing
    :return: total error count, or an error message if we have failed in some way
    """
    total = 0
    #For the ports we have
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

def reset_all_ber(cable_tester):
    """
    Reset all BERT counters to 0
    :param cable_tester: cable tester
    """
    #Reset the BERT counter for all counters
    ports = ["A0", "A1", "A2", "A3", "B0", "B1", "B2", "B3"]
    for port in ports:
        cable_tester.send_command(f"BERT:{port}:RESet")

def retrain_link(cable_tester, breaker, link_speed, ports=None):
    """Called when the link needs to be trained or retrained - at the start, or changing link speed
    :param cable_tester: cable tester
    :param breaker: breaker
    :param link_speed: link speed we are running currently
    :param ports: Pass in the ports array optionally to reset the BERT counter"""
    print("Retraining link...")
    #Stop any test, or any glitches running
    cable_tester.send_command("RUN:STOP")
    breaker.send_command("RUN:GLITch STOP")

    time.sleep(2)

    #Set the cable tester to the link it should be
    cable_tester.send_command(f"LINK:SPEED {link_speed}")
    time.sleep(1)

    #Start running the test
    cable_tester.send_command("RUN:TEST")

    print("Checking cable state...")

    #Query the test state, and poll it until we get complete
    response = cable_tester.send_command("RUN:INT?")
    print(f"Current cable status: {response} waiting for COMPLETE")
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

def run_glitch(breaker, glitch_index):
    """
    Runs glitch
    :param breaker: the breaker we are using
    :param glitch_index: glitch index, as PRBS and timed glitches are run in different ways
    """
    #If this is a timed glitch, run it once then sleep
    if glitch_index <= timed_glitch_count:
        breaker.send_command("RUN:GLITch ONCE")
        time.sleep(test_length)

    #If this is a PRBS glitch, run it for test_length then stop it
    if glitch_index >= (timed_glitch_count + 1):
        breaker.send_command("RUN:GLITch PRBS")
        time.sleep(test_length)
        breaker.send_command("RUN:GLITch STOP")

if __name__ == "__main__":
    main()

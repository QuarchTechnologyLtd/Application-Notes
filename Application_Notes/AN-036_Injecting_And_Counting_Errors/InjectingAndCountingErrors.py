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

    # Check we are on a recent version of quarchpy
    requiredQuarchpyVersion("2.2.21")

    # #Scans devices
    # device_list = scanDevices()
    # #Displays devices along with rescan, quit, all conn types
    # breaker_str = userSelectDevice(device_list, additionalOptions = ["Rescan", "All Conn Types", "Quit"], nice=True)

    # Hardcoded Device Strings
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

    # Test the link and the cable
    response = cable_tester.send_command("RUN TEST")
    if response == "FAIL: 0x61 -Unit is busy, wait then try again":
        cable_tester.send_command("RUN:STOP")
        cable_tester.send_command("RUN:TEST")

    # List of glitch lengths
    glitch_lengths_breaker = ["SETup 50ns 1", "SETup 50ns 2", "SETup 500ns 2", "SETup 5us 2", "SETup 50us 2", "SETup 500us 2", "SETup 5ms 2", "SETup 50ms 2", "SETup 500ms 2", "PRBS 32", "PRBS 16", "PRBS 8", "PRBS 2"]
    #Used to store number of timed glitches - PRBS glitches are setup and run in a different way
    timed_glitch_count = 8
    #More readable format of glitch lengths
    actual_glitch_lengths = ["50ns", "100ns", "1us", "10us", "100us", "1ms", "10ms", "100ms", "1s", "PRBS Ratio 1:32", "PRBS Ratio 1:16", "PRBS Ratio 1:8", "PRBS Ratio 1:2"]

    # Equivalent of PCIe Gen4.5 (fastest we can run), Gen4 and Gen3
    link_speeds = ["24G", "16G", "8G"]


    # Change these tester_ports if you use a cable with different cross-wiring!
    lanes_to_test = [
        {"tx_pair": "TX1", "tester_port": "A3"},
        {"tx_pair": "TX2", "tester_port": "A1"},
        {"tx_pair": "TX3", "tester_port": "A2"},
        {"tx_pair": "TX4", "tester_port": "A0"}
    ]

    #We will glitch 1 lane, 2 lanes and all 4 lanes
    test_groupings = {
        "1-Lane": lanes_to_test[:1],
        "2-Lane": lanes_to_test[:2],
        "4-Lane": lanes_to_test[:4]
    }

    results_list = []



    # ==========================================
    # OUTER LOOP: Iterate over Group Configurations
    # ==========================================
    for group_name, active_lanes in test_groupings.items():

        # Extract the specific TX and Tester ports for this group
        active_tx_pairs = [lane["tx_pair"] for lane in active_lanes]
        active_tester_ports = [lane["tester_port"] for lane in active_lanes]

        print(f"\n{'='*50}")
        print(f"STARTING {group_name.upper()} TEST")
        print(f"Active Breaker TX: {', '.join(active_tx_pairs)}")
        print(f"Active Tester Ports: {', '.join(active_tester_ports)}")
        print(f"{'='*50}")

        # Ensure all lanes are disabled first to prevent cross-contamination
        for pair in ["TX1", "TX2", "TX3", "TX4"]:
            breaker.send_command(f"SIGnal:{pair}_pl:GLITch:ENAble OFF")
            breaker.send_command(f"SIGnal:{pair}_mn:GLITch:ENAble OFF")
        for port in ["A0", "A1", "A2", "A3"]:
            cable_tester.send_command(f"BERT:{port}:ENAble OFF")

        time.sleep(1)

        # Enable glitching ONLY on the active lanes for this group
        for tx_pair in active_tx_pairs:
            breaker.send_command(f"SIGnal:{tx_pair}_pl:GLITch:ENAble ON")
            breaker.send_command(f"SIGnal:{tx_pair}_mn:GLITch:ENAble ON")

        # Enable BERT ONLY on the mapped active ports
        for port in active_tester_ports:
            cable_tester.send_command(f"BERT:{port}:ENAble ON")

        reset_all_berts(active_tester_ports)
        time.sleep(1)

        # ==========================================
        # MIDDLE LOOP: Iterate over link speeds
        # ==========================================
        for link_speed in link_speeds:
            print(f"\nSet link speed to {link_speed} for {group_name}")

            breaker.send_command("RUN:GLITch STOP")
            cable_tester.send_command(f"LINK:SPEED {link_speed}")
            cable_tester.send_command("RUN:TEST")

            attempts = 0
            while attempts < 5:
                response = cable_tester.send_command("RUN:TEST?")
                time.sleep(1)
                if response == "PASS":
                    break
                else:
                    attempts += 1
                    continue

            print(f"Link speed successfully set to: {cable_tester.send_command('LINK:SPEED?')}")
            time.sleep(2)

            # ==========================================
            # INNER LOOP: Iterate over the glitches
            # ==========================================
            for i, (glitch_length, actual_glitch) in enumerate(zip(glitch_lengths_breaker, actual_glitch_lengths)):
                start_time = time.time()

                breaker.send_command(f"GLITch:{glitch_length}")
                reset_all_berts(active_tester_ports)
                time.sleep(2)

                # Check aggregate baseline stability
                errors_before = get_total_errors(active_tester_ports)

                if errors_before > 0:
                    print(f"Unstable link (Baseline: {errors_before}), skipping {actual_glitch}")
                    breaker.send_command("RUN:GLITch STOP")
                    time.sleep(2)
                    continue

                if i <= timed_glitch_count:
                    breaker.send_command("RUN:GLITch ONCE")
                    time.sleep(2)

                if i >= (timed_glitch_count+1):
                    breaker.send_command("RUN:GLITch PRBS")
                    time.sleep(5)
                    breaker.send_command("RUN:GLITch STOP")

                final_error_count = 0
                attempts = 0

                while attempts < 3:
                    # Get new aggregate error count
                    errors_after = get_total_errors(active_tester_ports)
                    errors = errors_after - errors_before

                    if errors > 0:
                        print(f"\n{actual_glitch} glitch across {len(active_tx_pairs)} lane(s) at {link_speed} caused {errors} total errors")
                        final_error_count = errors
                        break
                    else:
                        if attempts == 2:
                            print(f"Glitch {actual_glitch} caused no detectable errors after 3 attempts")
                            break
                        else:
                            print(f"No errors detected for {actual_glitch}, retrying")
                            if i <= timed_glitch_count:
                                breaker.send_command("RUN:GLITch ONCE")
                                time.sleep(1.2)
                            if i >= (timed_glitch_count+1):
                                breaker.send_command("RUN:GLITch PRBS")
                                time.sleep(1)
                                breaker.send_command("RUN:GLITch STOP")
                            attempts += 1
                            continue

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

                reset_all_berts(active_tester_ports)
                time.sleep(0.5)

            print(f"Glitches at {link_speed} complete for {group_name}")

    # ==========================================
    # Save results to Pandas DataFrame
    # ==========================================
    df_results = pd.DataFrame(results_list)
    filename = "grouped_lane_glitch_results.csv"
    df_results.to_csv(filename, index=False)

    breaker.send_command("CONFig:DEFault STATE")
    cable_tester.send_command("CONFig:DEFault STATE")
    breaker.close_connection()
    cable_tester.close_connection()

    print(f"\nTest complete, results saved to {filename}")

    return 0

# Helper function to get aggregate errors across multiple active ports
def get_total_errors(cable_tester, ports):
    total = 0
    for p in ports:
        total += int(cable_tester.send_command(f"BERT:{p}:ERRors?"))
    return total

# Helper function to reset multiple ports
def reset_all_berts(cable_tester, ports):
    for p in ports:
        cable_tester.send_command(f"BERT:{p}:RESet")

if __name__ == "__main__":
    main()
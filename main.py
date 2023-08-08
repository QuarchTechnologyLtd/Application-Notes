'''
AN-022 - Application note demonstrating automation and post processing of raw data with QIS

This example demonstrates basic automation with QIS and post processing of raw data after recording.
We will record at a high rate and post process down to a lower rate, ending with 100uS and 500uS sample rates

QIS is distributed as part of the Quarchpy python package and does not require seperate install

########### VERSION HISTORY ###########

03/10/2019 - Andy Norrie     - First Version
07/11/2019 - Stuart Boon     - Module selection and streaming data fix
06/12/2019 - Stuart Boon     - Added rescan to module selection
17/11/2022 - Andy Norrie     - Major re-write of app note documentation
16/05/2023 - Nabil Ghayyda   - Re-written app note file to match standards

########### REQUIREMENTS ###########

1- Python (3.x recommended)
    https://www.python.org/downloads/
2- Java 8, with JaxaFX
    https://quarch.com/support/faqs/java/
3- Quarchpy python package
    https://quarch.com/products/quarchpy-python-package/
4- Quarch USB driver (Required for USB connected devices on windows only)
    https://quarch.com/downloads/driver/
5- Check USB permissions if using Linux:
    https://quarch.com/support/faqs/usb/

########### INSTRUCTIONS ###########

1- Connect a Quarch power module to your PC via USB or LAN and power it on
2- Ensure quarcypy is installed
3- Set the text ID of the PPM you want to connect to in myDeviceID

####################################
'''

import os, time

import quarchpy
from quarchpy import *
from quarchpy.device import *
from quarchpy.qis import *
# Timing to check how long it takes to end the stream
from timeit import default_timer as timer

# Path where stream will be saved to (defaults to current script path)
streamPath = os.path.dirname(os.path.realpath(__file__))


def main(args=[]):
    # Use a breakpoint in the code line below to debug your script.
    # Required min version for this application note
    quarchpy.requiredQuarchpyVersion("2.0.9")

    print("\n\nQuarch application note example: AN-026")
    print("---------------------------------------\n\n")

    # Start QIS (if it is already running, skip this step and also avoid closing it at the end)
    print("Starting QIS...\n")
    closeQisAtEndOfTest = False
    if isQisRunning() == False:
        startLocalQis()
        closeQisAtEndOfTest = True

    # Connect to the localhost QIS instance
    myQis = QisInterface()

    # Ask the user to select a module to use, via the console.
    myDeviceID = myQis.GetQisModuleSelection(additionalOptions=["rescan"])
    while myDeviceID == "rescan":
        myDeviceID = myQis.GetQisModuleSelection(additionalOptions=["rescan"])

    # If you know the name of the module you would like to talk to then you can skip module selection and hardcode the string.
    # myDeviceID = "USB:QTL1999-05-005"

    # Connect to the module
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType="QIS")

    # Convert the base device class to a power device, which provides additional controls, such as data streaming
    myQisDevice = quarchPPM(myQuarchDevice)

    # Prints out connected module information
    print("Module Selected: " + myDeviceID + "\n")

    print("\nWaiting for drive to be ready\n")
    # Setup the voltage mode and enable the outputs. This is used so the script is compatible with older XLC modules which do not autodetect the fixtures
    myQisDevice.setupPowerOutput()
    # (OPTIONAL) Wait for device to power up and become ready (you can also start your workloads here if needed)
    # time.sleep(5)

    print("Setting up module record parameters\n")

    # Sets for a manual record trigger, so we can start the stream from the script
    msg = myQisDevice.sendCommand("record:trigger:mode manual")
    if (msg != "OK"):
        print("Failed to set trigger mode: " + msg)
    # Set the averaging rate to the module to 16 (64uS) as the closest to 100uS
    msg = myQisDevice.sendCommand("record:averaging 16")
    if (msg != "OK"):
        print("Failed to set hardware averaging: " + msg)
    # Set the resampling mode to give us exactly 100uS
    msg = myQisDevice.sendCommand("stream mode resample 100uS")
    if (msg != "OK"):
        print("Failed to set software resampling: " + msg)
    # Ensure the latest level of header is requested so PPM and PAM data format is the same in the CSV
    msg = myQisDevice.sendCommand("stream mode header v3")
    if (msg != "OK"):
        print("Failed to set software resampling: " + msg)

    print("\nRecording data...\n")
    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = "RawData100us.csv"
    #
    response = startStream(myQis, fileName, myQisDevice, duration=5)

    # close qis
    closeQIS()


'''
This function will start a stream on QIS and provide write the stream data to a csv file of your choosing. 
Arguments:
 - myQIS ()
 - fileName ()
 - qisDevice ()
 - duration ()

Exits method when stream has stopped.
'''


def startStream(myQIS, fileName, qisDevice, duration):
    # Starts stream using command "rec stream" and checks for response
    response = qisDevice.sendCommand('rec stream')
    if response != 'OK':
        print("Failed to start stream")
    time.sleep(0.5)  # Give some time for stream to start properly
    # Gets the stream header for the file
    with open(fileName, 'w') as f:
        formatHeader = myQIS.streamHeaderFormat(device=qisDevice.ConString)
        formatHeader.replace(", ", ",")
        f.write(formatHeader + '\n')
    numStripesPerRead = 4096
    openAttempts = 0
    leftover = 0
    remainingStripes = []
    streamOverrun = False
    streamComplete = False
    streamDuration = 3000

    module = qisDevice.ConString

    isRun = True
    while isRun:
        try:
            with open(fileName, 'ab') as f:
                # Until the event threadRunEvent is set externally to this thread,
                # loop and read from the stream
                while (not streamOverrun) and (not streamComplete):
                    # now = time.time()
                    streamOverrun, removeChar, newStripes = myQIS.streamGetStripesText(device=module, sock=myQIS.sock,
                                                                                       numStripes=numStripesPerRead)
                    newStripes = newStripes.replace(b' ', str.encode(","))
                    # print (time.time() - now)
                    if streamOverrun:
                        print("Stream is overrun!")
                        streamOverrun = True
                    # TODO: MD Why don't we return isEmpty in the tuple, instead of having this confusing test?
                    if (removeChar == -6 and len(newStripes) == 6):
                        isEmpty = True
                    else:
                        isEmpty = False
                    if isEmpty == False:

                        # if we have a fixed streamDuration
                        if streamDuration != None:
                            # Get the last data line in the file
                            lastLine = newStripes.splitlines()[
                                -3]  # the last data line is followed by 'eof' and '>'
                            lastTime = lastLine.decode().split(",")[0]  # get the first (time) entry

                            # if the last entry is still within the required stream length, write the whole lot
                            if int(lastTime) < int(streamDuration / (10 ** -3)):  # < rather than <= because we start at 0
                                f.write(newStripes[:removeChar])
                            # else write each line individually until we have reached the desired endpoint
                            else:
                                for thisLine in newStripes.splitlines()[:-2]:
                                    lastTime = thisLine.decode().split(",")[0]
                                    if int(lastTime) < int(streamDuration / (10 ** -3)):
                                        f.write(thisLine + b'\r' + b'\n')  # Put the CR back on the end
                                    else:
                                        print("STOPPP !!!!!!!!!!!!!!!!!")
                                        streamComplete = True
                                        break
                        else:
                            f.write(newStripes[:removeChar])
                    else:
                        # there's no stripes in the buffer - it's not filling up fast -
                        # sleeps so we don't spam qis with requests (seems to make QIS crash)
                        # it might be clever to change the sleep time accoring to the situation
                        # e.g. wait longer with higher averaging or lots of no stripes in a row
                        time.sleep(0.1)
                        streamStatus = myQIS.streamRunningStatus(device=module)
                        if streamOverrun:
                            # printText('QisInterface overrun - breaking')
                            break
                        elif "Stopped" in streamStatus:
                            print("STOPPP !!!!!!!!!!!!!!!!!")
                            break
                break
        except IOError:
            print("POGGERS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    # Attempts to stop the stream using "rec stop"
    response = qisDevice.sendCommand('rec stop')
    if response != 'OK':
        print("Failed to stop stream")
    return


def streamHeaderAverage():
    return


def streamHeaderFormat():
    return


if __name__ == '__main__':
    main()

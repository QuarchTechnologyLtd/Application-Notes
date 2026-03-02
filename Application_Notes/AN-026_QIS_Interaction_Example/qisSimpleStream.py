import tkinter.filedialog

import quarchpy
from quarchpy.device import *
from quarchpy.qis import *
from quarchpy.user_interface.user_interface import quarchSleep
from quarchpy import __version__ as quarchpyVersion
import time, datetime

# # If you require logging, quarchpy logs everything level debug and above to file. It is also set to log to console
# # at the same level the python default logger. To get python logs and quarchpy logs in console comment in this line:
# logging.basicConfig(level=logging.DEBUG)
# # To control specifically the quarchpy console log level use the following line:
# quarchpy.configure_logging(console_level=logging.DEBUG) # you need "import quarchpy"
# # Use a combination of the 2 if you want only python logs with no quarchpy logs or vice versa.


def main():
    print("\n\nQuarch application note example: AN-")
    print("QuarhPy Version:" + quarchpyVersion)
    print("---------------------------------------\n\n")

    #Test Parameters
    fileName = "myFile.csv" #Use this if you want to hard code a file path.
    streamLength = 5
    separator = ","
    averaging ="16" # each sample is taken every 4uS, so 16 means a sample every 64uS
    resampling="100ms"
    #Comment these is if you would like user input for these parameters.
    # streamLength = input("Please enter the time in seconds you would like to stream for: ")
    # averaging = input("Please enter the base averaging you would like to have: ") #Sample rate of the Quarch module
    # resampling = input("Please enter the sample rate for the output file: ") #Sample rate of the output to file
    # fileName = tkinter.filedialog.asksaveasfilename(filetypes=[("csv file", ".csv")]) + ".csv"

    #Starting QIS and getting the version number
    closeQisAtEndOfTest = False
    if isQisRunning() == False:
        print("Starting QIS")
        startLocalQis()
        closeQisAtEndOfTest = True
    else:
        print("QIS already running. Using this instance.")
    myQis = QisInterface()
    print("QIS Version: " + myQis.sendAndReceiveCmd(cmd='$version'))

    # If you know the name of the module you would like to talk to then you can skip module selection and hardcode the string.
    myDeviceID = "USB::QTL2312-01-035"
    #myDeviceID = myQis.GetQisModuleSelection()
    print("Module Selected: " + myDeviceID + "\n")
    myQuarchDevice = getQuarchDevice(myDeviceID, ConType="QIS")
    module = quarchPPM(myQuarchDevice)
    module.sendCommand("stream mode header v3")
    module.sendCommand("stream mode power enable")
    module.sendCommand("stream mode power total enable")

    print("Set manual Trigger: " + module.sendCommand("record:trigger:mode manual"))
    print("Set averaging: " + module.sendCommand("record:averaging "+ str(averaging)))
    if resampling != None:
        module.sendCommand("stream mode resample "+str(resampling))
    startTime= time.time()

    print("Start stream: "+module.sendCommand("record stream"))
    output=""
    formatHeader = ""
    while time.time()-startTime<streamLength:
        time.sleep(1) # sleep every loop to allow some stream data to add up.
        response=module.sendCommand("stream text all")
        output+=response
        if ("stopped" in module.sendCommand("stream?").lower()):
            break
        elif formatHeader==""or "time" not in formatHeader.lower():
            formatHeader = myQis.streamHeaderFormat(device=module.ConString) #The header must be requested while the device is streaming and is only needed once.

    streamStatus = module.sendCommand("stream?").lower() #check to see if the module stopped streaming early and why.
    if ("stopped" in streamStatus):
        if ("overrun" in streamStatus):
            print('\tStream interrupted due to internal device buffer has filled up')
        elif ("user" in streamStatus):
            print('\tStream interrupted due to max file size has being exceeded')
        else:
            print("\tStopped for unknown reason")
    else:
        print("\tStream ran fully.")
    print("\nStopping the stream...")
    print("Stopping Stream: "+module.sendCommand("rec stop")) # Stop the stream and wait for the stream to have finished.
    while not "stopped" in module.sendCommand("stream?").lower():
        time.sleep(0.1)
    response = module.sendCommand("stream text all")
    output += response #Gather the last of the stream data.


    formatHeader = formatHeader.replace(", ", separator)
    output=output.replace(" ", separator).replace("eof", "").replace("\r\n","\n")


    print("\n\n"+str(formatHeader)+"\n"+str(output)+"\n\n") # Comment this out if you don't want to see the output in console.
    print("Outputting to file: "+str(fileName))
    with open(fileName, 'w') as f:
        f.write(formatHeader + '\n'+output)



    print("\nQIS SIMPLE STREAM Example - Complete!\n\n")
    if closeQisAtEndOfTest == True:
        closeQis()


if __name__ == "__main__":
    main()
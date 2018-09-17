import time, os
from quarchpy import ( requiredQuarchpyVersion,
                     isQpsRunning, startLocalQps, quarchQPS, qpsInterface, GetQpsModuleSelection, 
                     quarchDevice,
                     runFIO)

#if not requiredQuarchpyVersion ("1.3.4"):
#            raise ValueError ("quarchpy reported version is not new enough for this script!")

def checkUserInput(userVar):
    if userVar is None:
        raise ValueError('\nPlease set up this variable at the start of the main function.\n')

# Path where stream will be saved
streamPath = os.path.dirname(os.path.realpath(__file__))
checkUserInput(streamPath)

# Location of .fio file
fioFile = os.getcwd() + "\jobFileExample.fio"
checkUserInput(fioFile)

# Launch FIO in selected mode [arg|file]
#    - arg : will use a dictionary (or list of dictionaries) to run one (or several) FIO jobs for each variable
#    - file : will use a .fio file to load the arguments
runMode = "arg"
checkUserInput(fioFile)



def main():

    if 'filename' in open(fioFile).read():
        print("This script will not work as intended with the argument \'filename\' in file: " + fioFile)
        return

    # Display title text
    print ("\n################################################################################")
    print ("\n                           QUARCH TECHNOLOGY                        \n\n  ")
    print ("Automated power and performance data acquisition with Quarch Power Studio.   ")
    print ("\n################################################################################\n")  

    # Checks is QPS is running on the localhost
    if not isQpsRunning():
    # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps(keepQisRunning=True)

    # Open an interface to local QPS
    myQps = qpsInterface()
    
    # Module to work with
    myDeviceID = GetQpsModuleSelection (myQps)

    # Create a Quarch device connected via QPS
    myQuarchDevice = quarchDevice (myDeviceID, ConType = "QPS")
    
    # Upgrade Quarch device to QPS device
    myQpsDevice = quarchQPS(myQuarchDevice)
    myQpsDevice.openConnection()

    # Prints out connected module information        
    print ("MODULE CONNECTED: \n" + myQpsDevice.sendCommand ("*idn?"))
    
    # Setup the voltage mode and enable the outputs
    setupPowerOutput (myQpsDevice)
    
    # Get the required averaging rate from the user.  This sets the resolution of data to record        
    averaging = userInput("\n>>> Enter the average rate [32k]: ", "32k")
    
    # Set the averaging rate to the module
    myQpsDevice.sendCommand ("record:averaging " + averaging)

    # Start a stream, using the local folder of the script and a time-stamp file name in this example
    fileName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())        
    myStream = myQpsDevice.startStream (streamPath + "\\" + fileName)

    # Create new custom channels to plot IO results
    myStream.createChannel ('read_iops', 'IOPS', 'IOPS', "Yes")
    myStream.createChannel ('write_iops', 'IOPS', 'IOPS', "Yes")

    user_data = ["read_iops","write_iops"]
    
    fioCallbacks = {"TEST_START": notifyTestStart,
                    "TEST_END": notifyTestEnd,
                    "TEST_RESULT": notifyTestPoint}
    
  
    #Change / add arguments as required. JOB name should always be last added
    arguments = {"directory":"G\:\Testing", 
               "rw":"randread",           
               "size":"128m",             
               "runtime":"5",             
               "output":"testFile",
               "status-interval":"1",     
               "name":"job1"}


    #job2 = {"directory":"G\:\Testing", 
    #           "rw":"randread",           
    #           "size":"128m",             
    #           "runtime":"5",             
    #           "output":"mattsfile",
    #           "status-interval":"1",     
    #           "name":"job2"}


    #arguments={job1,job2}
                                 
    runFIO(myStream,
           runMode,
           fioCallbacks,
           user_data,
           arguments,                     
           fioFile)                     

    # End the stream after a few seconds of idle
    time.sleep(5)

    myStream.stopStream()

def notifyTestStart (myStream, timeStamp, testDescription):
    myStream.addAnnotation("<<text>TEST STARTED</text><extraText>" + testDescription + "</extraText>>", timeStamp)


def notifyTestEnd (myStream, timeStamp, testName="END"):
    #breaking data input to graph between tests
    myStream.addDataPoint('read_iops', 'IOPS', "endSeq" , timeStamp )
    myStream.addDataPoint('write_iops', 'IOPS', "endSeq" , timeStamp)

    myStream.addAnnotation(testName, timeStamp)

def notifyTestPoint (myStream, timeStamp, dataValues):
    myStream.addDataPoint('read_iops', 'IOPS', dataValues['read_iops'], timeStamp)
    myStream.addDataPoint('write_iops', 'IOPS', dataValues['write_iops'], timeStamp)


def setupPowerOutput (myModule):
    # Output mode is set automatically on HD modules using an HD fixture, otherwise we will chose 5V mode for this example
    if "DISABLED" in myModule.sendCommand("config:output Mode?"):
        try:
            drive_voltage = raw_input("\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3]: ") or "3V3"
        except NameError:
            drive_voltage = input("\n Either using an HD without an intelligent fixture or an XLC.\n \n>>> Please select a voltage [3V3]: ") or "3V3"

        myModule.sendCommand("config:output:mode:"+ drive_voltage)
    
    # Check the state of the module and power up if necessary
    powerState = myModule.sendCommand ("run power?")
    # If outputs are off
    if "OFF" in powerState:
        # Power Up
        print ("\n Turning the outputs on:"), myModule.sendCommand ("run:power up"), "!"

def userInput(text, orStr=""):
    try:
        return raw_input (text) or orStr
    except NameError:
        return input (text) or orStr        

if __name__=="__main__":
    main()

import time
from quarchpy import ( requiredQuarchpyVersion,
                     isQpsRunning, startLocalQps, quarchQPS, qpsInterface, 
                     quarchDevice,
                     runFIO,)

if not requiredQuarchpyVersion ("1.3.4"):
            raise ValueError ("quarchpy reported version is not new enough for this script!")

# Path where stream will be saved
streamPath = "C:\Users\pleao\Desktop\quarchpy"

# Module to work with
myDeviceID = "usb:QTL1999-02-001"

def main():

    # Checks is QPS is running on the localhost
    if not isQpsRunning():
    # Start the version on QPS installed with the quarchpy, otherwise use the running version
        startLocalQps(keepQisRunning=True)

    # Open an interface to local QPS
    myQps = qpsInterface()   

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

    #TODO: remove hardcoded path 
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
    #TODO: ju533a
    #- create a way to add more than one job by creating more than one varible
    #- create a "global" variable type  
    arguments = {"directory":"D\:\TEST", 
                "rw":"randread",           
                "size":"128m",             
                "runtime":"5",             
                "output":"testoutput_file",
                "status-interval":"1",     
                "name":"job1"}
    
    ##job2 = {"directory":"D\:\TEST", 
    #            "rw":"randread",           
    #            "size":"128m",             
    #            "runtime":"5",             
    #            "output":"testoutput_file",
    #            "status-interval":"1",     
    #            "name":"job2"}

    #arguments = [job1, job2]

    # TODO: implement a way to switch between modes - consider tuple of dictionaries and order of arguments in start_fio                                      
    runFIO(myStream,                      
           fioCallbacks,                  
           arguments,                     
           user_data)                     

    # End the stream after a few seconds of idle
    time.sleep(5)
    myStream.stopStream()

def notifyTestStart (myStream, timeStamp, testDescription):
    myStream.addAnnotation("<<text>TEST START</text><extraText>"+testDescription+"</extraText>>", timeStamp)

def notifyTestEnd (myStream, timeStamp, testName="END"):
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

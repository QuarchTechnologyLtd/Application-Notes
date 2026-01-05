'''
Implements basic control over lspci utilities, so that we can identify and check the
status of PCIe devices on the host

########### VERSION HISTORY ###########

25/04/2018 - Andy Norrie    - First version
12/05/2021 - Matt Holsey    - Bug fixed drive detection / comparison

####################################
'''
import ctypes
import os
import platform
import time
# from pySMART import DeviceList
from subprocess import Popen, PIPE

'''
Lists all PCIe devices on the bus
'''

class tempDevice(object):

    def __init__(self, name, identity1, identity2):
        self.name = name
        self.identity1 = identity1 
        self.identity2 = identity2
    

def getSataDevices():

    devices = []

    #process to find all devices
    cmd = Popen('smartctl --scan-open', shell=True,
                stdout=PIPE, stderr=PIPE)
    _stdout, _stderr = cmd.communicate()

    #get's only Ata (sata) devices - REMOVES SCSI
    for line in _stdout.split(str.encode('\n')):
        if str.encode("ATA device") in line:
            devices.append(bytes.decode(line))


    devicesSorted = []

    for device in devices:
        #command smartctl -a /dev/sda1
        cmd = Popen('smartctl -a ' + device[:device.index(' ')], shell=True,
                stdout=PIPE, stderr=PIPE)
        _stdout, _stderr = cmd.communicate()
        time.sleep(0.1)
        device = device[:device.index(' ')]
        devInfo = bytes.decode(_stdout)
        devInfo = devInfo.split('\n')
        identify1 = devInfo[4][devInfo[4].index(':') + 1:]
        identify2 = devInfo[5][devInfo[5].index(':') + 1:]

        tempDev = tempDevice(device.strip(), identify1.strip(), identify2.strip())
        
        devicesSorted.append(tempDev)
        
    

   # Return the list
    return devicesSorted


'''
Checks if the given device string is visible on the bus
'''
def devicePresent (deviceStr):

    # Get current device list
    deviceList = getSataDevices ()

    # Loop through devices and see if our module is there
    for sataStr in deviceList:
        if str(deviceStr.name) in str(sataStr.name):
            return True
    return False

'''
Prompts the user to view the list of PCIe devices and select the one to work with
'''
def pickSataTarget ():

    # Get the curent devices
    deviceList = getSataDevices ()

    print ("Select from the detected devices:")
    print ("")

    # Print the list of devices
    count = 0

    templ = "%s)  %-15s  %-30s  %-30s  "

    for sataStr in deviceList:
        #print (templ % (str(count+1) + str(sataStr.name) + sataStr.identity1 + sataStr.identity2))
        print (templ % (str(count+1), str(sataStr.name), sataStr.identity1, sataStr.identity2))
        count = count + 1

    try :
        # Ask for selection
        selection = raw_input('Enter a numerical selection and press enter >> ')
    except:
        selection = input('Enter a numerical selection and press enter >> ')
    # exit on 'q'
    if "q" in selection:
        return 0
    # Validate selection
    print(str(selection))

    if int(selection)-1 < len(deviceList):
        deviceStr = deviceList[int(selection)-1]

    # Return the device
    return deviceStr

'''
Checks if the script is runnin under admin permissions
'''
def checkAdmin():
    if platform.system() == 'Windows':
        if is_winAdmin () == False:
            print ("ERROR - Script required admin permissions to run!")
            quit ()
    else:
        if is_linuxAdmin () == False:
            print ("ERROR - Script required root permissions to run!")
            quit ()

'''
Checks for a windows admin user
'''
def is_winAdmin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

'''
Checks for a linux admin user
'''
def is_linuxAdmin():
    if os.getuid() == 0:
        return True
    else:
        return False

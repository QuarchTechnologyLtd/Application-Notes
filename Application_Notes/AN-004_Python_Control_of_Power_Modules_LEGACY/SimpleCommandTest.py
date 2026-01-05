#!/usr/bin/env python
# 21/02/17 - Anorrie
#
# Example script using pure Python code to connect to a power module over USB and perform simple command/response actions.
# This is a basic automation example, and can be used to run any standard command on the module.
#

import os
import re
import sys
import time

#set libpath = up one dir from path of script and into lib
libpath = os.path.dirname(os.path.abspath(__file__))
libpath = os.path.join(libpath, "libs")
#Insert QuarchLib folder into path
sys.path.insert(0, os.path.join(libpath,"QuarchLibs"))
#Import libusb dlls - needed on Windows systems if they are not in the default
#locations
from QuarchImportLibusb import importLibusb
importLibusb()

from QuarchUSB import *
from QuarchDevice import *

def main(argv):

    # Initialise helpers
    USBHelper = TUSBHelper()

    USBHelper.BuildDeviceList()
    QuarchComms = TQuarchUSB_IF(USBHelper.context)

    # This option connects to a Quarch device by serial number fragment
    QuarchComms.connection = USBHelper.GetMatchingDevice( serialNo = '1999' )
    #USBHelper.ListMatchingDevices('1999')
    # This option connects to the first Quarch module found on USB
    #QuarchComms.connection = USBHelper.GetMatchingDevice(venderID = QUARCH_VENDOR_ID, productID = QUARCH_PRODUCT_ID1)

    # Check the device connected
    if QuarchComms.connection == None:
        print('No Quarch units found')

    else:
        print('Selected Quarch Device '), QuarchComms.connection
        QuarchComms.OpenPort()
        print( QuarchComms.GetLastError() )

        # If we are ready
        if QuarchComms.IsPortOpen():
            #Run hello command and print output with $ removed
            print("The attached module is:")
            print( QuarchComms.RunCommand('hello?'))
        else:
            print("Failed to Connect to Device")

        #print header for voltages and curents about to be read
        print("12V             5V")
        #power down ppm
        QuarchComms.RunCommand( 'run:power:down' )
        #wait 500ms
        time.sleep(0.5)
        #set averaging to 32k samples
        volt12v = QuarchComms.RunCommand( 'rec:avg:32k' )
        #meas 12V Channel Voltage and Current, remove $, newline, and carriage return
        volt12v = QuarchComms.RunCommand( 'meas:volt:12v' )
        volt12v = re.sub('[$\n\r]', '', volt12v)
        cur12v = QuarchComms.RunCommand( 'meas:cur:12v' )
        cur12v = re.sub('[$\n\r]', '', cur12v)
        #meas 5V Channel Voltage and Current, remove $, newline, and carriage return
        volt5v = QuarchComms.RunCommand( 'meas:volt:5v' )
        volt5v = re.sub('[$\n\r]', '', volt5v)
        cur5v = QuarchComms.RunCommand( 'meas:cur:5v' )
        cur5v = re.sub('[$\n\r]', '', cur5v)

        #print results
        print(volt12v.ljust(7), cur12v.ljust(7), volt5v.ljust(7), cur5v.ljust(7))

        #power up ppm
        QuarchComms.RunCommand( 'run:power:up' )
        #wait 500ms
        time.sleep(0.5)

        #meas Voltages and Currents again
        volt12v = QuarchComms.RunCommand( 'meas:volt:12v' )
        volt12v = re.sub('[$\n\r]', '', volt12v)
        cur12v = QuarchComms.RunCommand( 'meas:cur:12v' )
        cur12v = re.sub('[$\n\r]', '', cur12v)
        volt5v = QuarchComms.RunCommand( 'meas:volt:5v' )
        volt5v = re.sub('[$\n\r]', '', volt5v)
        cur5v = QuarchComms.RunCommand( 'meas:cur:5v' )
        cur5v = re.sub('[$\n\r]', '', cur5v)    

        #print results
        print(volt12v.ljust(7), cur12v.ljust(7), volt5v.ljust(7), cur5v.ljust(7))
        
    QuarchComms.ClosePort()
    print(QuarchComms.GetLastError())

if __name__ == '__main__':
    main(sys.argv[1:])

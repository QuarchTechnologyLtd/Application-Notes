#!/usr/bin/env python
# 21/02/17 - Anorrie
#
# Example script using pure Python code to connect to a power module over USB.  It uses the recording feature to
# capture a block of data into a RAM and then download it to a CSV file for later processing.
#

import os
import sys
import time

#set libpath = up one dir from path of script and into lib
libpath = os.path.dirname(os.path.abspath(__file__))
libpath = os.path.join(libpath, "libs")
#Insert QuarchLib folder into path
sys.path.insert( 0, os.path.join(libpath,"QuarchLibs") )
#Import libusb dlls - needed on Windows systems if they are not in the default locations
from QuarchImportLibusb import importLibusb
importLibusb()

from QuarchUSB import *
from QuarchDevice import *

def main(argv):

    # Initialize helpers
    USBHelper = TUSBHelper()

    USBHelper.BuildDeviceList()
    QuarchComms = TQuarchUSB_IF( USBHelper.context )

    # This option connects to a Quarch device by serial number fragment
    # QuarchDevice.device = USBHelper.GetMatchingDevice( serialNo = '1999' )
    # This option connects to the first Quarch module found on USB
    QuarchComms.connection = USBHelper.GetMatchingDevice( venderID = QUARCH_VENDOR_ID, productID = QUARCH_PRODUCT_ID1 )

    # Check the device connected
    if QuarchComms.connection == None:
        print ('No Quarch units found')

    else:
        print ('Selected Quarch Device ', QuarchComms.connection)

        QuarchComms.OpenPort()
        print (QuarchComms.GetLastError())

        sys.stdout.write( TQuarchTerminalIO.TerminalCursor + ' ' )        # print cursor to look pretty

        # If we are ready
        if QuarchComms.IsPortOpen():
            # Send commands to set up the power module...

            # Set averaging level
            QuarchComms.VerboseSendCmd( 'rec ave 32k' )
            # Set recording trigger to manual
            QuarchComms.VerboseSendCmd( 'rec trig mode manual' )
            # Power up the outputs
            QuarchComms.VerboseSendCmd( 'power up' )
            # Start the recording
            QuarchComms.VerboseSendCmd( 'rec run' )

            print ('Recording for 10 seconds')
            i = 0
            while i < 10:
                time.sleep( 1 )
                sys.stdout.write( "." )
                sys.stdout.flush()
                i = i + 1

            print
            print            

            # Stop recording
            QuarchComms.VerboseSendCmd( 'rec stop' )

            streamBasePath = "./QuarchData"

            print ("")
            print ("")
            print ("Retreiving Data to Directory " + streamBasePath + "/")
            print ("")

            # put unit in data out mode
            QuarchComms.VerboseSendCmd( 'rec bdump' )

            # collect data from unit
            qDevice = TQuarchDevice.CreateFromCommsIF( QuarchComms )
            qDevice.SetStreamBasePath( streamBasePath )
            qDevice.SaveStreamToTextFile()
        else:
            print ("Failed to Connect to Device")

        QuarchComms.ClosePort()
        print (QuarchComms.GetLastError())


if __name__ == '__main__':
    main(sys.argv[1:])

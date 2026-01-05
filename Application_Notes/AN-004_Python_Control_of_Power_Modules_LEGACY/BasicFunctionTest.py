#!/usr/bin/env python
# Checks if libusb and libusb1 Python wrapper are available and working

import os
import sys

# Get the library path
libpath = os.path.dirname(os.path.abspath(__file__))
libpath = os.path.join(libpath, "libs")
sys.path.insert( 0, os.path.join(libpath,os.path.normpath('QuarchLibs')) )

# Import libusb wrapper library for python
from QuarchImportLibusb import importLibusb
if importLibusb() == "PASS":
    message = "LibUSB Import Test Passed."
else:
    message = "LibUSB Import Test Failed."
print (message)

# Import libUSB main DLL
try:
    import usb1
except Exception as e:
    print ("Test Failed on importing usb1 DLL")
    print (str(e))

QUARCH_VENDOR_ID = 0x16D0
QUARCH_PRODUCT_ID1 = 0x0449         # This ID applies to MOST but not all Quarch products, add additional IDs as required

def PrintDetails( device ):
    error = 0    

    try:
        vID = device.getVendorID()
    except:
        vID = "NO_VID"
    try:
        pID = device.getProductID()
    except:
        vID = "NO_PID"
    try:
        busN = device.getBusNumber()
    except:
        busN = "NO_BUS#"
    try:
        portList = device.getPortNumberList()
    except:
        portList = "NO_PORT_LIST"
    try:
        devAddr = device.getDeviceAddress()
    except:
        devAddr = "NO_DEV_ADDR"
    try:
        manufact = device.getManufacturer()
    except:
        manufact = "NO_MANF"
        error=error+1
    try:
        product = device.getProduct()
    except:
        product = "NO_PROD"
        error=error+1
    try:
        serialN = device.getSerialNumber()
    except:
        serialN = "NO_SERIAL"

    # Avoid printing devices with errors, as these are probably wierd duplicates
    if error == 0:
        print ('ID %04x:%04x' % ( vID, pID ), '->'.join(str(x) for x in ['Bus %03i' % (busN, )] + portList), 'Device', devAddr, 'Info:', manufact, ' ', product, ' ', serialN)


def main():
    context = usb1.USBContext()

    print ('')
    print ('List of Attached USB Devices:')
    for device in context.getDeviceList(skip_on_error=True):
        print ('ID %04x:%04x' % (device.getVendorID(), device.getProductID()), '->'.join(str(x) for x in ['Bus %03i' % (device.getBusNumber(), )] + device.getPortNumberList()), 'Device', device.getDeviceAddress())

    print ('')
    print ('Filtered List of Quarch IDs:')
    for device in context.getDeviceList(skip_on_error=True):
        if device.getVendorID() == QUARCH_VENDOR_ID:
            PrintDetails( device )
    
if __name__ == '__main__':
    main()
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2006, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import sys
import os
import string
import subprocess
import gettext
import time

#
# Utility functions
#

def loadFile(path):
    """Read contents of a file"""
    f = file(path)
    data = f.read()
    f.close()
    return data

#

def sysValue(path, value):
    return loadFile("%s/%s" % (path, value)).rstrip("\n")

def sysHexValue(path, value):
    tmp = loadFile("%s/%s" % (path, value)).rstrip("\n")
    if tmp.startswith("0x"):
        tmp = tmp[2:]
    return tmp


#
# Plugging Classes
#

class PCI:
    def deviceInfo(self, path):
        return (
                sysHexValue(path, "vendor"),
                sysHexValue(path, "device"),
                sysHexValue(path, "subsystem_vendor"),
                sysHexValue(path, "subsystem_device"),
                sysValue(path, "class")
        )
    
    def coldDevices(self):
        devices = []
        for dev in os.listdir("/sys/bus/pci/devices"):
            devices.append(self.deviceInfo("/sys/bus/pci/devices/%s" % dev))
        return devices
    
    def findModules(self, devpath=None):
        if devpath:
            if isinstance(devpath, basestring):
                devpath = ( devpath )
        else:
            devpath = self.coldDevices()
        
        PCI_ANY = '0xffffffff'
        
        modules = set()
        for line in file("/lib/modules/%s/modules.pcimap" % os.uname()[2]):
            if line == '' or line.startswith('#'):
                continue
            
            mod, values = line.split(None, 1)
            values = values.split()
            for dev in devpath:
                t = filter(lambda x: values[x] == PCI_ANY or values[x].endswith(dev[x]), range(4))
                if len(t) != 4:
                    continue
                if int(dev[4], 16) & int(values[5], 16) != int(values[4], 16):
                    continue
                modules.add(mod)
        return modules

#

class USB:
    def deviceInfo(self, path):
        dev = [
            "0x%s" % sysValue(path, "../idVendor"),
            "0x%s" % sysValue(path, "../idProduct"),
            "0x%s" % sysValue(path, "../bcdDevice"),
        ]
        
        if os.path.exists(path + "/bDeviceClass"):
            dev.extend((
                "0x%s" % sysValue(path, "bDeviceClass"),
                "0x%s" % sysValue(path, "bDeviceSubClass"),
                "0x%s" % sysValue(path, "bDeviceProtocol"),
            ))
        else:
            # out-of-range values
            dev.extend(('0x1000', '0x1000', '0x1000'))
        
        if os.path.exists(path + "/bInterfaceClass"):
            dev.extend((
                "0x%s" % sysValue(path, "bInterfaceClass"),
                "0x%s" % sysValue(path, "bInterfaceSubClass"),
                "0x%s" % sysValue(path, "bInterfaceProtocol"),
            ))
        else:
            # out-of-range values
            dev.extend(('0x1000', '0x1000', '0x1000'))
        
        return dev
    
    def coldDevices(self):
        devices = []
        for dev in os.listdir("/sys/bus/usb/devices"):
            if dev[0] in string.digits:
                path = os.path.realpath("/sys/bus/usb/devices/" + dev)
                if os.path.exists(os.path.join(path, "../idVendor")):
                    devices.append(self.deviceInfo(path))
        return devices
    
    def findModules(self, devpath=None):
        if devpath:
            if isinstance(devpath, basestring):
                devpath = ( devpath )
        else:
            devpath = self.coldDevices()
        
        mVendor = 0x0001
        mProduct = 0x0002
        mDevLo = 0x0004
        mDevHi = 0x0008
        mDevClass = 0x0010
        mDevSubClass = 0x0020
        mDevProto = 0x0040
        mIntClass = 0x0080
        mIntSubClass = 0x0100
        mIntProto = 0x0200
        
        modules = set()
        for line in file("/lib/modules/%s/modules.usbmap" % os.uname()[2]):
            if line == '' or line.startswith('#'):
                continue
            
            mod, flags, values = line.split(None, 2)
            flags = int(flags, 16)
            values = values.split()
            for dev in devpath:
                if flags & mVendor and dev[0] != values[0]:
                    continue
                if flags & mProduct and dev[1] != values[1]:
                    continue
                if flags & mDevLo and int(dev[2], 16) < int(values[2], 16):
                    continue
                if flags & mDevHi and int(dev[2], 16) < int(values[3], 16):
                    continue
                if flags & mDevClass and dev[3] != values[4]:
                    continue
                if flags & mDevSubClass and dev[4] != values[5]:
                    continue
                if flags & mDevProto and dev[5] != values[6]:
                    continue
                if flags & mIntClass and dev[6] != values[7]:
                    continue
                if flags & mIntSubClass and dev[7] != values[8]:
                    continue
                if flags & mIntProto and dev[8] != values[9]:
                    continue
                modules.add(mod)
        return modules

#

class PNP:
    def deviceInfo(self, sysid):
        vendor = sysid[:3]
        vendor = hex((ord(vendor[0]) & 0x3f) << 2 |
            (ord(vendor[1]) & 0x18) >> 3 |
            (ord(vendor[1]) & 0x07) << 13 |
            (ord(vendor[2]) & 0x1f) << 8)
        device = sysid[3:]
        device = "0x" + device[2:] + device[:2]
        return (device, vendor)
    
    def coldDevices(self):
        devices = []
        for dev in os.listdir("/sys/bus/pnp/devices"):
            devids = sysValue("/sys/bus/pnp/devices/" + dev, "id").split('\n')
            for id in devids:
                devices.append(self.deviceInfo(id))
        return devices
    
    def findModules(self, devpath=None):
        if devpath:
            if isinstance(devpath, basestring):
                devpath = ( devpath )
        else:
            devpath = self.coldDevices()
        
        modules = set()
        for line in file("/lib/modules/%s/modules.usbmap" % os.uname()[2]):
            if line == '' or line.startswith('#'):
                continue
            
            mod, vendor, device, rest = line.split(None, 3)
            for dev in devpath:
                if vendor == dev[1] and device == dev[0]:
                    modules.append(mod)
        
        return modules


# List of plugging classes, in coldstart order
pluggers = ( PNP, PCI, USB )


#
# Module functions
#

def blackList():
    blacks = set()
    for line in file("/etc/hotplug/blacklist"):
        line = line.rstrip('\n')
        if line == '' or line.startswith('#'):
            continue
        blacks.add(line)
    return blacks

def tryModule(modname):
    f = file("/dev/null", "w")
    ret = subprocess.call(["/sbin/modprobe", "-n", modname], stdout=f, stderr=f)
    if ret == 0:
        ret = subprocess.call(["/sbin/modprobe", modname], stdout=f, stderr=f)


#
# Main Functions
#

def coldPlug():
    blacks = blackList()
    
    for class_ in pluggers:
        plug = class_()
        for mod in plug.findModules():
            if not mod in blacks:
                tryModule(mod)

def debug():
    for class_ in pluggers:
        plug = class_()
        print list(plug.findModules())
    
    print "Blacklist:", list(blackList())


#
# Command line driver
#

if __name__ == "__main__":
    debug()
    #coldPlug()

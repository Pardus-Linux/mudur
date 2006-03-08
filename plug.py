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
import subprocess
import gettext
import time

def loadFile(path):
    """Read contents of a file"""
    f = file(path)
    data = f.read()
    f.close()
    return data

#

def pciDevice(dev):
        pci_vendor = loadFile("%s/vendor" % dev)[2:].strip("\n")
        pci_device = loadFile("%s/device" % dev)[2:].strip("\n")
        pci_sub_vendor = loadFile("%s/subsystem_vendor" % dev)[2:].strip("\n")
        pci_sub_device = loadFile("%s/subsystem_device" % dev)[2:].strip("\n")
        pci_class = loadFile("%s/class" % dev).strip("\n")
        return (pci_vendor, pci_device, pci_sub_vendor, pci_sub_device, pci_class)

def pciColdDevices():
    devices = []
    for dev in os.listdir("/sys/bus/pci/devices"):
        devices.append(pciDevice("/sys/bus/pci/devices/%s" % dev))
    return devices

def pciModules(devices):
    PCI_ANY = '0xffffffff'
    
    modules = set()
    for mod in file("/lib/modules/%s/modules.pcimap" % os.uname()[2]):
        if mod != '' and not mod.startswith('#'):
            mod = mod[:].split()
            for dev in devices:
                if mod[1] != PCI_ANY and not mod[1].endswith(dev[0]):
                    continue
                if mod[2] != PCI_ANY and not mod[2].endswith(dev[1]):
                    continue
                if mod[3] != PCI_ANY and not mod[3].endswith(dev[2]):
                    continue
                if mod[4] != PCI_ANY and not mod[4].endswith(dev[3]):
                    continue
                if int(dev[4], 16) & int(mod[6], 16) != int(mod[5], 16):
                    continue
                modules.add(mod[0])
    return modules

devs = pciColdDevices()
print pciModules(devs)

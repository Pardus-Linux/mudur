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

def blackList():
    blacks = set()
    # Unlike env.d and modules.d, blacklist is not generated
    # from blacklist.d, they all used together
    if os.path.exists("/etc/hotplug/blacklist"):
        for line in file("/etc/hotplug/blacklist"):
            line = line.rstrip('\n')
            if line == '' or line.startswith('#'):
                continue
            blacks.add(line)
    if os.path.exists("/etc/hotplug/blacklist.d"):
        for name in os.listdir("/etc/hotplug/blacklist.d"):
            for line in file(os.path.join("/etc/hotplug/blacklist.d", name)):
                line = line.rstrip('\n')
                if line == '' or line.startswith('#'):
                    continue
                blacks.add(line)
    return blacks

def tryModule(modname):
    f = file("/dev/null", "w")
    ret = subprocess.call(["/sbin/modprobe", "-n", modname], stdout=f, stderr=f)
    if ret == 0:
        ret = subprocess.call(["/sbin/modprobe", "-q", modname], stdout=f, stderr=f)

def loadModules(modules):
    blacks = blackList()
    for mod in modules:
        if not mod in blacks:
            tryModule(mod)


#
# Plugger classes
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
            devices = (self.deviceInfo(devpath), )
        else:
            devices = self.coldDevices()
        
        PCI_ANY = '0xffffffff'
        
        modules = set()
        for line in file("/lib/modules/%s/modules.pcimap" % os.uname()[2]):
            if line == '' or line.startswith('#'):
                continue
            
            mod, values = line.split(None, 1)
            values = values.split()
            for dev in devices:
                t = filter(lambda x: values[x] == PCI_ANY or values[x].endswith(dev[x]), range(4))
                if len(t) != 4:
                    continue
                if int(dev[4], 16) & int(values[5], 16) != int(values[4], 16):
                    continue
                modules.add(mod)
        return modules
    
    def hotPlug(self, action, devpath, env):
        if action != "add" or not devpath:
            return
        loadModules(self.findModules("/sys" + devpath))

#

class FireWire:
    def deviceInfo(self, devpath):
        return (
            int(sysValue(path, "vendor_id"), 16),
            int(sysValue(path, "model_id"), 16),
            int(sysValue(path, "specifier_id"), 16),
            int(sysValue(path, "version"), 16),
        )
    
    def findModules(self, devpath):
        dev = self.deviceInfo(devpath)
        modules = set()
        for line in file("/lib/modules/%s/modules.ieee1394map" % os.uname()[2]):
            if line == '' or line.startswith('#'):
                continue
            
            mod, rest = line.split(None, 1)
            vals = map(lambda x: int(x, 16), rest.split())
            
            if vals[0] & 1 and vals[1] != dev[0]:
                continue
            
            if vals[0] & 4 and vals[3] != dev[2]:
                continue
            
            if vals[0] & 8 and vals[4] != dev[3]:
                continue
            
            modules.add(mod)
        
        return modules
    
    def hotPlug(self, action, devpath, env):
        if action != "add" or not devpath:
            return
        loadModules(self.findModules(devpath))

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
        if not os.path.exists("/sys/bus/usb/devices"):
            return set()
        
        if devpath:
            devices = (self.deviceInfo(devpath), )
        else:
            devices = self.coldDevices()
        
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
            for dev in devices:
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
    
    def hotPlug(self, action, devpath, env):
        if action != "add" or not devpath:
            return
        loadModules(self.findModules("/sys" + devpath))

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
            # no hotplug for PNP
            return []
        else:
            devices = self.coldDevices()
        
        modules = set()
        for line in file("/lib/modules/%s/modules.usbmap" % os.uname()[2]):
            if line == '' or line.startswith('#'):
                continue
            
            mod, vendor, device, rest = line.split(None, 3)
            for dev in devices:
                if vendor == dev[1] and device == dev[0]:
                    modules.append(mod)
        
        return modules
    
    def hotPlug(self, action, devpath, env):
        # No hotplug possibility for ISA PNP devices
        pass

#

class SCSI:
    def findModules(self, devpath):
        modules = set()
        while not os.path.exists("/sys" + devpath + "/type"):
            time.sleep(0.1)
        
        # constants from scsi/scsi.h
        type = loadFile("/sys" + devpath + "/type").rstrip("\n")
        if type == "0":
            # disk
            modules.add("sd_mod")
        elif type == "1":
            # tape
            modules.add("st")
        elif type == "4":
            # worm
            modules.add("sr_mod")
        elif type == "5":
            # cdrom
            modules.add("sr_mod")
        elif type == "7":
            # mod
            modules.add("sd_mod")
        
        return modules
    
    def hotPlug(self, action, devpath, env):
        if action != "add" or not devpath:
            return
        loadModules(self.findModules(devpath))

#

class CPU:
    def __init__(self):
        self.vendor = "unknown"
        self.family = None
        self.model = None
        self.flags = []
        for line in file("/proc/cpuinfo"):
            if line.startswith("vendor_id"):
                self.vendor = line.split(":")[1].strip()
            elif line.startswith("cpu family"):
                self.family = int(line.split(":")[1].strip())
            elif not self.model and line.startswith("model"):
                self.model = int(line.split(":")[1].strip())
            elif line.startswith("flags"):
                self.flags = line.split(":", 1)[1].strip().split()
    
    def _find_pci(self, vendor, device):
        path = "/sys/bus/pci/devices"
        for item in os.listdir(path):
            ven = file(os.path.join(path, item, "vendor")).read().rstrip("\n")
            dev = file(os.path.join(path, item, "device")).read().rstrip("\n")
            if ven == vendor and dev == device:
                return item
        return None
    
    def _detect_speedstep(self):
        # FIXME: implement this
        return 0
    
    def _detect_ich(self):
        ich = 0
        if self._find_pci("0x8086", "0x24cc"):
            # ICH4-M
            ich = 4
        if self._find_pci("0x8086", "0x248c"):
            # ICH3-M
            ich = 3
        if self._find_pci("0x8086", "0x244c"):
            # ICH2-M
            # has trouble with old 82815 host bridge revisions
            if not self._find_pci("0x8086", "0x"):
                ich = 2
        return ich
    
    def findModules(self):
        modules = set()
        
        if self.vendor == "GenuineIntel":
            # Pentium M, Enhanced SpeedStep
            if "est" in self.flags:
                modules.add("speedstep-centrino")
            # P4 and XEON processors with thermal control
            elif "acpi" in self.flags and "tm" in self.flags:
                modules.add("p4-clockmod")
            # SpeedStep
            elif self._detect_speedstep():
                # SpeedStep ICH, PIII-M and P4-M with ICH2/3/4 southbridges
                if self._detect_ich():
                    modules.add("speedstep-ich")
        
        elif self.vendor == "AuthenticAMD":
            # Mobile K6-1/2 CPUs
            if self.family == 5 and (self.model == 12 or self.model == 13):
                modules.add("powernow-k6")
            # Mobile Athlon/Duron
            elif self.family == 6:
                modules.add("powernow-k7")
            # AMD Opteron/Athlon64
            #elif lala:
            #    modules.add("powernow-k8")
        
        elif self.vendor == "CentaurHauls":
            # VIA Cyrix III Longhaul
            if self.family == 6:
                if self.model >= 6 and self.model <= 9:
                    modules.add("longhaul")
        
        elif self.vendor == "GenuineTMx86":
            # Transmeta LongRun
            if "longrun" in self.flags:
                modules.add("longrun")
        
        return modules
    
    def coldModules(self):
        if os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/"):
            return set()
        return self.findModules()


#

class Firmware:
    def hotPlug(self, action, devpath, env):
        # FIXME: lame code, almost copied directly from firmware.agent
        devpath = "/sys" + devpath
        firm = "/lib/firmware/" + env["FIRMWARE"]
        loading = devpath + "/loading"
        if not os.path.exists(loading):
            time.sleep(1)
        
        f = file(loading, "w")
        if not os.path.exists(firm):
            f.write("-1\n")
            f.close()
            return
        f.write("1\n")
        f.close()
        import shutil
        shutil.copy(firm, devpath + "/data")
        f = file(loading, "w")
        f.write("0\n")
        f.close()


# List of plugger classes, in coldstart order
cold_pluggers = ( CPU, PNP, PCI, USB )
# Mapping of hot plugger classes
hot_pluggers = {
    "pci": PCI,
    "usb": USB,
    "ieee1394": FireWire,
    "scsi": SCSI,
    "firmware": Firmware,
}


#
# Main Functions
#

def coldPlug():
    modules = set()
    for class_ in cold_pluggers:
        plug = class_()
        try:
            tmp = plug.coldModules()
        except:
            tmp = plug.findModules()
        modules = modules.union(tmp)
    modules = modules.difference(blackList())
    for mod in modules:
        tryModule(mod)

def hotPlug(type, env):
    if hot_pluggers.has_key(type):
        if env.has_key("DEVPATH") and env.has_key("ACTION"):
            plugger = hot_pluggers[type]()
            plugger.hotPlug(env["ACTION"], env["DEVPATH"], env)

def debug():
    for class_ in cold_pluggers:
        plug = class_()
        print list(plug.findModules())
    
    print "Blacklist:", list(blackList())


#
# Command line driver
#

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--debug":
        debug()
    
    elif len(sys.argv) == 2 and sys.argv[1] == "--coldplug":
        coldPlug()
    
    else:
        hotPlug(sys.argv[1], os.environ)

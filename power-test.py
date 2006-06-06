#!/usr/bin/python
# -*- coding: utf-8 -*-
#

import os


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
            #elif lala:
            #    modules.add("powernow-k8")
        return modules



cpu = CPU()
print cpu.findModules()

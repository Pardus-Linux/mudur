#!/usr/bin/python
# -*- coding: utf-8 -*-
#

class CPU:
    def __init__(self):
        self.vendor = "unknown"
        self.model = None
        self.flags = []
        for line in file("/proc/cpuinfo"):
            if line.startswith("vendor_id"):
                self.vendor = line.split(":")[1].strip()
            elif not self.model and line.startswith("model"):
                self.model = int(line.split(":")[1].strip())
            elif line.startswith("flags"):
                self.flags = line.split(":", 1)[1].strip().split()
    
    def findModules(self):
        modules = set()
        if self.vendor == "GenuineIntel":
            if "est" in self.flags:
                modules.add("speedstep-centrino")
            if "acpi" in self.flags and "acc" in self.flags:
                modules.add("p4-clockmod")
        elif self.vendor == "AuthenticAMD":
            if self.model == 5 or self.model == 12 or self.model == 13:
                modules.add("powernow-k6")
            elif self.model == 6:
                modules.add("powernow-k7")
            #elif lala:
            #    modules.add("powernow-k8")
        return modules



cpu = CPU()
print cpu.findModules()

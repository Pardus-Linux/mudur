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
import time
import subprocess

def log(msg):
    path = "/dev/muavin.debug"
    if os.path.exists(path):
        file(path, "a").write(msg)

class Modalias:
    def coldAliases(self):
        aliases = []
        for root, dirs, files in os.walk("/sys", topdown=False):
            if "modalias" in files:
                path = os.path.join(root, "modalias")
                aliases.append(file(path).read().rstrip("\n"))
        return aliases

    def _match(self, match, alias, mod):
        # bu garip fonksiyon pythonun re ve fnmatch modullerinin
        # acayip yavas olmasindan turedi, 5 sn yerine 0.5 saniyede
        # islememizi sagliyor
        # C library deki fnmatch'i direk kullanabilsek daha hizli
        # ve temiz olacak bu isler
        i = 0
        while True:
            if i >= len(match):
                return alias == ""
            part = match[i]
            if not alias.startswith(part):
                return False
            alias = alias[len(part):]
            i += 1
            if i >= len(match):
                return alias == ""
            part = match[i]
            if part == "" and i + 1 == len(match):
                return True
            j = alias.find(part)
            if j == -1:
                return False
            alias = alias[j:]

    def aliasModules(self, aliases):
        modules = set()
        if len(aliases) == 0:
            return modules
        path = "/lib/modules/%s/modules.alias" % os.uname()[2]
        if not os.path.exists(path):
            # FIXME: log this as error somewhere
            return modules
        for line in file(path):
            try:
                cmd, match, mod = line.split()
            except ValueError:
                continue
            a = match.split("*")
            for alias in aliases:
                if self._match(a, alias, mod):
                    modules.add(mod)
        return modules

    def plug(self, current, env=None):
        aliases = []
        if env:
            if env.has_key("MODALIAS"):
                aliases = [env["MODALIAS"]]
            else:
                return
        else:
            aliases = self.coldAliases()
        mods = self.aliasModules(aliases)
        current.update(mods)

    def debug(self):
        aliases = self.coldAliases()
        mods = self.aliasModules(aliases)
        print "Modules: %s" % ", ".join(mods)


class PNP:
    def detect(self):
        path = "/sys/bus/pnp/devices"
        if os.path.exists(path):
            for dev in os.listdir(path):
                # For now, just a special case for parallel port driver
                # ISAPNP probing is trickier than it seems
                devids = file(os.path.join(path, dev, "id")).read().rstrip("\n")
                for id in devids.split("\n"):
                    if id == "PNP0400" or id == "PNP0401":
                        return [ "parport_pc", "lp" ]
        return []

    def plug(self, current, env=None):
        if env:
            # ISA bus doesn't support hotplugging
            return

        current.update(self.detect())

    def debug(self):
        print "ISAPNP: %s" % ", ".join(self.detect())


class SCSI:
    # Type constants from <scsi/scsi.h>
    modmap = {
        "0": ["sd_mod"],
        "1": ["st"],
        "4": ["sr_mod"],
        "5": ["sr_mod"],
        "7": ["sd_mod"],
    }

    def detect(self, devpath):
        path = "/sys" + devpath + "/type"
        # If type information is not ready, wait a bit
        timeout = 3
        while timeout > 0 and not os.path.exists(path):
            time.sleep(0.1)
            timeout -= 0.1

        type = file(path).read().rstrip("\n")
        return self.modmap.get(type, None)

    def plug(self, current, env=None):
        if not env or env.get("ACTION", "") != "add" or env.get("SUBSYSTEM", "") != "scsi":
            return
        mods = self.detect(env["DEVPATH"])
        if mods:
            current.update(mods)

    def debug(self):
        pass


class Firmware:
    def plug(self, current, env=None):
        if not env or env.get("SUBSYSTEM", "") != "firmware":
            return
        # FIXME: lame code, almost copied directly from firmware.agent
        devpath = "/sys" + env["DEVPATH"]
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

    def debug(self):
        pass

class MMC:
    def plug(self, current, env=None):
        if not env or env.get("SUBSYSTEM", "") != "mmc":
            return
        current.add("mmc_block")

    def debug(self):
        pass

class CPU:
    def __init__(self):
        self.vendor = "unknown"
        self.family = None
        self.model = None
        self.name = ""
        self.flags = []
        for line in file("/proc/cpuinfo"):
            if line.startswith("vendor_id"):
                self.vendor = line.split(":")[1].strip()
            elif line.startswith("cpu family"):
                self.family = int(line.split(":")[1].strip())
            elif line.startswith("model") and not line.startswith("model name"):
                self.model = int(line.split(":")[1].strip())
            elif line.startswith("model name"):
                self.name = line.split(":")[1].strip()
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

    def _detect_acpi_pps(self):
        # NOTE: This may not be a correct way to detect this
        if os.path.exists("/proc/acpi/processor/CPU0/info"):
            for line in file("/proc/acpi/processor/CPU0/info"):
                if line.startswith("power management"):
                    if line.split(":")[1].strip() == "yes":
                        return True
        return False

    def detect(self):
        modules = set()
        if self.vendor == "GenuineIntel":
            # FIXME: For kernel's 2.6.19+ speedstep_centrino merged with acpi_cpufreq
            # speedstep-centrino with X86_SPEEDSTEP_CENTRINO_ACPI config is deprecated.
            # Use X86_ACPI_CPUFREQ (acpi-cpufreq) instead.
            # Pentium M, Enhanced SpeedStep
            if "est" in self.flags:
                modules.add("speedstep_centrino")
            # Some kind of Mobile Pentium
            elif self.name.find("Mobile") != -1:
                # ACPI Processor Performance States
                if self._detect_acpi_pps():
                    modules.add("acpi_cpufreq")
                # SpeedStep ICH, PIII-M and P4-M with ICH2/3/4 southbridges
                elif self._detect_ich():
                    modules.add("speedstep_ich")
                # P4 and XEON processors with thermal control
                # NOTE: Disabled for now, I'm not sure if this does more
                # harm than good
                #elif "acpi" in self.flags and "tm" in self.flags:
                #    modules.add("p4-clockmod")

        elif self.vendor == "AuthenticAMD":
            # Mobile K6-1/2 CPUs
            if self.family == 5 and (self.model == 12 or self.model == 13):
                modules.add("powernow_k6")
            # Mobile Athlon/Duron
            elif self.family == 6:
                modules.add("powernow_k7")
            # AMD Opteron/Athlon64
            elif self.family == 15:
                modules.add("powernow_k8")

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

    def plug(self, current, env=None):
        if env:
            return
        if os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/"):
            # User already specified a frequency module in
            # modules.autoload.d or compiled it into the kernel
            return
        mods = self.detect()
        if len(mods) > 0:
            mods.add("cpufreq_userspace")
            mods.add("cpufreq_powersave")
            mods.add("cpufreq_ondemand")
        current.update(mods)

    def debug(self):
        print "CPU: %s" % ", ".join(self.detect())


class DVB:
    def plug(self, current, env=None):
        if "bttv" in current:
            # This card is detected over bttv module's api
            # If we have a bttv hardware, give the module a chance
            current.add("dvb_bt8xx")

    def debug(self):
        pass


#
# Main functions
#

# Order of pluggers is important!
pluggers = (
    CPU,
    PNP,
    Modalias,
    SCSI,
    DVB,
    MMC,
    Firmware,
)

def tryModule(modname):
    f = file("/dev/null", "w")
    ret = subprocess.call(["/sbin/modprobe", "-n", modname], stdout=f, stderr=f)
    if ret == 0:
        ret = subprocess.call(["/sbin/modprobe", "-q", modname], stdout=f, stderr=f)

def plug(env=None):
    log("*** Hotplug event:\n%s\n" % env)
    modules = set()
    for plugger in pluggers:
        p = plugger()
        p.plug(modules, env)
    log("*** Modules loading:\n%s\n" % modules)
    for mod in modules:
        tryModule(mod)

def debug():
    for plugger in pluggers:
        p = plugger()
        p.debug()


#
# Command line driver
#

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--debug":
        debug()

    elif len(sys.argv) == 2 and sys.argv[1] == "--coldplug":
        plug()

    else:
        # This file is written by mudur, after loading of modules in the
        # modules.autoload.d finishes, thus preventing udevtrigger events
        # from loading of other modules first. Triggered events are
        # needed to populate /dev way before module loading phase.
        if os.path.exists("/dev/.muavin"):
            plug(os.environ)

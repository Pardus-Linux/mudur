#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# /etc/fstab updater/generator
# Copyright (C) 2005-2009 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#

import os
import sys
import glob
import parted

# Default options

default_options = {
    "vfat":     ("quiet", "shortname=mixed", "dmask=007", "fmask=117", "utf8", "gid=6"),
    "ext3":     ("noatime", ),
    "ext2":     ("noatime", ),
    "ntfs-3g":  ("dmask=007", "fmask=117", "gid=6"),
    "reiserfs": ("noatime", ),
    "xfs":      ("noatime", ),
    "defaults": ("defaults", ),
}

default_mount_dir = "/mnt"

excluded_file_systems = ("proc", "tmpfs", "sysfs", "linux-swap", "swap", "nfs", "nfs4", "cifs")

pardus_labels = ("PARDUS_ROOT", "PARDUS_HOME", "PARDUS_SWAP")

# Utility functions

def blockDevices():
    devices = []
    for dev_type in ["hd*", "sd*"]:
        sysfs_devs = glob.glob("/sys/block/" + dev_type)
        for sysfs_dev in sysfs_devs:
            if not int(open(sysfs_dev + "/removable").read().strip()):
                devlink = os.readlink(sysfs_dev + "/device")
                devlink = os.path.realpath(os.path.join(sysfs_dev, "device", devlink))
                if (not "/usb" in devlink) and (not "/fw-host" in devlink):
                    devices.append("/dev/" + os.path.basename(sysfs_dev))
    devices.sort()
    return devices

def blockPartitions(dev):
    pdev = parted.getDevice(dev)
    try:
        disk = parted.Disk(device=pdev)
    except:
        # FIXME: replace with what exception could we get here, bare except sucks
        disk = parted.freshDisk(pdev, parted.diskType['msdos'])

    part = disk.getFirstPartition()
    while part:
        if part.fileSystem and part.fileSystem.type != "linux-swap":
            yield part.path, part.fileSystem.type
        part = part.nextPartition()

def blockNameByLabel(label):
    path = os.path.join("/dev/disk/by-label/%s" % label)
    if os.path.islink(path):
        return "/dev/%s" % os.readlink(path)[6:]
    else:
        return None

def getLocale():
    try:
        for line in file("/etc/env.d/03locale"):
            if "LC_ALL" in line:
                return line[7:].strip()
    except:
        pass

    return "tr_TR.UTF-8"

# Fstab classes


class FstabEntry:
    def __init__(self, line=None):
        defaults = [ None, None, "auto", "defaults", 0, 0 ]

        args = []
        if line:
            args = line.split()

        args = args[:len(args)] + defaults[len(args):]

        self.device_node = args[0]
        self.mount_point = args[1]
        self.file_system = args[2]
        self.options = args[3]
        self.dump_freq = args[4]
        self.pass_no = args[5]

    def __str__(self):
        return "%-20s %-16s %-9s %-20s %s %s" % (
            self.device_node,
            self.mount_point,
            self.file_system,
            self.options,
            self.dump_freq,
            self.pass_no
        )


class Fstab:
    comment = """# See the manpage fstab(5) for more information.
#
#   <fs>             <mountpoint>     <type>    <opts>               <dump/pass>
"""

    def __init__(self, path=None):
        if not path:
            path = "/etc/fstab"
        self.path = path
        self.entries = []
        self.partitions = None
        self.labels = {}
        for line in file(path):
            if line.strip() != "" and not line.startswith('#'):
                self.entries.append(FstabEntry(line))

    def __str__(self):
        return "\n".join(map(str, self.entries))

    def scan(self):
        self.partitions = {}
        for dev in blockDevices():
            for part, fstype in blockPartitions(dev):
                self.partitions[part] = fstype, dev
        if os.path.exists("/dev/disk/by-label"):
            for label in os.listdir("/dev/disk/by-label/"):
                self.labels[blockNameByLabel(label)] = label

    def write(self, path=None):
        if not path:
            path = self.path

        # Make sure mount points exist
        for entry in self.entries:
            if entry.mount_point != "none" and not os.path.exists(entry.mount_point):
                os.makedirs(entry.mount_point)

        f = file(path, "w")
        f.write(self.comment)
        f.write(str(self))
        f.write("\n")
        f.close()

    def removeEntry(self, device_node):
        for i, entry in enumerate(self.entries):
            if entry.device_node == device_node and entry.mount_point != "/":
                del self.entries[i]

    def addEntry(self, device_node, mount_point=None):
        if not self.partitions:
            self.scan()

        if not mount_point:
            mount_point = os.path.join(default_mount_dir, os.path.basename(device_node))

        file_system = self.partitions.get(device_node)[0]
        if file_system in ("fat16", "fat32"):
            file_system = "vfat"
        if file_system == "ntfs":
            file_system = "ntfs-3g"
        if file_system == "hfs+":
            file_system = "hfsplus"

        options = default_options.get(file_system, None)
        if not options:
            options = default_options.get("defaults")

        entry = FstabEntry()
        entry.device_node = device_node
        entry.mount_point = mount_point
        entry.file_system = file_system
        entry.options = ",".join(options)

        if file_system == "ntfs-3g":
            entry.options += ",locale=%s" % getLocale()

        self.entries.append(entry)
        return entry

    def refresh(self):
        if not self.partitions:
            self.scan()

        # Carefully remove non existing partitions
        removal = []
        for i, entry in enumerate(self.entries):
            node = entry.device_node
            if entry.mount_point == "/":
                # Root partition is never removed
                continue
            if not entry.mount_point.startswith("/mnt"):
                # Only remove partitions that were added in /mnt
                continue
            elif entry.file_system in excluded_file_systems:
                # Virtual file systems are never removed
                continue
            elif node.startswith("LABEL="):
                label = node.split("=", 1)[1]
                if label in pardus_labels:
                    # Labelled Pardus system partitions are never removed
                    continue
                if not self.partitions.has_key(blockNameByLabel(label)):
                    removal.append(node)
            else:
                if not self.partitions.has_key(node):
                    removal.append(node)
        map(self.removeEntry, removal)

        # Append all other existing non-removable partitions
        mounted = set(map(lambda x: x.device_node, self.entries))
        for part in self.partitions:
            if not part in mounted:
                if part in self.labels:
                    if "LABEL=%s" % self.labels[part] in mounted:
                        continue
                self.addEntry(part)


# Command line driver

def refresh_fstab(path=None, debug=False):
    f = Fstab(path)
    if debug:
        print "Fstab file:", f.path
        print "--- Current table ---"
        print f
    f.refresh()
    if debug:
        print "--- Refreshed table ---"
        print f
    else:
        f.write()

def main(args):
    path = None
    debug = False
    if "--debug" in args:
        args.remove("--debug")
        debug = True
    if len(args) > 0:
        path = args[0]
    refresh_fstab(path, debug)

if __name__ == "__main__":
    main(sys.argv[1:])

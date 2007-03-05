#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#

import os
import sys
import copy
import glob
import parted


comment="""# See the manpage fstab(5) for more information.
#
# <fs>      <mountpoint>         <type>    <opts>               <dump/pass>
"""

class DeviceError(Exception):
    pass

def getBlocknameByLabel(_f):
    f = os.path.join("/dev/disk/by-label/%s" % _f)
    if os.path.islink(f):
        return "/dev/%s" % os.readlink(f)[6:]
    else:
        return None

def getPartitionsOfDevice(device_path):
    """Returns all partitions of a given device but swap partition"""
    def getPartitionInfo(part):
        partition = {}
        if part.num >= 1:
            fs_name = ""
            if part.fs_type and part.fs_type.name != 'linux-swap':
                return (device_path + str(part.num), {"mount_point": None,
                                                          "file_system": part.fs_type.name,
                                                          "options": None,
                                                          "dump_freq": None,
                                                          "fs_pass_no": None})
                return partition

    dev = parted.PedDevice.get(device_path)

    try:
        disk = parted.PedDisk.new(dev)
    except:
        disk_type = parted.disk_type_get("msdos")
        disk = dev.disk_new_fresh(disk_type)

    part = disk.next_partition()
    while part:
        info = getPartitionInfo(part)
        if info:
            yield info
        part = disk.next_partition(part)

def getBlockDevices():
    """Returns a list of *non-removable* block devices attached to the system"""

    if not os.path.exists("/sys/block"):
        raise DeviceError, "sysfs not found!"

    devices = []

    for dev_type in ["hd*", "sd*"]:
        sysfs_devs = glob.glob("/sys/block/" + dev_type)
        for sysfs_dev in sysfs_devs:
            if not int(open(sysfs_dev + "/removable").read().strip()):
                devlink = os.readlink(sysfs_dev + "/device")
                if not "/usb" in devlink:
                    devices.append("/dev/" + os.path.basename(sysfs_dev))
    return devices


class FstabError(Exception):
    pass

class Fstab:
    def __init__(self, File = "/etc/fstab", debug = False):
        self.File = File
        self.Debug = debug
        self.Label = {}

        if os.path.isfile(File):
            self.content = self.__emergeContent()
        else:
            self.content = []

        # basic syntax check of the content - gonna be improved in the future.
        try:
            assert([x for x in self.content if len(x.split()) != 6] == [])
        except:
            raise FstabError, "Syntax of the fstab file doesn't seem to be correct"

        self.defaultMountDir = "/mnt"
        self.excludedFilesystems = ["proc", "tmpfs", "swap"]
        self.allDevices = getBlockDevices()

        self.defaultFileSystemOptions = {}
        self.defaultFileSystemOptions["vfat"] = ["quiet", "shortname=mixed", "dmask=007", "fmask=117", "utf8", "gid=6"]
        self.defaultFileSystemOptions["ext3"] = ["noatime"]
        self.defaultFileSystemOptions["ext2"] = ["noatime"]
        self.defaultFileSystemOptions["ntfs-3g"] = ["dmask=007", "fmask=117", "locale=tr_TR.UTF-8", "gid=6"]
        self.defaultFileSystemOptions["reiserfs"] = ["noatime"]
        self.defaultFileSystemOptions["xfs"] = ["noatime", "nobarrier"]
        self.defaultFileSystemOptions["defaults"] = ["defaults"]

        self.maplabels()
        self.update()

    def maplabels(self):
        for f in os.listdir("/dev/disk/by-label/"):
            self.Label[getBlocknameByLabel(f)] = f

    def update(self):
        self.__allPartitions, self.__fstabPartitions = {}, {}

        self.__emergeAllPartitions()
        self.__emergeFstabPartitions()

        for p in self.__fstabPartitions.keys():
            if self.__allPartitions.get(p):
                self.__allPartitions[p].update(self.__fstabPartitions[p])

    def writeContent(self, File = None):
        if not self.Debug:
            if not File:
                File = self.File
            try:
                f = open(File, "w")
            except IOError:
                # raise FstabError, "Unable to write: %s"
                print "Unable to write: %s" % File
                sys.exit(1)

            f.write(comment)
            for line in self.content:
                f.write(line)
            f.close()
        else:
            for line in self.content:
                print line.rstrip("\n")

    def __emergeContent(self):
        return [line for line in open(self.File).readlines() if not line.startswith('#') if not line.startswith("\n")]

    def __emergeAllPartitions(self):
        for dev in self.allDevices:
            for info in getPartitionsOfDevice(dev):
                self.__allPartitions[info[0]] = info[1]

    def __emergeFstabPartitions(self):
        for line in self.content:
            if line.split()[2] not in self.excludedFilesystems:
                self.__fstabPartitions[line.split()[0]] = {"mount_point": line.split()[1],
                                                        "file_system": line.split()[2], 
                                                        "options": line.split()[3].split(','), 
                                                        "dump_freq": line. split()[4], 
                                                        "fs_pass_no": line.split()[5]}

    def getFstabPartitions(self):
        return self.__fstabPartitions

    def getAvailablePartitions(self):
        ap = {}
        for p in set(self.__allPartitions) - set(self.__fstabPartitions):
            if not "LABEL=%s" % self.Label[p] in self.__fstabPartitions:
                ap[p] = copy.deepcopy(self.__allPartitions[p])
        return ap

    def addAvailablePartitions(self):
        """Adds all partitions that have no entries in fstab, 
           into fstab with default parameters"""
        for p in self.getAvailablePartitions():
            self.addFstabEntry(p, self.__allPartitions[p])

    def getDepartedPartitions(self):
        """Returns a list of partitions that have entries in fstab but also
        they do not exist anymore"""
        dp = {}
        for p in set(self.__fstabPartitions) - set(self.__allPartitions):
            if not (p.startswith("LABEL=") and getBlocknameByLabel(p[6:]) in self.__allPartitions):
                dp[p] = copy.deepcopy(self.__fstabPartitions[p])
        return dp

    def delDepartedPartitions(self):
        """Removes partitions from fstab. These partitions have entries in fstab but also
        they do not exist anymore"""
        for p in self.getDepartedPartitions():
            self.delFstabEntry(p)

    def getAllPartitions(self):
        return self.__allPartitions

    def addFstabEntry(self, partition, attr_dict = {}):
        """Adds an fstab entry for 'partition', with attributes given in 'attr_dict'"""

        if not partition:
            print "'partition' can not be null."
            return -1

        if attr_dict.get('mount_point') == None:
            attr_dict['mount_point'] = self.defaultMountDir + '/' + os.path.basename(partition)


        err = []
        if not self.__allPartitions.get(partition):
            err.append("'%s' is not an available partition.\n" % (partition))
        if self.__fstabPartitions.get(partition):
            err.append("'%s' is already in fstab\n" % (partition))
        if [p for p in self.__fstabPartitions if self.__fstabPartitions[p]['mount_point'] == attr_dict['mount_point']]:
            err.append("Mount point '%s' is already in use\n" % (attr_dict['mount_point']))
        if err:
            print err
            return -1


        if attr_dict.get('file_system') == None:
            attr_dict['file_system'] = self.__allPartitions[partition]['file_system']

        if attr_dict.get('dump_freq') == None:
            attr_dict['dump_freq'] = '0'

        if attr_dict.get('fs_pass_no') == None: 
            attr_dict['fs_pass_no'] = '0'

        # convert fat16 and fat32 to vfat..
        if attr_dict['file_system'] == 'fat16' or attr_dict['file_system'] == 'fat32':
            attr_dict['file_system'] = 'vfat'

        # convert ntfs to ntfs-3g
        if attr_dict['file_system'] == 'ntfs':
            attr_dict['file_system'] = 'ntfs-3g'

        if attr_dict.get('options') == None:
            attr_dict['options'] = self.defaultFileSystemOptions.get(attr_dict['file_system']) or self.defaultFileSystemOptions['defaults']

        if not self.Debug:
            if not os.path.exists(attr_dict['mount_point']):
                try:
                    os.mkdir(attr_dict['mount_point'])
                except OSError:
                    print ("Unable to create mount point: '%s' for '%s'" % (attr_dict['mount_point'], partition))
        else:
            pass

        self.content.append("%-11s %-20s %-9s %-20s %s %s\n" % (partition, 
                                                         attr_dict['mount_point'], 
                                                         attr_dict['file_system'], 
                                                         ','.join(attr_dict['options']), 
                                                         attr_dict['dump_freq'], 
                                                         attr_dict['fs_pass_no']))
        self.update()

    def delFstabEntry(self, partition):
        if not self.__fstabPartitions.get(partition):
            print("There is not any fstab record for '%s'.\n" % (partition))
            return -1
        else:
            for c in range(0, len(self.content)):
                if self.content[c].split()[0] == partition and self.content[c].split()[1] != "/":
                    self.content.remove(self.content[c])
                    self.update()
                    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        dbg = True
    else:
        dbg = False

    try:
        f = Fstab(File = "/etc/fstab", debug = dbg)
    except FstabError, e:
        print e
        sys.exit(-1)

    f.delDepartedPartitions()
    f.addAvailablePartitions()
    f.writeContent()


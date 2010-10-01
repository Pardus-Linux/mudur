#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess

FSTAB_PATH = "/etc/fstab"
FSTAB_HEADER = """\
# See the manpage fstab(5) for more information.
# This fstab file was created by generate-fstab on %s
#
#   <fs>             <mountpoint>     <type>     <opts>               <dump/pass>
proc                 /proc             proc      nosuid,noexec        0 0
sysfs                /sys              sysfs     defaults             0 0
debugfs              /sys/kernel/debug debugfs   defaults             0 0
tmpfs                /dev/shm          tmpfs     nodev,nosuid,noexec  0 0
""" % time.asctime()


DEFAULTS = {
    "defaults": ("defaults",),
    "reiserfs": ("noatime", ),
    "ntfs-3g":  ("dmask=007", "fmask=117", "gid=6"),
    "vfat":     ("quiet", "shortname=mixed", "dmask=007", "fmask=117", "utf8", "gid=6"),
    "swap":     ("defaults", "sw",),
    "ext4":     ("defaults", ),
    "ext3":     ("defaults", ),
    "ext2":     ("defaults", ),
    "xfs":      ("noatime", ),
}

# Debugged output switch
is_debug = sys.argv[1]=="-d" if len(sys.argv) > 1 else False

def debug(msg):
    if is_debug:
        print("DEBUG: %s" % msg)

def parse_fstab():
    """Parse /etc/fstab and return the relevant dictionary."""
    fstab = {}
    for line in open("/etc/fstab", "r").read().strip().split("\n"):
        if line and not line.startswith("#"):
            fstab[line.split()[0]] = line.split()[1:]

    return fstab

def fstab_entry(fs, mountpoint, type, opts, dumppass="0 0"):
    return "%-20s %-17s %-9s %-20s %s\n" % (fs, mountpoint, type, ",".join(opts), dumppass)

def get_partition_info():
    """Calls blkid and returns a list of dictionaries."""
    d = {}
    for dev in subprocess.Popen(["/sbin/blkid", "-c", "/dev/null"], stdout=subprocess.PIPE).communicate()[0].strip().split("\n"):
        device_node = dev.split(":")[0]
        d[device_node] = dict([(k.split("=")[0], k.split("=")[1].strip("\"'")) for k in dev.split(":")[1].strip().split()])

    return d

def get_root_partition():
    """Detects the device node of the rootfs as it's already mounted by initramfs."""
    for line in open("/proc/mounts", "r").read().strip().split("\n"):
        if line.startswith("rootfs"):
            continue
        if line.split()[1] == "/":
            return line.split()[0]

def get_home_partition():
    """Tries to detect the home partition if any using some heuristics and the current fstab."""
    # First parse current fstab to have some clue
    fstab = parse_fstab()
    for dev in fstab.keys():
        if fstab[dev][0] == "/home":
            if "LABEL=" in dev:
                label = dev.split("LABEL=")[1]
                return os.path.join("/dev", os.path.basename(os.readlink("/dev/disk/by-label/%s" % label)))
            else:
                return dev

def add_swap_partition(fstab, device_node, partition):
    if partition["TYPE"] == "swap" and partition.get("LABEL", "").startswith("PARDUS_SWAP"):
        label = partition.get("LABEL", "None")
        debug("Swap partition found at %s (LABEL %s)" % (device_node, label))
        fstab += fstab_entry(label, "none", "swap", DEFAULTS[partition.get("TYPE")])
    return fstab

def add_root_partition(fstab, device_node, partition):
    label = partition.get("LABEL", "None")
    fs = label if label!="None" else device_node
    debug("Root partition found at %s (LABEL %s)" % (device_node, label))
    fstab += fstab_entry(fs, "/", partition.get("TYPE"), DEFAULTS[partition.get("TYPE")])
    return fstab

def generate_fstab():
    partitions = get_partition_info()
    fstab = FSTAB_HEADER
    for partition in partitions.keys():
        d_part = partitions[partition]
        fstab = add_swap_partition(fstab, partition, d_part)
        if get_root_partition() == partition:
            fstab = add_root_partition(fstab, partition, d_part)
        if get_home_partition() == partition:
            fstab = add_home_partition(fstab, partition, d_part)

    return fstab


def main():
    print generate_fstab()


if __name__ == "__main__":
    main()

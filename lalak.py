#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import gettext
import time
import signal
import fcntl
import stat


def wipeTmp():
    paths = (
        "/tmp/lost+found/",
        "/tmp/quota.user/",
        "/tmp/aquota.user/",
        "/tmp/quota.group/",
        "/tmp/aquota.group/",
        "/tmp/.journal/",
    )
    
    dev = os.stat("/tmp").st_dev
    for root, dirs, files in os.walk("/tmp", topdown=False):
        special = False
        for path in paths:
            if root.startswith(path):
                special = True
                break
        #
        for name in files:
            path = os.path.join(root, name)
            if special:
                if os.stat(path).st_uid != 0:
                    print path
            else:
                print path
        #
        for name in dirs:
            path = os.path.join(root, name)
            if os.stat(path).st_dev == dev:
                if special:
                    if os.stat(path).st_uid != 0:
                        print path
                else:
                    print path



def saveUdev():
    real_devs = set()
    udev_devs = set()
    not_wanted = set(("MAKEDEV", "core", "fd", "initctl", "pts", "shm", "stderr", "stdin", "stdout"))
    
    dev = os.stat("/dev").st_dev
    for root, dirs, files in os.walk("/dev"):
        for name in files:
            st = os.lstat(os.path.join(root, name))
            mode = st.st_mode
            if st.st_dev == dev and (stat.S_ISBLK(mode) or stat.S_ISCHR(mode) or stat.S_ISLNK(mode)):
                real_devs.add(os.path.join(root, name)[5:])
    
    for name in os.listdir("/dev/.udevdb/"):
        for line in file(os.path.join("/dev/.udevdb/", name)):
            if line.startswith("S:") or line.startswith("N:"):
                udev_devs.add(line[2:].rstrip("\n"))
    
    print "\n".join(real_devs.difference(udev_devs).difference(not_wanted))





saveUdev()

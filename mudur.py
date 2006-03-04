#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Pardus boot and initialization system
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
import time

#
# Utilities
#

def loadFile(path):
    """Read contents of a file"""
    f = file(path)
    data = f.read()
    f.close()
    return data

def ensureDirs(path):
    """Create missing directories in the path"""
    if not os.path.exists(path):
        os.makedirs(path)

def symLink(linkname, destname):
    """Create a soft link"""
    if os.path.exists(linkname):
        os.unlink(linkname)
    os.symlink(destname, linkname)

def write(filename, data):
    """Write data to file"""
    f = file(filename, "w")
    f.write(data)
    f.close()

def mdate(filename):
    """Return last modification date of a file"""
    if os.path.exists(filename):
        return os.stat(filename).st_mtime
    return 0

def mdirdate(dirname):
    """Return last modification date of a directory"""
    # Directory mdate is not updated for file updates, so we check each file
    # Note that we dont recurse into subdirs, modules.d, env.d etc are all flat
    d = mdate(dirname)
    for f in os.listdir(dirname):
        d2 = mdate(os.path.join(dirname, f))
        if d2 > d:
            d = d2
    return d

def touch(filename):
    """Update file modification date, create file if necessary"""
    try:
        if os.path.exists(filename):
            os.utime(filename, None)
        else:
            file(filename, "w").close()
    except IOError, e:
        if e.errno != 13:
            raise
        else:
            return False
    except OSError, e:
        if e.errno != 13:
            raise
        else:
            return False
    return True

def capture(*cmd):
    """Capture the output of command without running a shell"""
    a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return a.communicate()

def run(*cmd):
    """Run a command without running a shell"""
    return subprocess.call(cmd)

#

class Logger:
    def __init__(self):
        self.lines = []
    
    def log(self, msg):
        self.lines.append(msg)
    
    def uptime(self):
        tmp = "uptime %s seconds." % loadFile("/proc/uptime").split()[0]
        self.lines.append(tmp)
    
    def sync(self):
        f = file("/var/log/mudur.log", "a")
        map(lambda x: f.write("%s\n" % x), self.lines)
        f.close()

logger = Logger()


class Config:
    def __init__(self):
        self.kernel = os.uname()[2].split(".")
        self.fstab = None
        self.cmdline = None
        # default options
        self.opts = {
            "language": "tr",
            "clock": "local",
        }
        # load config file if exists
        if os.path.exists("/etc/conf.d/mudur.conf"):
            data = loadFile("/etc/conf.d/mudur.conf")
            for line in data.split("\n"):
                if not line.startswith("#"):
                    t = line.split("=", 1)
                    if len(t) == 2:
                        key = t[0].strip()
                        value = t[1].strip()
                        if self.opts.has_key(key):
                            self.opts[key] = value
                        else:
                            print "Unknown option '%s' in mudur.conf!" % key
                            time.sleep(3)
    
    def get_opt(self, cmdopt):
        if not self.cmdline:
            self.cmdline = loadFile("/proc/cmdline").split()
        
        for cmd in self.cmdline:
            pos = len(cmdopt)
            if cmd == cmdopt:
                return cmd
            if cmd.startswith(cmdopt) and cmd[pos] == '=':
                return cmd[pos+1:]
        
        return None
    
    def parse_kernel_opts(self):
        lang = self.get_opt("lang")
        if lang:
            self.opts["language"] = lang
    
    def get(self, key):
        try:
            return self.opts[key]
        except:
            print "Unknown option '%s' requested" % key
            time.sleep(3)
            return None
    
    def get_mount(self, path):
        if not self.fstab:
            data = loadFile("/etc/fstab").split("\n")
            data = filter(lambda x: not (x.startswith("#") or x == ""), data)
            self.fstab = map(lambda x: x.split(), data)
        
        for ent in self.fstab:
            if len(ent) > 3 and ent[1] == path:
                return ent
        
        return None
    
    def is_virtual(self):
        return False
    
    def is_livecd(self):
        return False


config = Config()


class UI:
    def __init__(self):
        self.wait = False
        self.GOOD = '\x1b[32;01m'
        self.WARN = '\x1b[33;01m'
        self.BAD = '\x1b[31;01m'
        self.BRACKET = '\x1b[34;01m'
        self.NORMAL = '\x1b[0m'
        self.last_col = -1
        self.width = int(capture("/usr/bin/stty", "size")[0].split()[1])
    
    def _echo(self, msg, colour=None, is_error=False):
        if colour:
            sys.stdout.write(" %s*%s %s" % (colour, self.NORMAL, msg))
        else:
            sys.stdout.write(msg)
        
        if self.wait:
            time.sleep(3)
    
    def info(self, msg):
        logger.log(msg)
        self._echo(msg + "\n", self.GOOD)
    
    def warn(self, msg):
        logger.log(msg)
        self._echo(msg + "\n", self.WARN)
    
    def error(self, msg):
        logger.log(msg)
        self._echo(msg + "\n", self.BAD, True)
    
    def begin(self, msg):
        logger.log(msg)
        self._echo(msg, self.GOOD)
        self.last_col = 3 + len(msg)
    
    def end(self, error=None):
        if error:
            msg = "%s[ %s!!%s ]%s" % (self.BRACKET, self.BAD, self.BRACKET, self.NORMAL)
        else:
            msg = "%s[ %s%s%s ]%s" % (self.BRACKET, self.GOOD, "ok", self.BRACKET, self.NORMAL)
        
        self._echo("%s%s\n" % (" " * (self.width - self.last_col - len(msg)), msg))
        
        if error:
            self.error(error)
    
    def debug(self, msg):
        logger.log(msg)


ui = UI()


#

class Language:
    def __init__(self, data):
        self.keymap = data[0]
        self.font = data[1]
        self.trans = data[2]
        self.locale = data[3]
    
    def setConsole(self):
        os.system("/usr/bin/kbd_mode -u")
        os.system("/bin/loadkeys %s &> /dev/null" % self.keymap)
        os.system("/usr/bin/setfont -f %s -m %s" % (self.font, self.trans))


languages = {
    "en": Language(("us", "iso01.16", "8859-1", "en_US.UTF-8")),
    "tr": Language(("trq", "iso09.16", "8859-9", "tr_TR.UTF-8"))
}

#

def mount(part, args):
    ent = config.get_mount(part)
    if ent and len(ent) > 3:
        args = "-t %s -o %s %s %s" % (ent[2], ent[3], ent[0], ent[1])
    os.system("mount -n %s" % args)


#
# COMAR functions
#

def startServices():
    ui.begin("Starting services")
    import comar
    go = True
    while go:
        try:
            link = comar.Link()
            go = False
        except comar.Error:
            time.sleep(0.1)
    link.call("System.Service.ready")
    ui.end()


#
# Initialization functions
#

def setupUdev():
    udev_backup = "/lib/udev-state/devices.tar.bz2"
    # many video drivers require exec access in /dev
    ui.info("Mounting /dev")
    mount("/dev", "-t tmpfs -o exec,nosuid,mode=0755 udev /dev")
    ui.info("Restoring saved device states")
    if os.path.exists(udev_backup):
        run("/bin/tar", "-jxpf", udev_backup, "-C" "/dev")
    ui.info("Starting udev")
    run("/sbin/udevstart")
    # Not provided by sysfs but needed
    symLink("/dev/fd", "/proc/self/fd")
    symLink("/dev/stdin", "fd/0")
    symLink("/dev/stdout", "fd/1")
    symLink("/dev/stderr", "fd/2")
    symLink("/dev/core", "/proc/kcore")
    
    # NOTE: handle lvm here when used by pardus
    
    # Create problematic directories
    ensureDirs("/dev/pts")
    ensureDirs("/dev/shm")
    # Mark the /dev management system type
    touch("/dev/.udev")
    # Avast!
    write("/proc/sys/kernel/hotplug", "/sbin/udevsend")

def checkRoot():
    ui.begin("Remounting root filesystem read-only")
    run("/bin/mount", "-n", "-o", "remount,ro", "/")
    ui.end()
    
    ent = config.get_mount("/")
    if len(ent) > 5 and ent[5] != "0":
        ui.info("Checking root filesystem")
        t = run("/sbin/fsck", "-C", "-T", "-a", "/")
        if t == 0:
            pass
        elif t == 2 or t == 3:
            ui.info("Filesystem repaired, but reboot needed!")
            for i in range(4):
                print "\07"
                time.sleep(1)
            ui.info("Rebooting in 10 seconds ...")
            time.sleep(10)
            ui.info("Rebooting...")
            run("/sbin/reboot", "-f")
        else:
            ui.info("Filesystem couldn't be fixed :(")
    else:
        ui.info("Skipping root filesystem check (fstab's passno == 0)")
    
    ui.info("Remounting root filesystem read/write")
    if run("/bin/mount", "-n", "-o", "remount,rw", "/") != 0:
        ui.info("Root filesystem could not be mounted read/write :(")
    
    # Fix mtab
    write("/etc/mtab", "")
    run("/bin/mount", "-f", "/")
    ents = loadFile("/proc/mounts").split("\n")
    for ent in ents:
        if ent != "":
            data = ent.split()
            if config.get_mount(data[1]):
                run("/bin/mount", "-f", "-o", "remount", data[1])

def setHostname():
    khost = capture("/bin/hostname")[0].rstrip("\n")
    uhost = None
    data = loadFile("/etc/env.d/01hostname")
    i = data.find('HOSTNAME="')
    if i != -1:
        j = data.find('"',i+10)
        if j != -1:
            uhost = data[i+10:j]
    
    if khost != "" and khost != "(none)":
        # kernel already got a hostname (pxeboot or something)
        host = khost
    else:
        if uhost:
            host = uhost
        else:
            # nothing found, use the default hostname
            host = "pardus"
    
    if uhost and host != uhost:
        i = data.find('HOSTNAME="')
        if i != -1:
            j = data.find('"',i+10)
            if j != -1:
                data = data[:i+10] + host + data[j:]
        else:
            data = 'HOSTNAME="' + host + '"\n' + data
        write("/etc/env.d/01hostname", data)
    
    ui.info("Setting up hostname as '%s'" % host)
    run("/bin/hostname", host)

def modules():
    # dont fail if kernel do not have module support compiled in
    if not os.path.exists("/proc/modules"):
        return
    
    if mdirdate("/etc/modules.d") > mdate("/etc/modules.conf"):
        # FIXME: convert this script to python
        ui.begin("Calculating module dependencies")
        os.system("/sbin/modules-update &>/dev/null")
        ui.end()
    
    fn = "/etc/modules.autoload.d/kernel-%s.%s.%s" % (config.kernel[0], config.kernel[1], config.kernel[2])
    if not os.path.exists(fn):
        fn = "/etc/modules.autoload.d/kernel-%s.%s" % (config.kernel[0], config.kernel[1])
    if os.path.exists(fn):
        data = loadFile(fn).split("\n")
        data = filter(lambda x: x != "" and not x.startswith('#'), data)
        for mod in data:
            run("/sbin/modprobe", "-q", mod)

def checkFS():
    ui.info("Checking all filesystems")
    t = run("/sbin/fsck", "-C", "-T", "-R", "-A", "-a")
    if t == 0:
        pass
    elif t >= 2 and t <= 3:
        ui.info("Filesystem errors corrected")
    else:
        ui.info("Fsck could not correct all errors, manual repair needed")

def localMount():
    ui.info("Mounting local filesystems")
    run("/bin/mount", "-at", "noproc,noshm")
    ui.begin("Activating more swap")
    run("/sbin/swapon", "-a")
    ui.end()

def setClock():
    if config.is_virtual():
        return
    
    adj = "--adjust"
    if not touch("/etc/adjtime"):
        adj = "--noadjfile"
    elif os.stat("/etc/adjtime").st_size == 0:
        write("/etc/adjtime", "0.0 0 0.0\n")
    
    ui.begin("Setting system clock to hardware clock")
    
    opts = "--utc"
    if config.get("clock") != "UTC":
        opts = "--localtime"
    
    t = capture("/sbin/hwclock", adj, opts)
    t2 = capture("/sbin/hwclock", "--hctosys", opts)
    if t[1] != '' or t2[1] != '':
        ui.end("Failed to set system clock to hardware clock")
    else:
        ui.end()

def saveClock():
    if config.is_livecd() or config.is_virtual():
        return
    
    opts = "--utc"
    if config.get("clock") != "UTC":
        opts = "--localtime"
    
    ui.begin("Syncing system clock to hardware clock")
    t = capture("/sbin/hwclock", "--systohc", opts)
    if t[1] != '':
        ui.end("Failed to sync clocks")
    else:
        ui.end()

def stopSystem():
    def proc_key(x):
        """sort helper"""
        return x[1]
    
    ui.begin("Stopping services")
    run("/usr/bin/hav", "call", "System.Service.stop")
    ui.end()
    
    ui.begin("Stopping COMAR")
    run("start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/comar.pid")
    ui.end()
    
    saveClock()
    
    ui.begin("Deactivating swap")
    # unmount unused tmpfs filesystems before swap
    # (tmpfs can be swapped and you can get a deadlock)
    run("/bin/umount", "-at", "tmpfs")
    run("/sbin/swapoff", "-a")
    ui.end()
    
    def getFS():
        ents = loadFile("/proc/mounts").split("\n")
        ents = map(lambda x: x.split(), ents)
        ents = filter(lambda x: len(x) > 2, ents)
        # not the virtual systems
        vfs = [ "proc", "devpts", "sysfs", "devfs", "tmpfs", "usbfs", "usbdevfs" ]
        ents = filter(lambda x: not x[2] in vfs, ents)
        ents = filter(lambda x: x[0] != "none", ents)
        # not the root stuff
        ents = filter(lambda x: not (x[0] == "rootfs" or x[0] == "/dev/root"), ents)
        ents = filter(lambda x: x[1] != "/", ents)
        # sort for correct unmount order
        ents.sort(key=proc_key, reverse=True)
        return ents
    
    ui.begin("Unmounting filesystems")
    # write a reboot record to /var/log/wtmp before unmounting
    run("/sbin/halt", "-w")
    for dev in getFS():
        if run("/bin/umount", dev[1]) != 0:
            # kill processes still using this mount
            run("/bin/fuser", "-k", "-9", "-m", dev[1])
            time.sleep(2)
            run("/bin/umount", "-f", "-r", dev[1])
    ui.end()
    
    def remount_ro(force=False):
        ents = loadFile("/proc/mounts").split("\n")
        ents = map(lambda x: x.split(), ents)
        ents = filter(lambda x: len(x) > 2, ents)
        ents = filter(lambda x: x[0] != "none", ents)
        ents.sort(key=proc_key, reverse=True)
        
        if ents:
            run("/usr/bin/sync")
            run("/usr/bin/sync")
            time.sleep(1)
        
        ret = 0
        for ent in ents:
            if force:
                ret += run("/bin/umount", "-n", "-r", ent[1])
            else:
                ret += run("/bin/mount", "-n", "-o", "remount,ro", ent[1])
        if ret:
            run("killall5", "-9")
        return ret
    
    ui.begin("Remounting remaining filesystems readonly")
    # we parse /proc/mounts but use umount, so this have to agree
    run("cp", "/proc/mounts", "/etc/mtab")
    if remount_ro():
        if remount_ro():
            remount_ro(True)
    ui.end()


#
# Exception hook
#

def except_hook(eType, eValue, eTrace):
    print "boink\07 boink\07!"
    print eType, eValue
    import traceback
    traceback.print_tb(eTrace)
    time.sleep(10)
    run("/sbin/sulogin")


#
# Main program
#

logger.log("(((o) mudur %s" % sys.argv[1])

os.umask(022)
sys.excepthook = except_hook

# Setup path just in case
os.environ["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:" + os.environ["PATH"]

if sys.argv[1] == "sysinit":
    # This is who we are
    print "Pardus, http://www.uludag.org.tr"
    
    # mount /proc
    mount("/proc", "-t proc proc /proc")
    # those need /proc
    logger.uptime()
    config.parse_kernel_opts()
    
    # Setup encoding, font and mapping for console
    languages["tr"].setConsole()
    
    ui.begin("Mounting /sys")
    mount("/sys", "-t sysfs sysfs /sys")
    ui.end()
    
    setupUdev()
    
    ui.begin("Mounting /dev/pts")
    mount("/dev/pts", "-t devpts -o gid=5,mode=0620 devpts /dev/pts")
    ui.end()
    
    ui.begin("Activating swap partitions")
    run("/sbin/swapon", "-a")
    ui.end()
    
    # Set kernel console log level for cleaner boot
    # only panic messages will be printed
    run("/bin/dmesg", "-n", "1")
    
    checkRoot()
    setHostname()
    modules()
    checkFS()
    localMount()
    setClock()
    
    # better performance for SMP systems, /var/run must be mounted rw before this
    if os.path.exists("/sbin/irqbalance"):
        run("/sbin/irqbalance")

    # improve responsiveness
    write("/proc/sys/dev/rtc/max-user-freq", "1024")

    # when we exit this runlevel, init will write a boot record to utmp
    write("/var/run/utmp", "")
    touch("/var/log/wtmp")
    run("/usr/bin/chgrp", "utmp", "/var/run/utmp", "/var/log/wtmp")
    run("/usr/bin/chmod", "0664", "/var/run/utmp", "/var/log/wtmp")

    ui.begin("Starting Coldplug")
    for rc in os.listdir("/etc/hotplug/"):
        if rc.endswith(".rc"):
            os.spawnl(os.P_NOWAIT, os.path.join("/etc/hotplug", rc), os.path.join("/etc/hotplug", rc), "start")
    ui.end()

elif sys.argv[1] == "boot":
    logger.uptime()
    
    ui.begin("Setting up localhost")
    run("/sbin/ifconfig", "lo", "127.0.0.1", "up")
    run("/sbin/route", "add", "-net", "127.0.0.0", "netmask", "255.0.0.0",
        "gw", "127.0.0.1", "dev", "lo")
    ui.end()

    # set some disk parameters
    # run("/sbin/hdparm", "-d1", "-Xudma5", "-c3", "-u1", "-a8192", "/dev/hda")

    # start x earlier
    # we can't start X here, we sometimes need a service to run first
    # ui.begin("Starting X")
    # run("/sbin/start-stop-daemon", "--start", "--quiet", "--exe", "/usr/kde/3.5/bin/kdm")
    # ui.end()
    
    if mdirdate("/etc/env.d") > mdate("/etc/profile.env"):
        ui.begin("Updating environment")
        os.system("/sbin/env-update.sh")
        ui.end()
    
    ui.begin("Cleaning up /var")
    for root,dirs,files in os.walk("/var/run"):
        for f in files:
            if f != "utmp" and f != "random-seed":
                os.unlink(os.path.join(root, f))
    ui.end()
    
    # reset console permissions if we are actually using it
    if os.path.exists("/sbin/pam_console_apply"):
        for pamd in os.listdir("/etc/pam.d"):
            data = loadFile(os.path.join("/etc/pam.d", pamd)).split("\n")
            m = filter(lambda x: "pam_console" in x and not x.startswith("#"), data)
            if len(m) > 0:
                run("/sbin/pam_console_apply", "-r")
                break
    
    ui.begin("Starting COMAR")
    run("/sbin/start-stop-daemon", "-b", "--start", "--quiet",
        "--pidfile", "/var/run/comar.pid", "--make-pidfile",
        "--exec", "/usr/bin/comar")
    ui.end()

elif sys.argv[1] == "reboot":
    stopSystem()
    run("/sbin/reboot", "-idp")
    run("/sbin/reboot", "-f")

elif sys.argv[1] == "shutdown":
    stopSystem()
    run("/sbin/halt", "-ihdp")
    run("/sbin/halt", "-f")

elif sys.argv[1] == "default":
    logger.uptime()
    startServices()

logger.uptime()
logger.sync()

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
import glob
import stat
import subprocess
import gettext
import time
import signal
import fcntl
import socket

#
# i18n
#

__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

#
# Utilities
#

def loadFile(path):
    """Read contents of a file"""
    f = file(path)
    data = f.read()
    f.close()
    return data

def loadConfig(path):
    dict = {}
    for line in file(path):
        if line != "" and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith('"') or value.startswith("'"):
                value = value[1:-1]
            dict[key] = value
    return dict

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
    """Capture output of the command without running a shell"""
    a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return a.communicate()

def run(*cmd):
    """Run a command without running a shell, only output errors"""
    f = file("/dev/null", "w")
    return subprocess.call(cmd, stdout=f)

def run_full(*cmd):
    """Run a command without running a shell, with full output"""
    return subprocess.call(cmd)

def run_quiet(*cmd):
    """Run the command without running a shell and no output"""
    f = file("/dev/null", "w")
    return subprocess.call(cmd, stdout=f, stderr=f)

def delete(path, match=False, no_error=False):
    """Delete files and dirs recursively"""
    try:
        if match:
            path = glob.glob(path)
        else:
            path = [ path ]
        for item in path:
            for root, dirs, files in os.walk(item, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            if stat.S_ISDIR(os.stat(item).st_mode):
                os.rmdir(item)
            else:
                os.unlink(item)
    except Exception, e:
        if no_error == False:
            raise

def waitBus(unix_name, timeout=5, wait=0.1, stream=True):
    if stream:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    while timeout > 0:
        try:
            sock.connect(unix_name)
            return True
        except:
            timeout -= wait
        time.sleep(wait)
    return False

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


class Config:
    def __init__(self):
        self.kernel = os.uname()[2].split(".")
        self.fstab = None
        self.cmdline = None
        # default options
        self.opts = {
            "language": "tr",
            "keymap": None,
            "clock": "local",
            "debug": False,
            "livecd": False,
        }
        # load config file if exists
        if os.path.exists("/etc/conf.d/mudur"):
            for key in loadConfig("/etc/conf.d/mudur"):
                self.opts[key] = dict[key]
    
    def get_kernel_opt(self, cmdopt):
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
        # old style option
        lang = self.get_kernel_opt("lang")
        if lang:
            self.opts["language"] = lang
        
        opts = self.get_kernel_opt("mudur")
        if opts:
            opts = opts.split(",")
            for opt in opts:
                if opt == "livecd":
                    self.opts["livecd"] = True
                elif opt == "debug":
                    self.opts["debug"] = True
                elif opt.startswith("lang:"):
                    self.opts["language"] = opt[5:]
                elif opt.startswith("keymap:"):
                    self.opts["keymap"] = opt[7:]
    
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


class UI:
    UNICODE_MAGIC = "\x1b%G"
    
    def __init__(self):
        self.GOOD = '\x1b[32;01m'
        self.WARN = '\x1b[33;01m'
        self.BAD = '\x1b[31;01m'
        self.NORMAL = '\x1b[0m'
    
    def _echo(self, msg, colour=None):
        logger.log(msg)
        
        if colour:
            sys.stdout.write(" %s*%s %s\n" % (colour, self.NORMAL, msg.encode("utf-8")))
        else:
            sys.stdout.write(msg.encode("utf-8"))
            sys.stdout.write("\n")
    
    def greet(self):
        print self.UNICODE_MAGIC
        if os.path.exists("/etc/pardus-release"):
            release = loadFile("/etc/pardus-release").rstrip("\n")
            print "\x1b[1m  %s  \x1b[0;36mhttp://www.pardus.org.tr\x1b[0m" % release
        else:
            self.error(_("Cannot find /etc/pardus-release"))
        print
    
    def info(self, msg):
        self._echo(msg, self.GOOD)
    
    def warn(self, msg):
        self._echo(msg, self.WARN)
    
    def error(self, msg):
        self._echo(msg, self.BAD)
    
    def debug(self, msg):
        logger.log(msg)


#
# Language and keymap
#

class Language:
    def __init__(self, keymap, font, trans, locale):
        self.keymap = keymap
        self.font = font
        self.trans = trans
        self.locale = locale


languages = {
    "en": Language("us", "iso01.16", "8859-1", "en_US.UTF-8"),
    "tr": Language("trq", "iso09.16", "8859-9", "tr_TR.UTF-8")
}

def setConsole():
    """Setup encoding, font and mapping for console"""
    lang = config.get("language")
    keymap = config.get("keymap")
    # If language is unknown, default to English
    # Default language is Turkish, so this only used if someone
    # selected a language which isn't Turkish or English, and
    # in that case it is more likely they'll prefer English.
    if not languages.has_key(lang):
        lang = "en"
    language = languages[lang]
    # Given keymap can override language's default
    if not keymap:
        keymap = language.keymap
    # Now actually set the values
    run("/usr/bin/kbd_mode", "-u")
    run_quiet("/bin/loadkeys", keymap)
    run("/usr/bin/setfont", "-f", language.font, "-m", language.trans)

def setTranslation():
    """Load translation"""
    global __trans
    global _
    lang = config.get("language")
    if not languages.has_key(lang):
        # See the comment in setConsole
        lang = "en"
    __trans = gettext.translation('mudur', languages=[lang], fallback=True)
    _ = __trans.ugettext

def ttyUnicode():
    # constants from linux/kd.h
    KDSKBMODE = 0x4B45
    K_UNICODE = 0x03
    for i in range(1, 13):
        try:
            f = file("/dev/tty" + str(i), "w")
            fcntl.ioctl(f, KDSKBMODE, K_UNICODE)
            f.write(UI.UNICODE_MAGIC)
            f.close()
        except:
            ui.error(_("Could not set unicode mode on tty %d") % i)

#

def mount(part, args):
    ent = config.get_mount(part)
    if ent and len(ent) > 3:
        args = "-t %s -o %s %s %s" % (ent[2], ent[3], ent[0], ent[1])
    os.system("/bin/mount -n %s" % args)


#
# COMAR functions
#

def startComar():
    ui.info(_("Starting COMAR"))
    # If a job crashes before finishing a transaction, Berkeley DB halts.
    # We are deleting DB log files before starting Comar, so a reboot fixes
    # the problem if it ever happens.
    delete("/var/db/comar/__*", match=True)
    delete("/var/db/comar/log*", match=True)
    run("/sbin/start-stop-daemon", "-b", "--start", "--quiet",
        "--pidfile", "/var/run/comar.pid", "--make-pidfile",
        "--exec", "/usr/bin/comar")

def startServices():
    ui.info(_("Starting services"))
    import comar
    waitBus("/var/run/comar.socket")
    try:
        link = comar.Link()
    except:
        ui.error(_("Cannot connect to COMAR, services won't be started"))
        return
    # Almost everything depends on logger, so start manually
    link.call_package("System.Service.start", "sysklogd")
    if not waitBus("/dev/log", stream=False):
        ui.warn(_("Cannot start system logger"))
    # Give login screen a headstart
    link.call_package("System.Service.ready", "kdebase")
    time.sleep(1.5)
    link.call("System.Service.ready")


#
# Initialization functions
#

def setupUdev():
    udev_backup = "/lib/udev-state/devices.tar.bz2"
    # many video drivers require exec access in /dev
    ui.info(_("Mounting /dev"))
    mount("/dev", "-t tmpfs -o exec,nosuid,mode=0755 udev /dev")
    ui.info(_("Restoring saved device states"))
    if os.path.exists(udev_backup):
        run("/bin/tar", "-jxpf", udev_backup, "-C" "/dev")
    ui.info(_("Starting udev"))
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
    if not config.get("livecd"):
        ui.info(_("Remounting root filesystem read-only"))
        run("/bin/mount", "-n", "-o", "remount,ro", "/")
        
        ent = config.get_mount("/")
        if len(ent) > 5 and ent[5] != "0":
            ui.info(_("Checking root filesystem"))
            t = run_full("/sbin/fsck", "-C", "-T", "-a", "/")
            if t == 0:
                pass
            elif t == 2 or t == 3:
                ui.warn(_("Filesystem repaired, but reboot needed!"))
                for i in range(4):
                    print "\07"
                    time.sleep(1)
                ui.warn(_("Rebooting in 10 seconds ..."))
                time.sleep(10)
                ui.warn(_("Rebooting..."))
                run("/sbin/reboot", "-f")
            else:
                ui.error(_("Filesystem couldn't be fixed :("))
                run_full("/sbin/sulogin")
        else:
            ui.info(_("Skipping root filesystem check (fstab's passno == 0)"))
    
    ui.info(_("Remounting root filesystem read/write"))
    if run_quiet("/bin/mount", "-n", "-o", "remount,rw", "/") != 0:
        ui.error(_("Root filesystem could not be mounted read/write :("))
    
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
    
    ui.info(_("Setting up hostname as '%s'") % host)
    run("/bin/hostname", host)

def modules():
    # dont fail if kernel do not have module support compiled in
    if not os.path.exists("/proc/modules"):
        return
    
    if mdirdate("/etc/modules.d") > mdate("/etc/modules.conf"):
        # FIXME: convert this script to python
        ui.info(_("Calculating module dependencies"))
        run_quiet("/sbin/modules-update")
    
    fn = "/etc/modules.autoload.d/kernel-%s.%s.%s" % (config.kernel[0], config.kernel[1], config.kernel[2])
    if not os.path.exists(fn):
        fn = "/etc/modules.autoload.d/kernel-%s.%s" % (config.kernel[0], config.kernel[1])
    if os.path.exists(fn):
        data = loadFile(fn).split("\n")
        data = filter(lambda x: x != "" and not x.startswith('#'), data)
        for mod in data:
            run("/sbin/modprobe", "-q", mod)

def checkFS():
    if config.get("livecd"):
        return
    
    ui.info(_("Checking all filesystems"))
    t = run_full("/sbin/fsck", "-C", "-T", "-R", "-A", "-a")
    if t == 0:
        pass
    elif t >= 2 and t <= 3:
        ui.warn(_("Filesystem errors corrected"))
    else:
        ui.error(_("Fsck could not correct all errors, manual repair needed"))
        run_full("/sbin/sulogin")

def localMount():
    ui.info(_("Mounting local filesystems"))
    run("/bin/mount", "-at", "noproc,noshm")
    
    if os.path.exists("/proc/modules") and not os.path.exists("/proc/bus/usb"):
        run_quiet("/sbin/modprobe", "usbcore")
    
    if os.path.exists("/proc/bus/usb") and not os.path.exists("/proc/bus/usb/devices"):
        gid = None
        for line in file("/etc/group"):
            if line.startswith("usb:"):
                gid = line.split(":")[2]
                break
        ui.info(_("Mounting USB filesystem"))
        if gid:
            run("/bin/mount", "-t", "usbfs", "usbfs", "/proc/bus/usb", "-o", "devmode=0664,devgid=%s" % gid)
        else:
            run("/bin/mount", "-t", "usbfs", "usbfs", "/proc/bus/usb")
    
    ui.info(_("Activating swap"))
    run("/sbin/swapon", "-a")

def hdparm():
    if not os.path.exists("/sbin/hdparm") or not os.path.exists("/etc/conf.d/hdparm"):
        return
    
    dict = loadConfig("/etc/conf.d/hdparm")
    if len(dict) > 0:
        ui.info(_("Setting disk parameters"))
        if dict.has_key("all"):
            for name in os.listdir("/dev"):
                if name.startswith("hd") and len(name) == 3 and not dict.has_key(name):
                    args = [ "/sbin/hdparm", "/dev/%s" % name ]
                    args.extend(dict["all"].split())
                    run_quiet(*args)
        for key in dict:
            if key != "all":
                args = [ "/sbin/hdparm", "/dev/%s" % key ]
                args.extend(dict[key].split())
                run_quiet(*args)

def setClock():
    if config.is_virtual():
        return
    
    adj = "--adjust"
    if not touch("/etc/adjtime"):
        adj = "--noadjfile"
    elif os.stat("/etc/adjtime").st_size == 0:
        write("/etc/adjtime", "0.0 0 0.0\n")
    
    ui.info(_("Setting system clock to hardware clock"))
    
    opts = "--utc"
    if config.get("clock") != "UTC":
        opts = "--localtime"
    
    t = capture("/sbin/hwclock", adj, opts)
    t2 = capture("/sbin/hwclock", "--hctosys", opts)
    if t[1] != '' or t2[1] != '':
        ui.error(_("Failed to set system clock to hardware clock"))

def cleanupTmp():
    if config.get("livecd"):
        return
    
    ui.info(_("Cleaning up /tmp"))
    delete("/tmp/.X*-lock", match=True, no_error=True)
    delete("/tmp/kio*", match=True, no_error=True)
    delete("/tmp/ssh-*", match=True, no_error=True)
    delete("/tmp/kio*", match=True, no_error=True)
    delete("/tmp/ksocket-*", match=True, no_error=True)
    delete("/tmp/.*-unix", match=True, no_error=True)
    try:
        os.mkdir("/tmp/.ICE-unix")
        os.mkdir("/tmp/.X11-unix")
    except OSError, e:
        if e.errno != 17:
            raise
    os.chown("/tmp/.ICE-unix", 0, 0)
    os.chown("/tmp/.X11-unix", 0, 0)
    os.chmod("/tmp/.ICE-unix", 01777)
    os.chmod("/tmp/.ICE-unix", 01777)

def saveClock():
    if config.get("livecd") or config.is_virtual():
        return
    
    opts = "--utc"
    if config.get("clock") != "UTC":
        opts = "--localtime"
    
    ui.info(_("Syncing system clock to hardware clock"))
    t = capture("/sbin/hwclock", "--systohc", opts)
    if t[1] != '':
        ui.error(_("Failed to sync clocks"))

def stopSystem():
    def proc_key(x):
        """sort helper"""
        return x[1]
    
    ui.info(_("Stopping services"))
    run_quiet("/usr/bin/hav", "call", "System.Service.stop")
    
    ui.info(_("Stopping COMAR"))
    run("start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/comar.pid")
    
    saveClock()
    
    ui.info(_("Deactivating swap"))
    # unmount unused tmpfs filesystems before swap
    # (tmpfs can be swapped and you can get a deadlock)
    run_quiet("/bin/umount", "-at", "tmpfs")
    run_quiet("/sbin/swapoff", "-a")
    
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
    
    ui.info(_("Unmounting filesystems"))
    # write a reboot record to /var/log/wtmp before unmounting
    run("/sbin/halt", "-w")
    for dev in getFS():
        if run_quiet("/bin/umount", dev[1]) != 0:
            # kill processes still using this mount
            run_quiet("/bin/fuser", "-k", "-9", "-m", dev[1])
            time.sleep(2)
            run_quiet("/bin/umount", "-f", "-r", dev[1])
    
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
                ret += run_quiet("/bin/umount", "-n", "-r", ent[1])
            else:
                ret += run_quiet("/bin/mount", "-n", "-o", "remount,ro", ent[1])
        if ret:
            run_quiet("killall5", "-9")
        return ret
    
    ui.info(_("Remounting remaining filesystems readonly"))
    # we parse /proc/mounts but use umount, so this have to agree
    run("cp", "/proc/mounts", "/etc/mtab")
    if remount_ro():
        if remount_ro():
            remount_ro(True)


#
# Exception hook
#

def except_hook(eType, eValue, eTrace):
    print
    print _("An internal error occured. Please report to the bugs.pardus.org.tr with following information:").encode("utf-8")
    print
    print eType, eValue
    import traceback
    traceback.print_tb(eTrace)
    print
    run_full("/sbin/sulogin")


#
# Main program
#

signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGQUIT, signal.SIG_IGN)
signal.signal(signal.SIGTSTP, signal.SIG_IGN)
sys.excepthook = except_hook
os.umask(022)

# Setup path just in case
os.environ["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:" + os.environ["PATH"]

# Setup output and load configuration
logger = Logger()
config = Config()
ui = UI()

logger.log("(((o) mudur %s" % sys.argv[1])

if sys.argv[1] == "sysinit":
    # This is who we are...
    ui.greet()
    # Mount /proc
    mount("/proc", "-t proc proc /proc")
    # We need /proc mounted before accessing kernel boot options
    config.parse_kernel_opts()
    # Setup font and keymap
    setConsole()
else:
    config.parse_kernel_opts()


logger.uptime()
setTranslation()


if sys.argv[1] == "sysinit":
    ui.info(_("Mounting /sys"))
    mount("/sys", "-t sysfs sysfs /sys")
    
    setupUdev()
    
    ui.info(_("Mounting /dev/pts"))
    mount("/dev/pts", "-t devpts -o gid=5,mode=0620 devpts /dev/pts")
    
    # Set kernel console log level for cleaner boot
    # only panic messages will be printed
    run("/bin/dmesg", "-n", "1")
    
    ttyUnicode()
    
    checkRoot()
    setHostname()
    modules()
    checkFS()
    localMount()
    
    hdparm()
    
    ui.info(_("Starting Coldplug"))
    subprocess.Popen(["/sbin/muavin.py", "--coldplug"])
    
    setClock()
    
    # better performance for SMP systems, /var/run must be mounted rw before this
    if os.path.exists("/sbin/irqbalance"):
        run("/sbin/irqbalance")
    
    # improve responsiveness
    write("/proc/sys/dev/rtc/max-user-freq", "1024")
    
    # Change inittab for live cd autologin
    if config.get("livecd") and os.path.exists("/etc/inittab.livecd"):
        write("/etc/inittab", loadFile("/etc/inittab.livecd"))
        run_quiet("/sbin/telinit", "q")
    
    # when we exit this runlevel, init will write a boot record to utmp
    write("/var/run/utmp", "")
    touch("/var/log/wtmp")
    run("/usr/bin/chgrp", "utmp", "/var/run/utmp", "/var/log/wtmp")
    run("/usr/bin/chmod", "0664", "/var/run/utmp", "/var/log/wtmp")


elif sys.argv[1] == "boot":
    ui.info(_("Setting up localhost"))
    run("/sbin/ifconfig", "lo", "127.0.0.1", "up")
    run("/sbin/route", "add", "-net", "127.0.0.0", "netmask", "255.0.0.0",
        "gw", "127.0.0.1", "dev", "lo")
    
    if not config.get("livecd"):
        ui.info(_("Cleaning up /var"))
        for root,dirs,files in os.walk("/var/run"):
            for f in files:
                if f != "utmp" and f != "random-seed":
                    os.unlink(os.path.join(root, f))
    
    if mdirdate("/etc/env.d") > mdate("/etc/profile.env"):
        ui.info(_("Updating environment variables"))
        # FIXME: convert this script to python
        run("/sbin/env-update.sh")
    
    # reset console permissions if we are actually using it
    if os.path.exists("/sbin/pam_console_apply"):
        for pamd in os.listdir("/etc/pam.d"):
            data = loadFile(os.path.join("/etc/pam.d", pamd)).split("\n")
            m = filter(lambda x: "pam_console" in x and not x.startswith("#"), data)
            if len(m) > 0:
                run("/sbin/pam_console_apply", "-r")
                break
    
    cleanupTmp()
    
    startComar()

elif sys.argv[1] == "reboot":
    stopSystem()
    run("/sbin/reboot", "-idp")
    run("/sbin/reboot", "-f")

elif sys.argv[1] == "shutdown":
    stopSystem()
    run("/sbin/halt", "-ihdp")
    run("/sbin/halt", "-f")

elif sys.argv[1] == "default":
    startServices()

logger.uptime()
logger.sync()

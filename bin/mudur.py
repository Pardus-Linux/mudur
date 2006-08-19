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
        stamp = time.strftime("%b %d %H:%M:%S")
        try:
            up = loadFile("/proc/uptime").split()[0]
        except:
            up = "..."
        self.lines.append("%s (up %s) %s\n" % (stamp, up, msg))
    
    def sync(self):
        f = file("/var/log/mudur.log", "a")
        map(f.write, self.lines)
        f.close()


class Config:
    def __init__(self):
        self.fstab = None
        self.cmdline = None
        # parse kernel version
        self.kernel = []
        vers = os.uname()[2]
        vpart = ""
        for c in vers:
            if c == "." or c == "_" or c == "-":
                self.kernel.append(vpart)
                vpart = ""
            else:
                vpart += c
        self.kernel.append(vpart)
        # default options
        self.opts = {
            "language": "tr",
            "keymap": None,
            "clock": "local",
            "tty_number": "6",
            "debug": False,
            "livecd": False,
            "safe": False,
        }
        # load config file if exists
        if os.path.exists("/etc/conf.d/mudur"):
            dict_ = loadConfig("/etc/conf.d/mudur")
            for key in dict_:
                self.opts[key] = dict_[key]
    
    def kernel_ge(self, vers):
        vers = vers.split(".")
        if int(self.kernel[0]) < int(vers[0]):
            return False
        if int(self.kernel[1]) < int(vers[1]):
            return False
        if int(self.kernel[2]) < int(vers[2]):
            return False
        return True
    
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
        # We need to mount /proc before accessing kernel options
        # This function is called after that, and finish parsing options
        # We dont print any messages before, cause language is not known
        opts = self.get_kernel_opt("mudur")
        if opts:
            opts = opts.split(",")
            for opt in opts:
                if opt == "livecd":
                    self.opts["livecd"] = True
                elif opt == "debug":
                    self.opts["debug"] = True
                elif opt == "safe":
                    self.opts["safe"] = True
                elif opt.startswith("language:"):
                    self.opts["language"] = opt[9:]
                elif opt.startswith("keymap:"):
                    self.opts["keymap"] = opt[7:]
        
        # Normalize options
        
        # If language is unknown, default to English
        # Default language is Turkish, so this only used if someone
        # selected a language which isn't Turkish or English, and
        # in that case it is more likely they'll prefer English.
        lang = self.opts["language"]
        if not languages.has_key(lang):
            print "Unknown language option '%s'" % lang
            lang = "en"
            self.opts["language"] = lang
        
        # If no keymap is given, use the language's default
        if not self.opts["keymap"]:
            self.opts["keymap"] = languages[lang].keymap
    
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
        # FIXME: detect vmware and co. here
        return False


class UI:
    UNICODE_MAGIC = "\x1b%G"
    
    def __init__(self):
        self.GOOD = '\x1b[32;01m'
        self.WARN = '\x1b[33;01m'
        self.BAD = '\x1b[31;01m'
        self.NORMAL = '\x1b[0m'
    
    def greet(self):
        print self.UNICODE_MAGIC
        if os.path.exists("/etc/pardus-release"):
            release = loadFile("/etc/pardus-release").rstrip("\n")
            print "\x1b[1m  %s  \x1b[0;36mhttp://www.pardus.org.tr\x1b[0m" % release
        else:
            self.error(_("Cannot find /etc/pardus-release"))
        print
    
    def info(self, msg):
        if config.get("debug"):
            logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.GOOD, self.NORMAL, msg.encode("utf-8")))
    
    def warn(self, msg):
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.WARN, self.NORMAL, msg.encode("utf-8")))
    
    def error(self, msg):
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.BAD, self.NORMAL, msg.encode("utf-8")))
    
    def debug(self, msg):
        if config.get("debug"):
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
    "tr": Language("trq", "iso09.16", "8859-9", "tr_TR.UTF-8"),
    "nl": Language("nl", "iso01.16", "8859-1", "nl_NL.UTF-8")
}

def setConsole():
    """Setup encoding, font and mapping for console"""
    lang = config.get("language")
    keymap = config.get("keymap")
    language = languages[lang]
    # Now actually set the values
    run("/usr/bin/kbd_mode", "-u")
    run_quiet("/bin/loadkeys", keymap)
    run("/usr/bin/setfont", "-f", language.font, "-m", language.trans)

def setSystemLanguage():
    lang = config.get("language")
    keymap = config.get("keymap")
    language = languages[lang]
    # Put them in /etc, so other programs like kdm can use them
    # without duplicating default->mudur.conf->kernel-option logic
    # we do here. Note that these are system-wide not per user,
    # and only for reading.
    ensureDirs("/etc/mudur")
    write("/etc/mudur/language", "%s\n" % lang)
    write("/etc/mudur/keymap", "%s\n" % keymap)
    write("/etc/mudur/locale", "%s\n" % language.locale)
    # Update environment if necessary
    content = "LANG=%s\nLC_ALL=%s\n" % (language.locale, language.locale)
    if content != loadFile("/etc/env.d/03locale"):
        write("/etc/env.d/03locale", content)

def setSplash():
    """Setup console splash and proper encodings for consoles"""
    splash = config.get_kernel_opt("splash")
    if not splash or not os.path.exists("/dev/fb0"):
        return
    
    theme = "default"
    for arg in splash.split(","):
        if arg.startswith("theme:"):
            theme = arg[6:]
    
    lang = config.get("language")
    language = languages[lang]
    
    for i in range(1, int(config.get("tty_number")) + 1):
        run("/usr/bin/setfont", "-f", language.font, "-m", language.trans, "-C", "/dev/tty%s" %i)
        run("/usr/bin/splash_manager", "--mode=v", "--theme=%s" % theme, "--cmd=set", "--tty=%s" % i)

def setTranslation():
    """Load translation"""
    global __trans
    global _
    lang = config.get("language")
    __trans = gettext.translation('mudur', languages=[lang], fallback=True)
    _ = __trans.ugettext

def ttyUnicode():
    # constants from linux/kd.h
    KDSKBMODE = 0x4B45
    K_UNICODE = 0x03
    for i in range(1, int(config.get("tty_number")) + 1):
        try:
            f = file("/dev/tty%s" % i, "w")
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
    if not config.get("safe"):
        time.sleep(1.5)
        link.call("System.Service.ready")

def stopServices():
    ui.info(_("Stopping services"))
    run_quiet("/usr/bin/hav", "call", "System.Service.stop")

def stopComar():
    ui.info(_("Stopping COMAR"))
    run("start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/comar.pid")


#
# Initialization functions
#

def setupUdev():
    ui.info(_("Mounting /dev"))
    # many video drivers require exec access in /dev
    mount("/dev", "-t tmpfs -o exec,nosuid,mode=0755 udev /dev")

#    FIXME: There is problem here
#    if os.path.exists("/lib/udev/devices"):
#        ui.info(_("Restoring saved device states"))
#        run_quiet("/usr/bin/cp", "-ar", "/lib/udev/devices/*", "/dev/")
    
    ui.info(_("Starting udev"))

    if config.kernel_ge("2.6.16"):
        # disable uevent helper, udevd listens to netlink
        write("/sys/kernel/uevent_helper", " ")

        run("/sbin/udevd", "--daemon")

        ui.info(_("Populating /dev"))

        # trigger events for all devices
        run("/sbin/udevtrigger")

        # wait for events to finish
        run("/sbin/udevsettle", "--timeout=180")
    else:
        # no netlink support in old kernels
        write("/proc/sys/kernel/hotplug", "/sbin/udevsend")
        run("/sbin/udevstart")

    # NOTE: handle lvm here when used by pardus

    # Create problematic directories
    ensureDirs("/dev/pts")
    ensureDirs("/dev/shm")

    # Mark the /dev management system type
    touch("/dev/.udev")

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
    if os.path.exists("/etc/env.d/01hostname"):
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
            j = data.find('"', i+10)
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
    
    do_modup = False
    if os.path.exists("/etc/modprobe.mudur"):
        depkernel = loadFile("/etc/modprobe.mudur").rstrip("\n")
        curkernel = os.uname()[2]
        if depkernel != curkernel:
            do_modup = True
    if mdirdate("/etc/modules.d") > mdate("/etc/modprobe.conf"):
        do_modup = True
    if do_modup:
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
    
    ui.info(_("Mounting local filesystems"))
    run("/bin/mount", "-at", "noproc,noshm")
    
    ui.info(_("Activating swap"))
    run("/sbin/swapon", "-a")

def hdparm():
    if config.get("safe"):
        return
    
    if not os.path.exists("/sbin/hdparm") or not os.path.exists("/etc/conf.d/hdparm"):
        return
    
    dict = loadConfig("/etc/conf.d/hdparm")
    if len(dict) > 0:
        ui.info(_("Setting disk parameters"))
        if dict.has_key("all"):
            for name in os.listdir("/sys/block/"):
                if name.startswith("hd") and len(name) == 3 and not dict.has_key(name):
                    args = [ "/sbin/hdparm" ]
                    args.extend(dict["all"].split())
                    args.append("/dev/%s" % name)
                    run_quiet(*args)
        for key in dict:
            if key != "all":
                args = [ "/sbin/hdparm" ]
                args.extend(dict[key].split())
                args.append("/dev/%s" % key)
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

def cleanupVar():
    if not config.get("livecd"):
        ui.info(_("Cleaning up /var"))
        for root,dirs,files in os.walk("/var/run"):
            for f in files:
                if f != "utmp" and f != "random-seed":
                    os.unlink(os.path.join(root, f))

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
    os.chmod("/tmp/.X11-unix", 01777)

def resetConPerms():
    # reset console permissions if we are actually using it
    if os.path.exists("/sbin/pam_console_apply"):
        for pamd in os.listdir("/etc/pam.d"):
            data = loadFile(os.path.join("/etc/pam.d", pamd)).split("\n")
            m = filter(lambda x: "pam_console" in x and not x.startswith("#"), data)
            if len(m) > 0:
                run("/sbin/pam_console_apply", "-r")
                break


#
# Finalization functions
#

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
    
    stopServices()
    stopComar()
    
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

if sys.argv[1] == "sysinit":
    # This is who we are...
    ui.greet()
    # Mount /proc
    mount("/proc", "-t proc proc /proc")
    # We need /proc mounted before accessing kernel boot options
    config.parse_kernel_opts()
    # Now we know which language and keymap to use
    setConsole()
else:
    config.parse_kernel_opts()

# We can log the event with uptime information now
logger.log("/sbin/mudur.py %s" % sys.argv[1])

# Activate i18n, we can print localized messages from now on
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
    
    checkRoot()
    setHostname()
    modules()
    checkFS()
    localMount()
    
    hdparm()
    
    ui.info(_("Starting Coldplug"))
    subprocess.Popen(["/sbin/muavin.py", "--coldplug"])
    
    setClock()
    
    setSystemLanguage()
    
    # better performance for SMP systems, /var/run must be mounted rw before this
    if os.path.exists("/sbin/irqbalance"):
        run("/sbin/irqbalance")
    
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
    
    run("/sbin/sysctl", "-q", "-p", "/etc/sysctl.conf")
    
    cleanupVar()

    if mdirdate("/etc/env.d") > mdate("/etc/profile.env"):
        ui.info(_("Updating environment variables"))
        run("/sbin/update-environment")
    
    resetConPerms()
    
    cleanupTmp()
    
    startComar()

    setSplash()

    ttyUnicode()

elif sys.argv[1] == "default":
    startServices()

elif sys.argv[1] == "single":
    stopServices()

elif sys.argv[1] == "reboot" or sys.argv[1] == "shutdown":
    # Log the operation before unmounting file systems
    logger.sync()
    stopSystem()
    if sys.argv[1] == "reboot":
        run("/sbin/reboot", "-idp")
        run("/sbin/reboot", "-f")
    else:
        run("/sbin/halt", "-ihdp")
        run("/sbin/halt", "-f")
    # Control never reaches here

logger.sync()

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Pardus boot and initialization system
# Copyright (C) 2006-2007, TUBITAK/UEKAE
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
import termios
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

def delete(pattern):
    """rmdir with glob support"""
    for path in glob.glob(pattern):
        mode = os.lstat(path).st_mode
        if stat.S_ISDIR(mode):
            run("rm", "-rf", path)
        else:
            run("rm", "-f", path)

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
        try:
            f = file("/var/log/mudur.log", "a")
            map(f.write, self.lines)
            f.close()
        except IOError:
            ui.error(_("Cannot write mudur.log, read-only file system"))


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
            "clock_adjust": "no",
            "tty_number": "6",
            "debug": False,
            "livecd": False,
            "safe": False,
            "forcefsck": False,
            "head_start": "",
            "services": "",
        }
        # load config file if exists
        if os.path.exists("/etc/conf.d/mudur"):
            dict_ = loadConfig("/etc/conf.d/mudur")
            for key in dict_:
                self.opts[key] = dict_[key]
        # file system check can be requested with a file
        if os.path.exists("/forcefsck"):
            self.opts["forcefsck"] = True

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
                if opt == "livecd" or opt == "livedisk" or opt == "thin":
                    self.opts["livecd"] = True
                elif opt == "debug":
                    self.opts["debug"] = True
                elif opt == "safe":
                    self.opts["safe"] = True
                elif opt.startswith("language:"):
                    self.opts["language"] = opt[9:]
                elif opt.startswith("keymap:"):
                    self.opts["keymap"] = opt[7:]
                elif opt == "forcefsck":
                    self.opts["forcefsck"] = True

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
        # Xen detection
        if os.path.exists("/proc/xen/capabilities"):
            dom0 = loadFile("/proc/xen/capabilities").rstrip("\n")
            # if we are in dom0 then no extra work needed, boot normally
            if dom0 != "control_d":
                # if we are in domU then no need to set/sync clock and others
                return True
        return False

class Splash:
    def __init__(self):
        self.enabled = False
        self.increasing = True
        self.percent = 0

    def init(self, percent, increasing=True):
        if os.path.exists("/proc/splash"):
            splash_opts = config.get_kernel_opt("splash")
            self.enabled = splash_opts and "silent" in splash_opts.split(",")
            self.increasing = increasing
            self.percent = percent

    def silent(self):
        if self.enabled:
            write("/proc/splash", "silent\n")
            self.updateProgressBar()

    def verbose(self):
        if self.enabled:
            write("/proc/splash", "verbose\n")

    def updateProgressBar(self, percent=None):
        if self.enabled:
            if percent is not None:
                self.percent = percent
            pe = int(655.35 * self.percent)
            write("/proc/splash", "show %d" % pe)

    def progress(self, delta=3):
        if self.enabled:
            if self.increasing:
                self.updateProgressBar(self.percent + delta)
            else:
                self.updateProgressBar(self.percent - delta)

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
        splash.progress()

    def warn(self, msg):
        splash.verbose()
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.WARN, self.NORMAL, msg.encode("utf-8")))

    def error(self, msg):
        try:
            splash.verbose()
        except IOError:
            pass
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.BAD, self.NORMAL, msg.encode("utf-8")))

    def debug(self, msg):
        if config.get("debug"):
            logger.log(msg)

#
# CPUfreq
#

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
            # Pentium M, Enhanced SpeedStep
            if "est" in self.flags:
                modules.add("acpi-cpufreq")
            # Some kind of Mobile Pentium
            elif self.name.find("Mobile") != -1:
                # ACPI Processor Performance States
                if self._detect_acpi_pps():
                    modules.add("acpi_cpufreq")
                # SpeedStep ICH, PIII-M and P4-M with ICH2/3/4 southbridges
                elif self._detect_ich():
                    modules.add("speedstep_ich")
            # P4 and XEON processors with thermal control
            elif "acpi" in self.flags and "tm" in self.flags:
                modules.add("p4-clockmod")

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

    def loadCPUfreq(self):
        if os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/"):
            # User already specified a frequency module in
            # modules.autoload.d or compiled it into the kernel
            return True

        modules = self.detect()
        if len(modules) > 0:
            modules.add("cpufreq_userspace")
            modules.add("cpufreq_powersave")
            modules.add("cpufreq_ondemand")

            for module in modules:
                run_quiet("/sbin/modprobe", module)

    def debug(self):
        if config.get("debug"):
            logger.log("CPU: %s" % ", ".join(self.detect()))

#
# Language and keymap
#

class Language:
    def __init__(self, keymap, font, trans, locale):
        self.keymap = keymap
        self.font = font
        self.trans = trans
        self.locale = locale


languages = {
    "en": Language("us", "iso01.16", "8859-1", "en_US.UTF-8"),
    "pl": Language("pl", "iso02.16", "8859-2", "pl_PL.UTF-8"),
    "tr": Language("trq", "lat5u-16", "8859-9", "tr_TR.UTF-8"),
    "nl": Language("nl", "iso01.16", "8859-1", "nl_NL.UTF-8"),
    "de": Language("de", "iso01.16", "8859-1", "de_DE.UTF-8"),
    "es": Language("es", "iso01.16", "8859-1", "es_ES.UTF-8"),
    "it": Language("it", "iso01.16", "8859-1", "it_IT.UTF-8"),
    "fr": Language("fr", "iso01.16", "8859-1", "fr_FR.UTF-8"),
    "pt_BR": Language("br-abnt2", "iso01.16", "8859-1", "pt_BR.UTF-8"),
    "ca": Language("es", "iso01.16", "8859-1", "ca_ES.UTF-8"),
}

def setConsole():
    """Setup encoding, font and mapping for console"""
    if config.is_virtual():
        """Xen is just a serial console """
        return

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

def setTranslation():
    """Load translation"""
    global __trans
    global _
    lang = config.get("language")
    __trans = gettext.translation('mudur', languages=[lang], fallback=True)
    _ = __trans.ugettext

def ttyUnicode():
    lang = config.get("language")
    language = languages[lang]

    # constants from linux/kd.h
    KDSKBMODE = 0x4B45
    K_UNICODE = 0x03
    for i in range(1, int(config.get("tty_number")) + 1):
        try:
            if os.path.exists("/dev/tty%s" % i):
                f = file("/dev/tty%s" % i, "w")
                fcntl.ioctl(f, KDSKBMODE, K_UNICODE)
                f.write(UI.UNICODE_MAGIC)
                f.close()
                run("/usr/bin/setfont", "-f", language.font, "-m", language.trans, "-C", "/dev/tty%s" %i)
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
def fork_handler():
    # Set umask to a sane value
    # (other and group has no write permission by default)
    os.umask(022)
    # Detach from controlling terminal
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
        fcntl.ioctl(tty_fd, termios.TIOCNOTTY)
        os.close(tty_fd)
    except OSError:
        pass
    # Close IO channels
    devnull_fd = os.open("/dev/null", os.O_RDWR)
    os.dup2(devnull_fd, 0)
    os.dup2(devnull_fd, 1)
    os.dup2(devnull_fd, 2)
    # Detach from process group
    os.setsid()

def startDBus():
    os.setuid(0)
    ui.info("Starting DBus...")
    if not os.path.exists("/var/lib/dbus/machine-id"):
        run("/usr/bin/dbus-uuidgen", "--ensure")
    run("/sbin/start-stop-daemon", "-b", "--start", "--quiet",
        "--pidfile", "/var/run/dbus/pid", "--exec", "/usr/bin/dbus-daemon",
        "--", "--system")
    waitBus("/var/run/dbus/system_bus_socket")

def readyService(service):
    cmd = ["/bin/service", "--quiet", service, "ready"]
    subprocess.Popen(cmd, close_fds=True, preexec_fn=fork_handler, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    splash.progress(1)

def startService(service):
    cmd = ["/bin/service", "--quiet", service, "start"]
    subprocess.Popen(cmd, close_fds=True, preexec_fn=fork_handler, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    splash.progress(1)

def stopService(service):
    cmd = ["/bin/service", "--quiet", service, "stop"]
    subprocess.Popen(cmd, close_fds=True, preexec_fn=fork_handler, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    splash.progress(1)

def getServices(bus, all=False):
    if all:
        obj = bus.get_object("tr.org.pardus.comar", "/", introspect=False)
        return obj.listModelApplications("System.Service", dbus_interface="tr.org.pardus.comar")
    else:
        enabled = set(os.listdir("/etc/mudur/services/enabled"))
        conditional = set(os.listdir("/etc/mudur/services/conditional"))
        return enabled.union(conditional)

def startServices(extras=None):
    os.setuid(0)
    import dbus
    try:
        bus = dbus.SystemBus()
    except dbus.DBusException:
        ui.error(_("Cannot connect to DBus, services won't be started"))
        return
    # Almost everything depends on logger, so start manually
    startService("sysklogd")
    if not waitBus("/dev/log", stream=False):
        ui.warn(_("Cannot start system logger"))

    if extras:
        for service in extras:
            try:
                startService(service)
            except dbus.DBusException:
                pass
        return
    # Remove unnecessary lock files - bug #7212
    for _file in os.listdir("/etc/network"):
        if _file.startswith("."):
            os.unlink(os.path.join("/etc/network", _file))
    # Start network service
    import pardus.iniutils
    obj = bus.get_object("tr.org.pardus.comar", "/", introspect=False)
    for script in obj.listModelApplications("Net.Link", dbus_interface="tr.org.pardus.comar"):
        db = pardus.iniutils.iniDB(os.path.join("/etc/network", script))
        for profile in db.listDB():
            if db.getDB(profile).get("state", "down") == "up":
                device = db.getDB(profile).get("device", None)
                if not device:
                    continue
                device = device.rsplit("_")[-1]
                try:
                    ui.info(_("Bringing up interface %s") % device)
                    obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
                    obj.setState(profile, "up", dbus_interface="tr.org.pardus.comar.Net.Link", ignore_reply=True)
                except dbus.DBusException:
                    ui.error(_("Unable to bring up interface %s") % device)
    if not config.get("safe"):
        ui.info(_("Starting services"))
        services = getServices(bus)
        # Give login screen a headstart
        head_start = config.get("head_start")
        if head_start and head_start in services:
            readyService(head_start)
            services.remove(head_start)
        for service in services:
            readyService(service)
        waitBus("/tmp/.X11-unix/X0")
        splash.updateProgressBar(100)
        time.sleep(2)

def stopServices():
    ui.info(_("Stopping services"))
    import dbus
    try:
        bus = dbus.SystemBus()
    except dbus.DBusException:
        return

    for service in getServices(bus, all=True):
        stopService(service)

def stopDBus():
    ui.info(_("Stopping DBus"))
    run("start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/dbus/pid")


#
# Initialization functions
#

def setupUdev():
    ui.info(_("Mounting /dev"))
    # many video drivers require exec access in /dev
    mount("/dev", "-t tmpfs -o exec,nosuid,mode=0755 udev /dev")

    # At this point, an empty /dev is mounted on ramdisk
    # We need /dev/null for calling run_quiet
    os.mknod("/dev/null", 0666 | stat.S_IFCHR, os.makedev(1, 3))

    devpath = "/lib/udev/devices"
    if os.path.exists(devpath):
        ui.info(_("Restoring saved device states"))
        for name in os.listdir(devpath):
            run_quiet(
                "/bin/cp",
                "--preserve=all", "--recursive", "--update",
                "%s/%s" % (devpath, name), "/dev/"
            )

    # When these files are missing, lots of trouble happens
    # so we double check that they are there
    ensureDirs("/dev/pts")
    ensureDirs("/dev/shm")
    devlinks = (
        ("/dev/fd", "/proc/self/fd"),
        ("/dev/stdin", "fd/0"),
        ("/dev/stdout", "fd/1"),
        ("/dev/stderr", "fd/2"),
        ("/dev/core", "/proc/kcore"),
    )
    for link in devlinks:
        if not os.path.lexists(link[0]):
            os.symlink(link[1], link[0])

    ui.info(_("Starting udev"))

    if config.kernel_ge("2.6.16"):
        # disable uevent helper, udevd listens to netlink
        write("/sys/kernel/uevent_helper", " ")
        run("/sbin/udevd", "--daemon")

        ui.info(_("Populating /dev"))

        # create needed queue directory
        ensureDirs("/dev/.udev/queue/")

        # trigger events for all devices
        run("/sbin/udevadm", "trigger")
        # wait for events to finish
        run("/sbin/udevadm", "settle", "--timeout=180")
    else:
        # no netlink support in old kernels
        write("/proc/sys/kernel/hotplug", "/sbin/udevsend")
        run("/sbin/udevstart")

    # NOTE: handle lvm here when used by pardus

def checkRoot():
    if not config.get("livecd"):
        ui.info(_("Remounting root filesystem read-only"))
        run("/bin/mount", "-n", "-o", "remount,ro", "/")

        ent = config.get_mount("/")
        if config.get("forcefsck") or (len(ent) > 5 and ent[5] != "0"):
            if config.get("forcefsck"):
                splash.verbose()
                ui.info(_("Checking root filesystem (full check forced)"))
                t = run_full("/sbin/fsck", "-C", "-a", "-f", "/")
                # /forcefsck isn't deleted because checkFS needs it.
                # it'll be deleted in that function.
            else:
                ui.info(_("Checking root filesystem"))
                t = run_full("/sbin/fsck", "-C", "-T", "-a", "/")
            if t == 0:
                pass
            elif t == 2 or t == 3:
                splash.verbose()
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

    curkernel = os.uname()[2]
    ui.info(_("Calculating module dependencies for %s" % curkernel))

    if os.path.exists("/etc/modprobe.mudur"):
        depkernel = loadFile("/etc/modprobe.mudur").rstrip("\n")
        if depkernel != curkernel:
            run_quiet("sbin/depmod", "-a")
    else:
        run_quiet("sbin/depmod", "-a")
    file("/etc/modprobe.mudur", "w").write("%s\n" % curkernel)

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

    if config.get("forcefsck"):
        splash.verbose()
        ui.info(_("A full fsck has been forced"))
        t = run_full("/sbin/fsck", "-C", "-R", "-A", "-a", "-f")
        # remove forcefsck file
        os.unlink("/forcefsck")
    else:
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
    run("/bin/mount", "-at", "noproc,noshm,nocifs,nonfs,nonfs4")

    ui.info(_("Activating swap"))
    run("/sbin/swapon", "-a")

def remoteMount(old_handler):
    data = loadFile("/etc/fstab").split("\n")
    data = filter(lambda x: not (x.startswith("#") or x == ""), data)
    fstab = map(lambda x: x.split(), data)
    netmounts = filter(lambda x: len(x) > 2 and x[2] in ("cifs", "nfs", "nfs4"), fstab)
    if len(netmounts) == 0:
        return
    # If user has set some network filesystems in fstab, we should wait
    # until they are mounted, otherwise several programs can fail if
    # /home or /var is on a network share.

    fs_types = map(lambda x: x[2], netmounts)
    if "nfs" in fs_types or "nfs4" in fs_types:
        ui.info(_("Starting portmap service for NFS"))
        startServices(["portmap"])

    ui.info(_("Mounting remote filesystems (CTRL-C stops trying)"))
    try:
        signal.signal(signal.SIGINT, old_handler)
        while True:
            next_set = []
            for item in netmounts:
                ret = run_quiet("/bin/mount", item[1])
                if ret != 0:
                    next_set.append(item)
            if len(next_set) == 0:
                break
            netmounts = next_set
            time.sleep(0.5)
    except KeyboardInterrupt:
        ui.error(_("Mounting skipped with CTRL-C, remote shares are not accessible!"))
        time.sleep(1)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

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

    ui.info(_("Setting system clock to hardware clock"))

    opts = "--utc"
    if config.get("clock") != "UTC":
        opts = "--localtime"

    if config.get("clock_adjust") == "yes":
        adj = "--adjust"
        if not touch("/etc/adjtime"):
            adj = "--noadjfile"
        elif os.stat("/etc/adjtime").st_size == 0:
            write("/etc/adjtime", "0.0 0 0.0\n")
        t = capture("/sbin/hwclock", adj, opts)
        if t[1] != '':
            ui.error(_("Failed to adjust systematic drift of the hardware clock"))

    t = capture("/sbin/hwclock", "--hctosys", opts)
    if t[1] != '':
        ui.error(_("Failed to set system clock to hardware clock"))

def cleanupVar():
    ui.info(_("Cleaning up /var"))
    for root,dirs,files in os.walk("/var/run"):
        for f in files:
            if f != "utmp" and f != "random-seed":
                os.unlink(os.path.join(root, f))

def cleanupTmp():
    ui.info(_("Cleaning up /tmp"))

    cleanup_list = (
        "/tmp/gpg-*",
        "/tmp/kde-*",
        "/tmp/kio*",
        "/tmp/kio*",
        "/tmp/ksocket-*",
        "/tmp/mc-*",
        "/tmp/pisi-*",
        "/tmp/pulse-*",
        "/tmp/quilt.*",
        "/tmp/ssh-*",
        "/tmp/.*-unix",
        "/tmp/.X*-lock"
    )
    map(delete, cleanup_list)

    ensureDirs("/tmp/.ICE-unix")
    os.chown("/tmp/.ICE-unix", 0, 0)
    os.chmod("/tmp/.ICE-unix", 01777)

    ensureDirs("/tmp/.X11-unix")
    os.chown("/tmp/.X11-unix", 0, 0)
    os.chmod("/tmp/.X11-unix", 01777)

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
    stopDBus()

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
            run("/bin/sync")
            run("/bin/sync")
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
    splash.updateProgressBar(0)
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

old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGQUIT, signal.SIG_IGN)
signal.signal(signal.SIGTSTP, signal.SIG_IGN)
sys.excepthook = except_hook
os.umask(022)

# Setup path just in case
os.environ["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:" + os.environ["PATH"]

# Setup output and load configuration
logger = Logger()
config = Config()
splash = Splash()
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
    splash.init(0)

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

    setClock()

    setSystemLanguage()

    # better performance for SMP systems, /var/run must be mounted rw before this
    if os.path.exists("/usr/sbin/irqbalance"):
        run("/usr/sbin/irqbalance")

    # when we exit this runlevel, init will write a boot record to utmp
    write("/var/run/utmp", "")
    touch("/var/log/wtmp")
    run("/bin/chgrp", "utmp", "/var/run/utmp", "/var/log/wtmp")
    run("/bin/chmod", "0664", "/var/run/utmp", "/var/log/wtmp")

elif sys.argv[1] == "boot":
    splash.init(60)

    ui.info(_("Setting up localhost"))
    run("/sbin/ifconfig", "lo", "127.0.0.1", "up")
    run("/sbin/route", "add", "-net", "127.0.0.0", "netmask", "255.0.0.0",
        "gw", "127.0.0.1", "dev", "lo")

    run("/sbin/sysctl", "-q", "-p", "/etc/sysctl.conf")

    cleanupVar()

    if mdirdate("/etc/env.d") > mdate("/etc/profile.env"):
        ui.info(_("Updating environment variables"))
        run("/sbin/update-environment")

    cleanupTmp()

    startDBus()

    ttyUnicode()

    remoteMount(old_handler)

elif sys.argv[1] == "default":
    splash.init(75)

    ui.info(_("Triggering udev events which are failed during a previous run"))
    # Trigger only the events which are failed during a previous run.
    run("/sbin/udevadm", "trigger", "--retry-failed")

    if not config.get("safe") and os.path.exists("/etc/conf.d/local.start"):
        run("/bin/bash", "/etc/conf.d/local.start")

    ui.info(_("Loading CPUFreq modules"))
    cpu = CPU()
    cpu.loadCPUfreq()

    startServices()
    splash.verbose()

elif sys.argv[1] == "single":
    stopServices()

elif sys.argv[1] == "reboot" or sys.argv[1] == "shutdown":
    splash.init(90, False)
    splash.silent()

    # Log the operation before unmounting file systems
    logger.sync()

    if not config.get("safe") and os.path.exists("/etc/conf.d/local.stop"):
        run("/bin/bash", "/etc/conf.d/local.stop")
    splash.progress(40)

    stopSystem()

    if sys.argv[1] == "reboot":
        # Try to reboot using kexec, if kernel supports it.
        kexecFile = "/sys/kernel/kexec_loaded"
        if os.path.exists(kexecFile) and int(file(kexecFile).read().strip()):
            ui.info(_("Trying initiate a warm reboot (skipping BIOS with kexec kernel)"))
            run_quiet("/usr/sbin/kexec", "-e")

        # Shut down all network interfaces just before halt or reboot,
        # When halting the system do a poweroff. This is the default when halt is called as powerof
        # Don't write the wtmp record.
        run("/sbin/reboot", "-idp")
        # Force halt or reboot, don't call shutdown
        run("/sbin/reboot", "-f")
    else:
        run("/sbin/halt", "-ihdp")
        run("/sbin/halt", "-f")
    # Control never reaches here

logger.sync()

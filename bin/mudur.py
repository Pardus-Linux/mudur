#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Pardus boot and initialization system
# Copyright (C) 2006-2009 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import fcntl
import signal
import shutil

import os
import re
import sys
import time
import gettext
import subprocess

########
# i18n #
########

__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

#######################
# Convenience methods #
#######################

def waitBus(unix_name, timeout=5, wait=0.1, stream=True):
    """Waits over a AF_UNIX socket for a given duration."""
    import socket
    itimeout = timeout
    if stream:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    while timeout > 0:
        try:
            sock.connect(unix_name)
            ui.debug("Waited %.2f seconds for '%s'" % (itimeout-timeout, unix_name))
            return True
        except:
            timeout -= wait
        time.sleep(wait)

    ui.debug("Waited %.2f seconds for '%s'" % (itimeout-timeout, unix_name))
    return False

def loadFile(path):
    """Reads the contents of a file and returns it."""
    f = open(path, "r")
    data = f.read()
    f.close()
    return data

def loadConfig(path):
    """Reads key=value formatted config files and returns a dictionary."""
    d = {}
    for line in file(path):
        if line != "" and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith('"') or value.startswith("'"):
                value = value[1:-1]
            d[key] = value
    return d

def writeToFile(filename, data=""):
    """Write data to file."""
    f = open(filename, "w")
    f.write(data)
    f.close()

def createDirectory(path):
    """Create missing directories in the path."""
    if not os.path.exists(path):
        os.makedirs(path)

def mount(part, args):
    """Mounts the partition with arguments."""
    ent = config.get_fstab_entry_with_mountpoint(part)
    if ent and len(ent) > 3:
        args = "-t %s -o %s %s %s" % (ent[2], ent[3], ent[0], ent[1])
    os.system("/bin/mount -n %s" % args)

def mdate(filename):
    """Returns the last modification date of a file."""
    mtime = 0
    if os.path.exists(filename):
        mtime = os.path.getmtime(filename)
    return mtime

def mdirdate(dirname):
    """Returns the last modification date of a directory."""
    # Directory mdate is not updated for file updates, so we check each file
    # Note that we dont recurse into subdirs, modules.d, env.d etc are all flat
    d = mdate(dirname)
    for f in os.listdir(dirname):
        d2 = mdate(os.path.join(dirname, f))
        if d2 > d:
            d = d2
    return d

def touch(filename):
    """Updates file modification date, create file if necessary"""
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

def getKernelOption(option):
    """Get a dictionary of args for the given kernel command line option"""
    args = {}

    try:
        cmdline = open("/proc/cmdline").read().split()
    except IOError:
        return args

    for cmd in cmdline:
        if "=" in cmd:
            optname, optargs = cmd.split("=", 1)
        else:
            optname = cmd
            optargs = ""

        if optname == option:
            for arg in optargs.split(","):
                if ":" in arg:
                    k, v = arg.split(":", 1)
                    args[k] = v
                else:
                    args[arg] = ""
    return args

####################################
# Process spawning related methods #
####################################

def capture(*cmd):
    """Captures the output of a command without running a shell."""
    a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return a.communicate()

def run_async(cmd, stdout=None, stderr=None):
    """Runs a command in background and redirects the outputs optionally."""
    fstdout = stdout if stdout else "/dev/null"
    fstderr = stderr if stderr else "/dev/null"

    return subprocess.Popen(cmd, stdout=open(fstdout, "w"), stderr=open(fstderr, "w")).pid

def run(*cmd):
    """Runs a command without running a shell, only output errors."""
    return subprocess.call(cmd, stdout=open("/dev/null", "w"))

def run_full(*cmd):
    """Runs a command without running a shell, with full output."""
    return subprocess.call(cmd)

def run_quiet(*cmd):
    """Runs a command without running a shell and no output."""
    f = file("/dev/null", "w")
    return subprocess.call(cmd, stdout=f, stderr=f)

################
# Logger class #
################

class Logger:
    """Logger class for dumping into /var/log/mudur.log."""
    def __init__(self):
        self.lines = ["\n"]

    def log(self, msg):
        stamp = time.strftime("%b %d %H:%M:%S")
        # Strip color characters
        msg = re.sub("(\033.*?m)", "", msg)
        self.lines.append("[%.3f] %s %s\n" % (time.time(), stamp, msg))

    def sync(self):
        try:
            f = open("/var/log/mudur.log", "a")
            self.lines.append("\n")
            f.writelines(self.lines)
            f.close()
        except IOError:
            ui.error(_("Cannot write mudur.log, read-only file system"))

################
# Config class #
################

class Config:
    """Configuration class which parsing /proc/cmdline to get mudur related options."""
    def __init__(self):
        self.fstab = None

        # Parse kernel version
        vers = os.uname()[2].replace("_", ".").replace("-", ".")
        self.kernel = vers.split(".")

        # Default options for mudur= in /proc/cmdline
        self.opts = {
            "language": "en",
            "clock": "local",
            "clock_adjust": "no",
            "tty_number": "6",
            "keymap": None,
            "debug": True,
            "livecd": False,
            "lvm": False,
            "safe": False,
            "forcefsck": False,
            "preload": False,
            "head_start": "",
            "services": "",
        }

        # Load config file if exists
        if os.path.exists("/etc/conf.d/mudur"):
            self.opts.update(loadConfig("/etc/conf.d/mudur"))

        # File system check can be requested with a file
        self.opts["forcefsck"] = os.path.exists("/forcefsck")

    def parse_kernel_opts(self):
        # We need to mount /proc before accessing kernel options
        # This function is called after that, and finish parsing options
        # We dont print any messages before, cause language is not known
        opts = getKernelOption("mudur")

        # Fill in the options
        self.opts["livecd"] = opts.has_key("livecd") or opts.has_key("livedisk") or opts.has_key("thin")

        for k in [_k for _k in opts.keys() if _k not in ("livecd", "livedisk", "thin")]:
            if opts[k]:
                self.opts[k] = opts[k]
            else:
                self.opts[k] = True

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

    def get_fstab_entry_with_mountpoint(self, mountpoint):
        if not self.fstab:
            data = loadFile("/etc/fstab").split("\n")
            data = filter(lambda x: not (x.startswith("#") or x == ""), data)
            self.fstab = map(lambda x: x.split(), data)

        for entry in self.fstab:
            if entry and len(entry) > 3 and entry[1] == mountpoint:
                return entry

    def is_virtual(self):
        # Xen detection
        if os.path.exists("/proc/xen/capabilities"):
            dom0 = loadFile("/proc/xen/capabilities").rstrip("\n")
            # if we are in dom0 then no extra work needed, boot normally
            if dom0 != "control_d":
                # if we are in domU then no need to set/sync clock and others
                return True
        return False

################
# Splash class #
################

class Splash:
    def __init__(self):
        self.enabled = False
        self.increasing = True
        self.percent = 0

    def init(self, percent, increasing=True):
        if os.path.exists("/proc/splash"):
            self.enabled = getKernelOption("splash").has_key("silent")
            self.increasing = increasing
            self.percent = percent

    def silent(self):
        if self.enabled:
            writeToFile("/proc/splash", "silent\n")
            self.updateProgressBar()

    def verbose(self):
        if self.enabled:
            writeToFile("/proc/splash", "verbose\n")

    def updateProgressBar(self, percent=None):
        if self.enabled:
            if percent is not None:
                self.percent = percent
            pe = int(655.35 * self.percent)
            writeToFile("/proc/splash", "show %d" % pe)

    def progress(self, delta=3):
        if self.enabled:
            if self.increasing:
                self.updateProgressBar(self.percent + delta)
            else:
                self.updateProgressBar(self.percent - delta)

############
# UI class #
############

class UI:
    UNICODE_MAGIC = "\x1b%G"

    def __init__(self):
        self.colors = {'red'        : '\x1b[31;01m', # BAD
                       'blue'       : '\x1b[34;01m',
                       'cyan'       : '\x1b[36;01m',
                       'gray'       : '\x1b[30;01m',
                       'green'      : '\x1b[32;01m', # GOOD
                       'light'      : '\x1b[37;01m',
                       'yellow'     : '\x1b[33;01m', # WARN
                       'magenta'    : '\x1b[35;01m',
                       'reddark'    : '\x1b[31;0m',
                       'bluedark'   : '\x1b[34;0m',
                       'cyandark'   : '\x1b[36;0m',
                       'graydark'   : '\x1b[30;0m',
                       'greendark'  : '\x1b[32;0m',
                       'magentadark': '\x1b[35;0m',
                       'normal'     : '\x1b[0m'}     # NORMAL

    def greet(self):
        print self.UNICODE_MAGIC
        if os.path.exists("/etc/pardus-release"):
            release = loadFile("/etc/pardus-release").rstrip("\n")
            if config.get("safe"):
                release = "%s (%s)" % (release, _("Safe Mode"))
            print "\x1b[1m  %s  \x1b[0;36mhttp://www.pardus.org.tr\x1b[0m" % release
        else:
            self.error(_("Cannot find /etc/pardus-release"))
        print

    def info(self, msg):
        if config.get("debug"):
            logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.colors['green'], self.colors['normal'], msg.encode("utf-8")))
        splash.progress()

    def warn(self, msg):
        splash.verbose()
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.colors['yellow'], self.colors['normal'], msg.encode("utf-8")))

    def error(self, msg):
        try:
            splash.verbose()
        except IOError:
            pass
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.colors['red'], self.colors['normal'], msg.encode("utf-8")))

    def debug(self, msg):
        if config.get("debug"):
            logger.log(msg)

    def colorize(self, uicolor, msg):
        return "%s%s%s" % (self.colors[uicolor], msg, self.colors['normal'])

##################
# Language class #
##################

class Language:
    def __init__(self, keymap, font, trans, locale):
        self.keymap = keymap
        self.font = font
        self.trans = trans
        self.locale = locale


########################################
# Language and console related methods #
########################################

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
    "sv": Language("sv-latin1", "lat0-16", "8859-1", "sv_SE.UTF-8"),
}

def setConsole():
    """Setups encoding, font and mapping for console."""
    if not config.is_virtual():
        lang = config.get("language")
        keymap = config.get("keymap")
        language = languages[lang]

        # Now actually set the values
        run("/usr/bin/kbd_mode", "-u")
        run_quiet("/bin/loadkeys", keymap)
        run("/usr/bin/setfont", "-f", language.font, "-m", language.trans)

def setSystemLanguage():
    """Sets the system language."""
    lang = config.get("language")
    keymap = config.get("keymap")
    language = languages[lang]

    # Put them in /etc, so other programs like kdm can use them
    # without duplicating default->mudur.conf->kernel-option logic
    # we do here. Note that these are system-wide not per user,
    # and only for reading.
    createDirectory("/etc/mudur")
    writeToFile("/etc/mudur/language", "%s\n" % lang)
    writeToFile("/etc/mudur/keymap", "%s\n" % keymap)
    writeToFile("/etc/mudur/locale", "%s\n" % language.locale)

    # Update environment if necessary
    content = "LANG=%s\nLC_ALL=%s\n" % (language.locale, language.locale)
    if content != loadFile("/etc/env.d/03locale"):
        writeToFile("/etc/env.d/03locale", content)

def setTranslation():
    """Loads the translation catalogue for mudur."""
    global __trans
    global _
    lang = config.get("language")
    __trans = gettext.translation('mudur', languages=[lang], fallback=True)
    _ = __trans.ugettext

def ttyUnicode():
    """Makes TTYs unicode compatible."""
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

######################################
# Service management related methods #
######################################

def fork_handler():
    """Callback which is passed to Popen as preexec_fn."""
    import termios

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

def startService(service, command="start"):
    """Starts the service."""
    cmd = ["/bin/service", "--quiet", service, command]
    ui.debug("Starting service %s" % service)
    subprocess.Popen(cmd, close_fds=True, preexec_fn=fork_handler, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ui.debug("%s started" % service)
    splash.progress(1)

def stopService(service):
    """Stops the service."""
    cmd = ["/bin/service", "--quiet", service, "stop"]
    ui.debug("Stopping service %s" % service)
    subprocess.Popen(cmd, close_fds=True, preexec_fn=fork_handler, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ui.debug("%s stopped" % service)
    splash.progress(1)

def getServices(bus, all=False):
    """Requests and returns the list of system services through COMAR."""
    obj = bus.get_object("tr.org.pardus.comar", "/", introspect=False)
    services = obj.listModelApplications("System.Service", dbus_interface="tr.org.pardus.comar")
    if all:
        return services
    else:
        enabled = set(os.listdir("/etc/mudur/services/enabled"))
        conditional = set(os.listdir("/etc/mudur/services/conditional"))
        return enabled.union(conditional).intersection(set(services))

def startNetwork():
    """Sets up network connections if any."""
    import dbus
    import comar

    # Remote mount required?
    need_remount = remoteMount(dry_run=True)

    link = comar.Link()

    def ifUp(package, name, info):
        ifname = info["device_id"].split("_")[-1]
        ui.info((_("Bringing up %s") + ' (%s)') % (ui.colorize("light", ifname), ui.colorize("cyan", name)))
        if need_remount:
            try:
                link.Network.Link[package].setState(name, "up")
            except dbus.DBusException:
                ui.error((_("Unable to bring up %s") + ' (%s)') % (ifname, name))
                return False
        else:
            link.Network.Link[package].setState(name, "up", quiet=True)
        return True

    def ifDown(package, name):
        try:
            link.Network.Link[package].setState(name, "down", quiet=True)
        except dbus.DBusException:
            pass

    def getConnections(package):
        connections = {}
        try:
            for name in link.Network.Link[package].connections():
                connections[name] = link.Network.Link[package].connectionInfo(name)
        except dbus.DBusException:
            pass
        return connections

    try:
        packages = list(link.Network.Link)
    except dbus.DBusException:
        packages = []

    for package in packages:
        try:
            linkInfo = link.Network.Link[package].linkInfo()
        except dbus.DBusException:
            break
        if linkInfo["type"] == "net":
            for name, info in getConnections(package).iteritems():
                if info.get("state", "down").startswith("up"):
                    ifUp(package, name, info)
                else:
                    ifDown(package, name)
        elif linkInfo["type"] == "wifi":
            # Scan remote access points
            devices = {}
            try:
                for deviceId in link.Network.Link[package].deviceList():
                    devices[deviceId] = []
                    for point in link.Network.Link[package].scanRemote(deviceId):
                        devices[deviceId].append(unicode(point["remote"]))
            except dbus.DBusException:
                break
            # Try to connect last connected profile
            skip = False
            for name, info in getConnections(package).iteritems():
                if info.get("state", "down").startswith("up") and info.get("device_id", None) in devices and info["remote"] in devices[info["device_id"]]:
                    ifUp(package, name, info)
                    skip = True
                    break
            # There's no last connected profile, try to connect other profiles
            if not skip:
                # Reset connection states
                for name, info in getConnections(package).iteritems():
                    ifDown(package, name)
                # Try to connect other profiles
                for name, info in getConnections(package).iteritems():
                    if info.get("device_id", None) in devices and info["remote"] in devices[info["device_id"]]:
                        ifUp(package, name, info)
                        break

    if need_remount:
        from pardus.netutils import waitNet
        if waitNet():
            remoteMount()
        else:
            ui.error(_("No network connection, skipping remote mount."))

def startServices(extras=None):
    """Sends start signals to the required services through D-Bus."""
    import dbus

    os.setuid(0)
    try:
        bus = dbus.SystemBus()
    except dbus.DBusException:
        ui.error(_("Cannot connect to DBus, services won't be started"))
        return

    if extras:
        # Start only the services given in extras
        for service in extras:
            try:
                startService(service)
            except dbus.DBusException:
                pass

    else:
        # Remove unnecessary lock files - bug #7212
        for _file in os.listdir("/etc/network"):
            if _file.startswith("."):
                os.unlink(os.path.join("/etc/network", _file))

        # Start network service
        try:
            startNetwork()
        except Exception, e:
            ui.error(_("Unable to start network:\n  %s") % e)

        # Almost everything depends on logger, so start manually
        startService("sysklogd")
        if not waitBus("/dev/log", stream=False, timeout=15):
            ui.warn(_("Cannot start system logger"))

        if not config.get("safe"):
            ui.info(_("Starting services"))
            services = getServices(bus)

            # Remove redundant sysklogd
            if "sysklogd" in services:
                services.remove("sysklogd")

            # Give login screen a headstart
            head_start = config.get("head_start")
            run_head_start = head_start and head_start in services
            if run_head_start:
                startService(head_start, command="ready")
                services.remove(head_start)
            for service in services:
                startService(service, command="ready")

            if run_head_start and not getKernelOption("xorg").has_key("off"):
                waitBus("/tmp/.X11-unix/X0", timeout=10)

                # Avoid users trying to login using VT
                # because of the X startup delay.
                time.sleep(1)

            splash.updateProgressBar(100)

        # Close the handle
        bus.close()

def stopServices():
    """Sends stop signals to all available services through D-Bus."""
    import dbus

    ui.info(_("Stopping services"))
    try:
        bus = dbus.SystemBus()
    except dbus.DBusException:
        return

    for service in getServices(bus, all=True):
        stopService(service)

    # Close the handle
    bus.close()


############################
# D-Bus start/stop methods #
############################

def startDBus():
    """Starts the D-Bus service."""
    os.setuid(0)
    ui.info(_("Starting %s") % "DBus")
    if not os.path.exists("/var/lib/dbus/machine-id"):
        run("/usr/bin/dbus-uuidgen", "--ensure")
    run("/sbin/start-stop-daemon", "-b", "--start", "--quiet",
        "--pidfile", "/var/run/dbus/pid", "--exec", "/usr/bin/dbus-daemon",
        "--", "--system")
    waitBus("/var/run/dbus/system_bus_socket")

def stopDBus():
    """Stops the D-Bus service."""
    ui.info(_("Stopping %s") % "DBus")
    run("/sbin/start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/dbus/pid")

###############################
# Other boot related services #
###############################

def startPreload():
    """Starts the Preload service."""
    if os.path.exists("/sbin/preload") and config.get("preload"):
        ui.info(_("Starting %s") % "Preload")
        run("/sbin/start-stop-daemon", "-b", "-m", "--start", "--quiet",
            "--pidfile", "/var/run/preload.pid", "--exec", "/sbin/preload",
            "--", "-f")
        run("/usr/bin/ionice", "-c3", "-p", open("/var/run/preload.pid", "r").read().strip())

def stopPreload():
    """Stops the Preload service."""
    if os.path.exists("/sbin/preload") and config.get("preload"):
        ui.info(_("Stopping %s") % "Preload")
        run("/sbin/start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/preload.pid")

#############################
# UDEV management functions #
#############################

def copyUdevRules():
    """Copies persistent udev rules from /dev into /etc/udev/rules."""
    import glob

    # Copy udevtrigger log file to /var/log
    if os.path.exists("/dev/.udevmonitor.log"):
        try:
            shutil.move("/dev/.udevmonitor.log", "/var/log/udevmonitor.log")
        except IOError:
            # Can't move it, no problem.
            pass

    # Moves any persistent rules from /dev/.udev to /etc/udev/rules.d
    for rule in glob.glob("/dev/.udev/tmp-rules--*"):
        dest = "/etc/udev/rules.d/%s" % os.path.basename(rule).split("tmp-rules--")[1]
        try:
            shutil.move(rule, dest)
        except IOError:
            ui.warn(_("Can't move persistent udev rules from /dev/.udev"))
            pass

def setupUdev():
    """Prepares the initial setup for udev daemon initialization."""

    ui.info(_("Mounting /dev"))

    # Many video drivers require exec access in /dev
    mount("/dev", "-t tmpfs -o exec,nosuid,mode=0755,size=10M udev /dev")

    # At this point, an empty /dev is mounted on ramdisk
    # We need /dev/null for calling run_quiet
    S_IFCHR = 8192
    os.mknod("/dev/null", 0666 | S_IFCHR, os.makedev(1, 3))

    # Copy over any persistent things
    devpath = "/lib/udev/devices"
    if os.path.exists(devpath):
        for name in os.listdir(devpath):
            run_quiet(
                "/bin/cp",
                "--preserve=all", "--recursive", "--update",
                "%s/%s" % (devpath, name), "/dev/"
            )

    # When these files are missing, lots of trouble happens
    # so we double check their existence
    createDirectory("/dev/pts")
    createDirectory("/dev/shm")

    devlinks = (
        ("/dev/fd", "/proc/self/fd"),
        ("/dev/stdin", "fd/0"),
        ("/dev/stdout", "fd/1"),
        ("/dev/stderr", "fd/2"),
        ("/dev/core", "/proc/kcore"),
    )

    # Create if any of the above links is missing
    for link in devlinks:
        if not os.path.lexists(link[0]):
            os.symlink(link[1], link[0])

def startUdev():
    """Prepares the startup of udev daemon and starts it."""

    # Start udev daemon
    ui.info(_("Starting udev"))

    run("/sbin/start-stop-daemon",
        "--start", "--quiet",
        "--exec", "/sbin/udevd", "--", "--daemon")

    # Create needed queue directory
    createDirectory("/dev/.udev/queue/")

    # Log things that trigger does
    pid = run_async(["/sbin/udevadm", "monitor", "--env"],
                    stdout="/dev/.udevmonitor.log")

    # Filling up /dev by triggering uevents
    ui.info(_("Populating /dev"))

    # Trigger events for all devices
    run("/sbin/udevadm", "trigger")

    # Wait for events to finish
    run("/sbin/udevadm", "settle", "--timeout=60")

    # Stop udevmonitor
    os.kill(pid, 15)

    # NOTE: handle lvm here when used by pardus
    # These could be achieved using some udev rules.

    if config.get("lvm"):
        run_quiet("/sbin/modprobe", "dm-mod")
        run_quiet("/usr/sbin/dmsetup", "mknodes")
        run_quiet("/usr/sbin/lvm", "vgscan", "--ignorelockingfailure")
        run_quiet("/usr/sbin/lvm", "vgchange", "-ay", "--ignorelockingfailure")

def stopUdev():
    """Stops udev daemon."""
    run("/sbin/start-stop-daemon",
        "--stop", "--exec", "/sbin/udevd")


##############################
# Filesystem related methods #
##############################

def updateMtabForRoot():
    """Calls mount -f to update mtab for a previous mount."""
    MOUNT_FAILED_LOCK = 16
    if os.path.exists("/etc/mtab~"):
        try:
            ui.warn(_("Removing stale lock file /etc/mtab~"))
            os.unlink("/etc/mtab~")
        except OSError:
            ui.warn(_("Failed removing stale lock file /etc/mtab~"))
            pass

    return (run_quiet("/bin/mount", "-f", "/") == MOUNT_FAILED_LOCK)

def checkRootFileSystem():
    """Checks root filesystem with fsck if required."""
    if not config.get("livecd"):

        entry = config.get_fstab_entry_with_mountpoint("/")
        if not entry:
            ui.warn(_("/etc/fstab doesn't contain an entry for the root filesystem"))
            return

        if config.get("forcefsck") or (len(entry) > 5 and entry[5] != "0"):

            # Remount root filesystem read-only for fsck without writing to mtab (-n)
            ui.info(_("Remounting root filesystem read-only"))
            run_quiet("/bin/mount", "-n", "-o", "remount,ro", "/")

            if config.get("forcefsck"):
                splash.verbose()
                ui.info(_("Checking root filesystem (full check forced)"))
                # -y: Fix whatever the error is without user's intervention
                t = run_full("/sbin/fsck", "-C", "-y", "-f", "/")
                # /forcefsck isn't deleted because checkFileSystems needs it.
                # it'll be deleted in that function.
            else:
                ui.info(_("Checking root filesystem"))
                t = run_full("/sbin/fsck", "-C", "-T", "-a", "/")
            if t == 0:
                # No errors,just go on
                pass
            elif t == 2 or t == 3:
                # Actually 2 means that a reboot is required, fsck man page doesn't
                # mention about 3 but let's leave it as it's harmless.
                splash.verbose()
                ui.warn(_("Filesystem repaired, but reboot needed!"))
                for i in range(4):
                    print "\07"
                    time.sleep(1)
                ui.warn(_("Rebooting in 10 seconds..."))
                time.sleep(10)
                ui.warn(_("Rebooting..."))
                run("/sbin/reboot", "-f")
                # Code should never reach here
            else:
                ui.error(_("Filesystem could not be repaired"))
                run_full("/sbin/sulogin")
                # Code should never reach here

        else:
            ui.info(_("Skipping root filesystem check (fstab's passno == 0)"))

def mountRootFileSystem():
    """Mounts root filesystem."""

    # Let's remount read/write again.
    ui.info(_("Remounting root filesystem read/write"))

    # We remount here without writing to mtab (-n)
    if run_quiet("/bin/mount", "-n", "-o", "remount,rw", "/") != 0:
        ui.error(_("Root filesystem could not be mounted read/write\n\
   You can either login below and manually check your filesytem(s) OR\n\
   restart your system, press F3 and select 'FS check' from boot menu\n"))

        # Fail if can't remount r/w
        run_full("/sbin/sulogin")

    # Fix mtab as we didn't update it yet
    try:
        # Double guard against IO exceptions
        writeToFile("/etc/mtab")
    except IOError:
        ui.warn(_("Couldn't synchronize /etc/mtab from /proc/mounts"))
        pass

    # This will actually try to update mtab for /. If it fails because
    # of a stale lock file, it will clear it and return.
    updateMtabForRoot()

    # Update mtab
    for entry in loadFile("/proc/mounts").split("\n"):
        try:
            devpath = entry.split()[1]
        except IndexError:
            continue
        if config.get_fstab_entry_with_mountpoint(devpath):
            run("/bin/mount", "-f", "-o", "remount", devpath)

def checkFileSystems():
    """Checks all the filesystems with fsck if required."""
    if not config.get("livecd"):
        ui.info(_("Checking all filesystems"))

        if config.get("forcefsck"):
            splash.verbose()
            ui.info(_("A full fsck has been forced"))
            # -C: Display completion bars
            # -R: Skip the root file system
            # -A: Check all filesystems found in /etc/fstab
            # -a: Automatically repair without any questions
            # -f: Force checking even it's clean (e2fsck)
            t = run_full("/sbin/fsck", "-C", "-R", "-A", "-a", "-f")

            # remove forcefsck file if it exists
            if os.path.exists("/forcefsck"):
                os.unlink("/forcefsck")
        else:
            # -T: Don't show the title on startup
            t = run_full("/sbin/fsck", "-C", "-T", "-R", "-A", "-a")

        if t == 0:
            pass
        elif t >= 2 and t <= 3:
            ui.warn(_("Filesystem errors corrected"))
        else:
            ui.error(_("Fsck could not correct all errors, manual repair needed"))
            run_full("/sbin/sulogin")

def localMount():
    """Mounts local filesystems and enables swaps if any."""
    # FIXME: /proc/bus/usb is deprecated by /dev/bus/usb, we shouldn't mount it.
    if os.path.exists("/proc/bus/usb") and not os.path.exists("/proc/bus/usb/devices"):
        ui.info(_("Mounting USB filesystem"))
        run("/bin/mount", "-t", "usbfs", "usbfs", "/proc/bus/usb")

    ui.info(_("Mounting local filesystems"))
    run("/bin/mount", "-at", "noproc,nocifs,nonfs,nonfs4")


def remoteMount(dry_run=False):
    """Mounts remote filesystems."""
    data = loadFile("/etc/fstab").split("\n")
    data = filter(lambda x: not (x.startswith("#") or x == ""), data)
    fstab = map(lambda x: x.split(), data)
    netmounts = filter(lambda x: len(x) > 2 and x[2] in ("cifs", "nfs", "nfs4"), fstab)
    if len(netmounts) == 0:
        return False

    if dry_run:
        return True
    # If user has set some network filesystems in fstab, we should wait
    # until they are mounted, otherwise several programs can fail if
    # /home or /var is on a network share.

    fs_types = map(lambda x: x[2], netmounts)
    if "nfs" in fs_types or "nfs4" in fs_types:
        ui.info(_("Starting portmap service for NFS"))
        startServices(["portmap"])

    ui.info(_("Mounting remote filesystems (CTRL-C stops trying)"))
    try:
        signal.signal(signal.SIGINT, signal.default_int_handler)
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
        ui.error(_("Mounting skipped with CTRL-C, remote shares will not be accessible!"))
        time.sleep(1)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

################################################################################
# Other system related methods for hostname setting, modules autoloading, etc. #
################################################################################

def setHostname():
    """Sets the system's hostname."""
    khost = capture("/bin/hostname")[0].rstrip("\n")
    uhost = None
    if os.path.exists("/etc/env.d/01hostname"):
        data = loadFile("/etc/env.d/01hostname")
        i = data.find('HOSTNAME="')
        if i != -1:
            j = data.find('"',i+10)
            if j != -1:
                uhost = data[i+10:j]
        """
        try:
            data = loadFile("/etc/env.d/01hostname").strip().split("HOSTNAME=")[1].strip("\"")
        except IndexError:
            pass
        """

    if khost != "" and khost != "(none)":
        # kernel already got a hostname (pxeboot or something)
        host = khost
    else:
        # if nothing found, use the default hostname 'pardus'
        host = uhost if uhost else "pardus"

    if uhost and host != uhost:
        i = data.find('HOSTNAME="')
        if i != -1:
            j = data.find('"', i+10)
            if j != -1:
                data = data[:i+10] + host + data[j:]
        else:
            data = 'HOSTNAME="' + host + '"\n' + data
        writeToFile("/etc/env.d/01hostname", data)

    ui.info(_("Setting up hostname as '%s'") % ui.colorize("light", host))
    run("/bin/hostname", host)

def autoloadModules():
    """Traverses /etc/modules.autoload.d to autoload kernel modules if any."""
    if os.path.exists("/proc/modules"):
        fn = "/etc/modules.autoload.d/kernel-%s.%s.%s" % (config.kernel[0], config.kernel[1], config.kernel[2])
        if not os.path.exists(fn):
            fn = "/etc/modules.autoload.d/kernel-%s.%s" % (config.kernel[0], config.kernel[1])
        if os.path.exists(fn):
            data = loadFile(fn).split("\n")
            data = filter(lambda x: x != "" and not x.startswith('#'), data)
            for mod in data:
                run("/sbin/modprobe", "-q", "-b", mod)

def setDiskParameters():
    # FIXME: Why do we have this, is it really crucial for booting?
    if config.get("safe"):
        return

    if not os.path.exists("/sbin/hdparm") or not os.path.exists("/etc/conf.d/hdparm"):
        return

    d = loadConfig("/etc/conf.d/hdparm")
    if len(d) > 0:
        ui.info(_("Setting disk parameters"))
        if d.has_key("all"):
            for name in os.listdir("/sys/block/"):
                if name.startswith("hd") and len(name) == 3 and not d.has_key(name):
                    args = ["/sbin/hdparm"]
                    args.extend(d["all"].split())
                    args.append("/dev/%s" % name)
                    run_quiet(*args)
        for key in d:
            if key != "all":
                args = ["/sbin/hdparm"]
                args.extend(d[key].split())
                args.append("/dev/%s" % key)
                run_quiet(*args)


################
# Swap methods #
################

def swapOn():
    """Calls swapon for all swaps in /etc/fstab."""
    ui.info(_("Activating swap space"))
    run("/sbin/swapon", "-a")

def swapOff():
    """Calls swapoff after unmounting tmpfs."""
    # unmount unused tmpfs filesystems before swap
    # (tmpfs can be swapped and you can get a deadlock)
    run_quiet("/bin/umount", "-at", "tmpfs")

    ui.info(_("Deactivating swap space"))
    run_quiet("/sbin/swapoff", "-a")


##############################
# Filesystem cleanup methods #
##############################

def cleanupVar():
    ui.info(_("Cleaning up /var"))
    for root, dirs, files in os.walk("/var/run"):
        for f in files:
            if f != "utmp" and f != "random-seed":
                try:
                    os.unlink(os.path.join(root, f))
                except OSError:
                    pass

def cleanupTmp():
    ui.info(_("Cleaning up /tmp"))

    cleanup_list = (
        "/tmp/gpg-*",
        "/tmp/kde-*",
        "/tmp/kde4-*",
        "/tmp/kio*",
        "/tmp/ksocket-*",
        "/tmp/ksocket4-*",
        "/tmp/mc-*",
        "/tmp/pisi-*",
        "/tmp/pulse-*",
        "/tmp/quilt.*",
        "/tmp/ssh-*",
        "/tmp/.*-unix",
        "/tmp/.X*-lock"
    )

    # Remove directories
    os.system("rm -rf %s" % " ".join(cleanup_list))

    createDirectory("/tmp/.ICE-unix")
    os.chown("/tmp/.ICE-unix", 0, 0)
    os.chmod("/tmp/.ICE-unix", 01777)

    createDirectory("/tmp/.X11-unix")
    os.chown("/tmp/.X11-unix", 0, 0)
    os.chmod("/tmp/.X11-unix", 01777)

########################################
# System time/Clock management methods #
########################################

def setClock():
    """Sets the system time according to /etc."""
    if not config.is_virtual():
        ui.info(_("Setting system clock to hardware clock"))

        # Default is UTC
        opts = "--utc"
        if config.get("clock") != "UTC":
            opts = "--localtime"

        # Default is no
        if config.get("clock_adjust") == "yes":
            adj = "--adjust"
            if not touch("/etc/adjtime"):
                adj = "--noadjfile"
            elif os.stat("/etc/adjtime").st_size == 0:
                writeToFile("/etc/adjtime", "0.0 0 0.0\n")
            t = capture("/sbin/hwclock", adj, opts)
            if t[1] != '':
                ui.error(_("Failed to adjust systematic drift of the hardware clock"))

        t = capture("/sbin/hwclock", "--hctosys", opts)
        if t[1] != '':
            ui.error(_("Failed to set system clock to hardware clock"))

def saveClock():
    """Saves the system time for further boots."""
    if config.get("livecd") or config.is_virtual():
        return

    opts = "--utc"
    if config.get("clock") != "UTC":
        opts = "--localtime"

    ui.info(_("Syncing system clock to hardware clock"))
    t = capture("/sbin/hwclock", "--systohc", opts)
    if t[1] != '':
        ui.error(_("Failed to synchronize clocks"))

def stopSystem():
    """Stops the system."""

    stopServices()
    stopUdev()
    stopDBus()
    stopPreload()
    saveClock()
    swapOff()

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
        ents.sort(key=lambda x: x[1], reverse=True)
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
        ents.sort(key=lambda x: x[1], reverse=True)

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

    ui.info(_("Remounting remaining filesystems read-only"))
    splash.updateProgressBar(0)

    # We parse /proc/mounts but use umount, so this have to agree
    shutil.copy("/proc/mounts", "/etc/mtab")
    if remount_ro():
        if remount_ro():
            remount_ro(True)

##################
# Exception hook #
##################

def except_hook(eType, eValue, eTrace):
    import traceback
    print
    print _("An internal error occured. Please report to the bugs.pardus.org.tr with following information:").encode("utf-8")
    print
    print eType, eValue
    traceback.print_tb(eTrace)
    print
    run_full("/sbin/sulogin")


##################
# Global objects #
##################

logger = Logger()
config = Config()
splash = Splash()
ui = UI()

############################
# Main program starts here #
############################

if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    sys.excepthook = except_hook
    os.umask(022)

    # Setup path just in case
    os.environ["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:" + os.environ["PATH"]

    if sys.argv[1] == "sysinit":

        # Mount /proc
        mount("/proc", "-t proc proc /proc")

        # We need /proc mounted before accessing kernel boot options
        config.parse_kernel_opts()

        # This is who we are...
        ui.greet()

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

        # Mount sysfs
        ui.info(_("Mounting /sys"))
        mount("/sys", "-t sysfs sysfs /sys")

        # Set kernel console log level for cleaner boot
        # only panic messages will be printed
        run("/bin/dmesg", "-n", "1")

        # Prepare the /dev directory for udev startup
        setupUdev()

        # Start udev and event triggering
        startUdev()

        ui.info(_("Mounting /dev/pts"))
        mount("/dev/pts", "-t devpts -o gid=5,mode=0620 devpts /dev/pts")

        # Check root file system
        checkRootFileSystem()

        # Mount root file system
        mountRootFileSystem()

        # Start preload if possible
        startPreload()

        # Grab persistent rules and udev.log file from /dev
        copyUdevRules()

        # Set hostname
        setHostname()

        # Load modules manually written in /etc/modules.autoload.d/kernel-x.y
        autoloadModules()

        # Check all filesystems
        checkFileSystems()

        # Mount local filesystems
        localMount()

        # Activate swap space
        swapOn()

        # Set disk parameters using hdparm
        setDiskParameters()

        # Set the clock
        setClock()

        # Set the system language
        setSystemLanguage()

        # When we exit this runlevel, init will write a boot record to utmp
        writeToFile("/var/run/utmp")
        touch("/var/log/wtmp")
        run("/bin/chgrp", "utmp", "/var/run/utmp", "/var/log/wtmp")
        run("/bin/chmod", "0664", "/var/run/utmp", "/var/log/wtmp")

    elif sys.argv[1] == "boot":
        splash.init(60)

        ui.info(_("Setting up localhost"))
        run("/sbin/ifconfig", "lo", "127.0.0.1", "up")
        run("/sbin/route", "add", "-net", "127.0.0.0",
            "netmask", "255.0.0.0", "gw", "127.0.0.1", "dev", "lo")

        run("/sbin/sysctl", "-q", "-p", "/etc/sysctl.conf")

        # Cleanup /var
        cleanupVar()

        # Update environment variables according to the modification
        # time of the relevant files
        if mdirdate("/etc/env.d") > mdate("/etc/profile.env"):
            ui.info(_("Updating environment variables"))
            if config.get("livecd"):
                run("/sbin/update-environment", "--live")
            else:
                run("/sbin/update-environment")

        # Cleanup /tmp
        cleanupTmp()

        # Start DBUS
        startDBus()

        # Set unicode properties for ttys
        ttyUnicode()

    elif sys.argv[1] == "default":
        splash.init(75)

        # Trigger only the events which are failed during a previous run
        if os.path.exists("/dev/.udev/failed"):
            ui.info(_("Triggering udev events which are failed during a previous run"))
            run("/sbin/udevadm", "trigger", "--type=failed")

        # Source local.start
        if not config.get("safe") and os.path.exists("/etc/conf.d/local.start"):
            run("/bin/bash", "/etc/conf.d/local.start")

        # Start services
        startServices()

        splash.verbose()

    elif sys.argv[1] == "single":
        stopServices()

    elif sys.argv[1] == "reboot" or sys.argv[1] == "shutdown":
        splash.init(90, False)
        splash.silent()

        # Log the operation before unmounting file systems
        logger.sync()

        # Source local.stop
        if not config.get("safe") and os.path.exists("/etc/conf.d/local.stop"):
            run("/bin/bash", "/etc/conf.d/local.stop")

        splash.progress(40)

        # Stop the system
        stopSystem()

        if sys.argv[1] == "reboot":

            # Try to reboot using kexec, if kernel supports it.
            kexecFile = "/sys/kernel/kexec_loaded"

            if os.path.exists(kexecFile) and int(file(kexecFile).read().strip()):
                ui.info(_("Trying to initiate a warm reboot (skipping BIOS with kexec kernel)"))
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

    try:
        logger.sync()
    except IOError:
        pass

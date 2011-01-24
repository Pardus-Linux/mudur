#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Pardus boot and initialization system
# Copyright (C) 2006-2010 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

"""
Pardus booting and initialization system written in Python.
"""

import os
import re
import sys
import time
import signal
import gettext
import subprocess

########
# i18n #
########

__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

##############
# Decorators #
##############

def skip_for_lxc_guests(function):
    def wrapped():
        if config.get("lxc_guest") == "no":
            function()
    return wrapped

def plymouth_update_milestone(function):
    def wrapped():
        function()
        splash.update(function.__name__)
    return wrapped

#######################
# Convenience methods #
#######################

def wait_bus(unix_name, timeout=5, wait=0.1, stream=True):
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
            logger.debug("Waited %.2f sec for '%s'" % (itimeout-timeout, unix_name))
            return True
        except socket.error:
            timeout -= wait
        time.sleep(wait)

    logger.debug("Waited %.2f seconds for '%s'" % (itimeout-timeout, unix_name))
    return False

def load_file(path, ignore_comments=False):
    """Reads the contents of a file and returns it."""
    data = ""
    try:
        with open(path, "r") as _file:
            data = _file.read()
    except IOError:
        return ""
    if ignore_comments:
        data = filter(lambda x: not (x.startswith("#") or x == ""), data)
    return data

def load_config(path):
    """Reads key=value formatted config files and returns a dictionary."""
    data = {}
    for key, value in [_line.split("=", 1) for _line in
                       open(path, "r").readlines() if "=" in _line
                       and not _line.startswith("#")]:
        key = key.strip()
        value = value.strip()
        data[key] = value.strip("'").strip('"')
    return data

def write_to_file(filename, data=""):
    """Write data to file."""
    with open(filename, "w") as _file:
        _file.write(data)

def create_directory(path):
    """Create missing directories in the path."""
    if not os.path.exists(path):
        os.makedirs(path)

def mtime(filename):
    """Returns the last modification time of a file."""
    m_time = 0
    if os.path.exists(filename):
        m_time = os.path.getmtime(filename)
    return m_time

def mdirtime(dirname):
    """Returns the last modification date of a directory."""
    # Directory mdate is not updated for file updates, so we check each file
    # Note that we dont recurse into subdirs, modules.d, env.d etc are all flat
    mtime_dir = mtime(dirname)
    for _file in os.listdir(dirname):
        mtime_file = mtime(os.path.join(dirname, _file))
        if mtime_file > mtime_dir:
            mtime_dir = mtime_file
    return mtime_dir

def touch(filename):
    """Updates file modification date, create file if necessary"""
    try:
        if os.path.exists(filename):
            os.utime(filename, None)
        else:
            open(filename, "w").close()
    except IOError, error:
        if error.errno != 13:
            raise
        else:
            return False
    except OSError, error:
        if error.errno != 13:
            raise
        else:
            return False
    return True

def get_kernel_option(option):
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
                    key, value = arg.split(":", 1)
                    args[key] = value
                else:
                    args[arg] = ""
    return args

####################################
# Process spawning related methods #
####################################

def capture(*cmd):
    """Captures the output of a command without running a shell."""
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process.communicate()

def run_async(cmd, stdout=None, stderr=None):
    """Runs a command in background and redirects the outputs optionally."""
    fstdout = stdout if stdout else "/dev/null"
    fstderr = stderr if stderr else "/dev/null"
    return subprocess.Popen(cmd,
                            stdout=open(fstdout, "w"),
                            stderr=open(fstderr, "w")).pid

def run(*cmd):
    """Runs a command without running a shell, only output errors."""
    return subprocess.call(cmd, stdout=open("/dev/null", "w"))

def run_full(*cmd):
    """Runs a command without running a shell, with full output."""
    return subprocess.call(cmd)

def run_quiet(*cmd):
    """Runs a command without running a shell and no output."""
    _file = open("/dev/null", "w")
    return subprocess.call(cmd, stdout=_file, stderr=_file)

################
# Logger class #
################

class Logger:
    """Logger class for dumping into /var/log/mudur.log."""
    def __init__(self):
        self.lines = ["\n"]

    def log(self, msg):
        """Logs the given message."""
        stamp = time.strftime("%b %d %H:%M:%S")
        # Strip color characters
        msg = re.sub("(\033.*?m)", "", msg)
        self.lines.append("[%.3f] %s %s\n" % (time.time(), stamp, msg))

    def debug(self, msg):
        """Log the message if debug is enabled."""
        if config.get("debug"):
            self.log(msg)

    def flush(self):
        """Flushes the log buffer."""
        try:
            self.lines.append("\n")
            with open("/var/log/mudur.log", "a") as _file:
                _file.writelines(self.lines)
        except IOError:
            ui.error(_("Cannot write mudur.log, read-only file system"))

################
# Config class #
################

class Config:
    """Configuration class which parses /proc/cmdline to get mudur options."""
    def __init__(self):
        self.fstab = None

        # Parse kernel version
        vers = os.uname()[2].replace("_", ".").replace("-", ".")
        self.kernel = vers.split(".")

        # Default options for mudur= in /proc/cmdline
        self.options = {
            "language"      : "en",
            "clock"         : "local",
            "clock_adjust"  : "no",
            "tty_number"    : "6",
            "lxc_guest"     : "no",
            "keymap"        : None,
            "debug"         : True,
            "live"          : False,
            "safe"          : False,
            "forcefsck"     : False,
            "head_start"    : "",
            "services"      : "",
        }

        # Load config file if exists
        if os.path.exists("/etc/conf.d/mudur"):
            self.options.update(load_config("/etc/conf.d/mudur"))

        # File system check can be requested with a file
        self.options["forcefsck"] = os.path.exists("/forcefsck")

        # First try
        self.parse_kernel_options()

    def parse_kernel_options(self):
        """Parse mudur= from kernel boot parameters."""
        # We need to mount /proc before accessing kernel options
        # This function is called after that, and finish parsing options
        # We dont print any messages before, cause language is not known
        options = get_kernel_option("mudur")

        # Fill in the options
        self.options["live"] = options.has_key("thin") or \
                               os.path.exists("/var/run/pardus/livemedia")

        for k in [_k for _k in options.keys() if _k not in ("thin")]:
            self.options[k] = options[k] if options[k] else True

        # Normalize options

        # If language is unknown, default to English
        # Default language is Turkish, so this only used if someone
        # selected a language which isn't Turkish or English, and
        # in that case it is more likely they'll prefer English.
        lang = self.options["language"]
        if not languages.has_key(lang):
            print "Unknown language option '%s'" % lang
            lang = "en"
            self.options["language"] = lang

        # If no keymap is given, use the language's default
        if not self.options["keymap"]:
            self.options["keymap"] = languages[lang].keymap

    def get(self, key):
        """Custom dictionary getter method."""
        try:
            return self.options[key]
        except KeyError:
            print "Unknown option '%s' requested" % key
            time.sleep(3)

    def get_fstab_entry_with_mountpoint(self, mountpoint):
        """Returns /etc/fstab entry corresponding to the given mountpoint."""
        if not self.fstab:
            data = load_file("/etc/fstab", True).split("\n")
            self.fstab = map(lambda x: x.split(), data)

        for entry in self.fstab:
            if entry and len(entry) > 3 and entry[1] == mountpoint:
                return entry


##################
# Plymouth class #
##################

class Plymouth:
    """Plymouth class for visualizing init messages and plymouth splash."""

    def __init__(self):
        """Plymouth constructor."""
        self.client = "/bin/plymouth"
        self.daemon = "/sbin/plymouthd"
        self.available = config.get("lxc_guest") != "yes" \
                and os.path.exists(self.client)
        self.running = self.available and not run_quiet(self.client, "--ping")

    def send_cmd(self, *cmd):
        """Send the client a command to pass to the daemon."""
        if self.running:
            return run_quiet(self.client, *cmd)

    def start_daemon(self):
        if self.available:
            self.running = not run_quiet(self.daemon, "--mode=shutdown")

    def show_splash(self):
        self.send_cmd("show-splash")

    def hide_splash(self):
        self.send_cmd("hide-splash")

    def report_error(self):
        self.send_cmd("report-error")

    def update(self, milestone):
        self.send_cmd("update", "--status=%s" % milestone)

    def rootfs_is_now_rw(self):
        self.send_cmd("update-root-fs", "--read-write")

    def quit(self, retain_splash=False):
        self.send_cmd("quit", "--retain-splash" if retain_splash else "")

############
# UI class #
############

class UI:
    """User Interface class to settle the console and fonts."""

    UNICODE_MAGIC = "\x1b%G"

    # constants from linux/kd.h
    KDSKBMODE = 0x4B45
    K_UNICODE = 0x03

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
        """Dump release information, sets unicode mode."""
        print self.UNICODE_MAGIC
        if os.path.exists("/etc/pardus-release"):
            release = load_file("/etc/pardus-release").rstrip("\n")
            print "\x1b[1m  %s  \x1b[0;36mhttp://www.pardus.org.tr\x1b[0m" \
                    % release
        else:
            self.error(_("Cannot find /etc/pardus-release"))
        print

    def info(self, msg):
        """Print the given message and log if debug enabled."""
        if config.get("debug"):
            logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.colors['green'],
                         self.colors['normal'], msg.encode("utf-8")))

    def warn(self, msg):
        """Print the given message as a warning and log if debug enabled."""
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.colors['yellow'],
                         self.colors['normal'], msg.encode("utf-8")))

    def error(self, msg):
        """Print the given message as an error and log if debug enabled."""
        splash.report_error()
        logger.log(msg)
        sys.stdout.write(" %s*%s %s\n" % (self.colors['red'],
                         self.colors['normal'], msg.encode("utf-8")))

    def colorize(self, uicolor, msg):
        """Colorizes the given message."""
        return "%s%s%s" % (self.colors[uicolor], msg, self.colors['normal'])

##################
# Language class #
##################

class Language:
    """Dummy class to hold language informations."""

    def __init__(self, keymap, font, trans, locale):
        self.keymap = keymap
        self.font = font
        self.trans = trans
        self.locale = locale



########################################
# Language and console related methods #
########################################

languages = {
    "ca"    : Language("es",         "iso01.16",   "8859-1", "ca_ES.UTF-8"),
    "de"    : Language("de",         "iso01.16",   "8859-1", "de_DE.UTF-8"),
    #"el"    : Language("gr",         "iso07u-16",  "",       "el_GR.UTF-8"),
    "en"    : Language("us",         "iso01.16",   "8859-1", "en_US.UTF-8"),
    "es"    : Language("es",         "iso01.16",   "8859-1", "es_ES.UTF-8"),
    "fr"    : Language("fr",         "iso01.16",   "8859-1", "fr_FR.UTF-8"),
    "hu"    : Language("hu",         "lat2a-16",   "8859-2", "hu_HU.UTF-8"),
    "it"    : Language("it",         "iso01.16",   "8859-1", "it_IT.UTF-8"),
    "nl"    : Language("nl",         "iso01.16",   "8859-1", "nl_NL.UTF-8"),
    "pl"    : Language("pl",         "iso02.16",   "8859-2", "pl_PL.UTF-8"),
    "pt_BR" : Language("br-abnt2",   "iso01.16",   "8859-1", "pt_BR.UTF-8"),
    "ru"    : Language("ru",         "Cyr_a8x16",  "8859-5", "ru_RU.UTF-8"),
    "sv"    : Language("sv-latin1",  "lat0-16",    "8859-1", "sv_SE.UTF-8"),
    "tr"    : Language("trq",        "lat5u-16",   "8859-9", "tr_TR.UTF-8"),
}

def set_console_parameters():
    """Setups encoding, font and mapping for console."""
    lang = config.get("language")
    keymap = config.get("keymap")
    language = languages[lang]

    # Now actually set the values
    run("/usr/bin/kbd_mode", "-u")
    run_quiet("/bin/loadkeys", keymap)
    run("/usr/bin/setfont", "-f", language.font, "-m", language.trans)

def set_system_language():
    """Sets the system language."""
    lang = config.get("language")
    keymap = config.get("keymap")
    language = languages[lang]

    # Put them in /etc, so other programs like kdm can use them
    # without duplicating default->mudur.conf->kernel-option logic
    # we do here. Note that these are system-wide not per user,
    # and only for reading.
    create_directory("/etc/mudur")
    write_to_file("/etc/mudur/language", "%s\n" % lang)
    write_to_file("/etc/mudur/keymap", "%s\n" % keymap)
    write_to_file("/etc/mudur/locale", "%s\n" % language.locale)

    # Update environment if necessary
    content = "LANG=%s\nLC_ALL=%s\n" % (language.locale, language.locale)

    try:
        if content != load_file("/etc/env.d/03locale"):
            write_to_file("/etc/env.d/03locale", content)
    except IOError:
        ui.warn(_("/etc/env.d/03locale cannot be updated"))

def load_translations():
    """Loads the translation catalogue for mudur."""
    global __trans
    global _
    lang = config.get("language")
    __trans = gettext.translation('mudur', languages=[lang], fallback=True)
    _ = __trans.ugettext

def set_unicode_mode():
    """Makes TTYs unicode compatible."""
    import fcntl
    lang = config.get("language")
    language = languages[lang]

    for i in xrange(1, int(config.get("tty_number")) + 1):
        try:
            if os.path.exists("/dev/tty%s" % i):
                with open("/dev/tty%s" % i, "w") as _file:
                    fcntl.ioctl(_file, UI.KDSKBMODE, UI.K_UNICODE)
                    _file.write(UI.UNICODE_MAGIC)
                    run("/usr/bin/setfont", "-f",
                            language.font,  "-m",
                            language.trans, "-C", "/dev/tty%s" %i)
        except:
            ui.error(_("Could not set unicode mode on tty %d") % i)

######################################
# Service management related methods #
######################################

def fork_handler():
    """Callback which is passed to Popen as preexec_fn."""
    import termios
    import fcntl

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

def manage_service(service, command):
    """Starts/Stops the given service."""
    cmd = ["/bin/service", "--quiet", service, command]
    logger.debug("%s service %s.." % (command, service))
    subprocess.Popen(cmd, close_fds=True, preexec_fn=fork_handler,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug("%s service %s..done" % (command, service))
    splash.update(service)

def get_service_list(bus, _all=False):
    """Requests and returns the list of system services through COMAR."""
    obj = bus.get_object("tr.org.pardus.comar", "/", introspect=False)
    services = obj.listModelApplications("System.Service",
                                         dbus_interface="tr.org.pardus.comar")
    if _all:
        return services
    else:
        enabled = set(os.listdir("/etc/mudur/services/enabled"))
        conditional = set(os.listdir("/etc/mudur/services/conditional"))
        return enabled.union(conditional).intersection(set(services))

def start_services(extras=None):
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
                manage_service(service, "start")
            except dbus.DBusException:
                pass

    else:
        # Start network service first
        try:
            manage_service("NetworkManager", "start")
        except Exception, error:
            ui.error(_("Unable to start network:\n  %s") % error)

        # Almost everything depends on logger, so start manually
        manage_service("rsyslog", "start")
        if not wait_bus("/dev/log", stream=False, timeout=15):
            ui.warn(_("Cannot start system logger"))

        # Mount remote filesystems if any
        mount_remote_filesystems()

        if not config.get("safe"):
            ui.info(_("Starting services"))
            services = get_service_list(bus)

            # Remove already started services
            services = set(services).difference(["rsyslog", "NetworkManager"])

            # Give login screen a headstart
            head_start = config.get("head_start")
            run_head_start = head_start and head_start in services

            # Decide whether we'll stop plymouth or not
            stop_plymouth = "off" in get_kernel_option("xorg") or \
                            not run_head_start
            if run_head_start:
                manage_service(head_start, "ready")
                services.remove(head_start)

            # Run other services
            for service in services:
                manage_service(service, "ready")

            if stop_plymouth:
                # Stop plymouth
                splash.quit(retain_splash=False)

        # Close the handle
        bus.close()

@plymouth_update_milestone
def stop_services():
    """Sends stop signals to all available services through D-Bus."""
    import dbus

    ui.info(_("Stopping services"))
    try:
        bus = dbus.SystemBus()
    except dbus.DBusException:
        return

    for service in get_service_list(bus, _all=True):
        manage_service(service, "stop")

    # Close the handle
    bus.close()

def prune_needs_action_package_list():
    """Clears the lists to hold needsServiceRestart and needsReboot updates."""
    for f in ("/var/lib/pisi/info/needsrestart",
              "/var/lib/pisi/info/needsreboot"):
        if os.path.exists(f):
            os.unlink(f)


############################
# D-Bus start/stop methods #
############################

@plymouth_update_milestone
def start_dbus():
    """Starts the D-Bus service."""
    os.setuid(0)
    ui.info(_("Starting %s") % "DBus")
    if not os.path.exists("/var/lib/dbus/machine-id"):
        run("/usr/bin/dbus-uuidgen", "--ensure")
    run("/sbin/start-stop-daemon", "-b", "--start", "--quiet",
        "--pidfile", "/var/run/dbus/pid", "--exec", "/usr/bin/dbus-daemon",
        "--", "--system")
    wait_bus("/var/run/dbus/system_bus_socket")

@plymouth_update_milestone
def stop_dbus():
    """Stops the D-Bus service."""
    ui.info(_("Stopping %s") % "DBus")
    run("/sbin/start-stop-daemon", "--stop", "--quiet",
            "--pidfile", "/var/run/dbus/pid")

#############################
# UDEV management functions #
#############################

@skip_for_lxc_guests
@plymouth_update_milestone
def wait_for_udev_events():
    run("/sbin/udevadm", "settle", "--timeout=60")

@skip_for_lxc_guests
def trigger_failed_udev_events():
    # Trigger only the events which are failed during a previous run
    if os.path.exists("/dev/.udev/failed"):
        ui.info(_("Triggering udev events which are failed during a previous run"))
        run("/sbin/udevadm", "trigger", "--type=failed", "--action=add")

@skip_for_lxc_guests
def copy_udev_rules():
    """Copies persistent udev rules from /dev into /etc/udev/rules."""
    import glob
    import shutil

    # Copy udevtrigger log file to /var/log
    if os.path.exists("/dev/.udevmonitor.log"):
        try:
            shutil.move("/dev/.udevmonitor.log", "/var/log/udevmonitor.log")
        except IOError:
            # Can't move it, no problem.
            pass

    # Moves any persistent rules from /dev/.udev to /etc/udev/rules.d
    for rule in glob.glob("/dev/.udev/tmp-rules--*"):
        dest = "/etc/udev/rules.d/%s" % \
                os.path.basename(rule).split("tmp-rules--")[1]
        try:
            shutil.move(rule, dest)
        except IOError:
            ui.warn(_("Can't move persistent udev rules from /dev/.udev"))

@skip_for_lxc_guests
@plymouth_update_milestone
def start_udev():
    """Prepares the startup of udev daemon and starts it."""

    # When these files are missing, lots of trouble happens
    # so we double check their existence
    create_directory("/dev/shm")

    # Start udev daemon
    ui.info(_("Starting udev"))

    run("/sbin/start-stop-daemon",
        "--start", "--quiet",
        "--exec", "/sbin/udevd", "--", "--daemon")

    # Create needed queue directory
    create_directory("/dev/.udev/queue/")

    # Log things that trigger does
    pid = run_async(["/sbin/udevadm", "monitor", "--env"],
                    stdout="/dev/.udevmonitor.log")

    # Filling up /dev by triggering uevents
    ui.info(_("Populating /dev"))

    # Trigger events for all devices
    run("/sbin/udevadm", "trigger", "--type=subsystems", "--action=add")
    run("/sbin/udevadm", "trigger", "--type=devices", "--action=add")

    # Stop udevmonitor
    os.kill(pid, 15)

@skip_for_lxc_guests
@plymouth_update_milestone
def stop_udev():
    """Stops udev daemon."""
    run("/sbin/start-stop-daemon",
        "--stop", "--exec", "/sbin/udevd")


##############################
# Filesystem related methods #
##############################

def update_mtab_for_root():
    """Calls mount -f to update mtab for a previous mount."""
    mount_failed_lock = 16
    if os.path.exists("/etc/mtab~"):
        try:
            ui.warn(_("Removing stale lock file /etc/mtab~"))
            os.unlink("/etc/mtab~")
        except OSError:
            ui.warn(_("Failed removing stale lock file /etc/mtab~"))

    return (run_quiet("/bin/mount", "-f", "/") != mount_failed_lock)

@skip_for_lxc_guests
@plymouth_update_milestone
def check_root_filesystem():
    """Checks root filesystem with fsck if required."""
    if not config.get("live"):

        entry = config.get_fstab_entry_with_mountpoint("/")
        if not entry:
            ui.warn(_("/etc/fstab doesn't contain an entry "
                "for the root filesystem"))
            return

        if config.get("forcefsck") or (len(entry) > 5 and entry[5] != "0"):

            # Remount root filesystem ro for fsck without writing to mtab (-n)
            ui.info(_("Remounting root filesystem read-only"))
            run_quiet("/bin/mount", "-n", "-o", "remount,ro", "/")

            # FIXME: Test with plymouth
            if config.get("forcefsck"):
                splash.hide_splash()
                ui.info(_("Checking root filesystem (full check forced)"))
                # -y: Fix whatever the error is without user's intervention
                ret = run_full("/sbin/fsck", "-C", "-y", "-f", "/")
                # /forcefsck isn't deleted because check_filesystems needs it.
                # it'll be deleted in that function.
            else:
                ui.info(_("Checking root filesystem"))
                ret = run_full("/sbin/fsck", "-C", "-T", "-a", "/")
            if ret == 0:
                # No errors,just go on
                pass
            elif ret == 2 or ret == 3:
                # Actually 2 means that a reboot is required, fsck man page
                # doesn't mention about 3 but let's leave it as it's harmless.
                splash.hide_splash()
                ui.warn(_("Filesystem repaired, but reboot needed!"))
                for i in xrange(4):
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

@skip_for_lxc_guests
@plymouth_update_milestone
def mount_root_filesystem():
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
        write_to_file("/etc/mtab")
    except IOError:
        ui.warn(_("Couldn't synchronize /etc/mtab from /proc/mounts"))

    # This will actually try to update mtab for /. If it fails because
    # of a stale lock file, it will clear it and return.
    update_mtab_for_root()

    # Update mtab
    for entry in load_file("/proc/mounts").split("\n"):
        try:
            devpath = entry.split()[1]
        except IndexError:
            continue
        if config.get_fstab_entry_with_mountpoint(devpath):
            run("/bin/mount", "-f", "-o", "remount", devpath)

@skip_for_lxc_guests
@plymouth_update_milestone
def check_filesystems():
    """Checks all the filesystems with fsck if required."""
    if not config.get("live"):
        ui.info(_("Checking all filesystems"))

        if config.get("forcefsck"):
            splash.hide_splash()
            ui.info(_("A full fsck has been forced"))
            # -C: Display completion bars
            # -R: Skip the root file system
            # -A: Check all filesystems found in /etc/fstab
            # -a: Automatically repair without any questions
            # -f: Force checking even it's clean (e2fsck)
            ret = run_full("/sbin/fsck", "-C", "-R", "-A", "-a", "-f")

            # remove forcefsck file if it exists
            if os.path.exists("/forcefsck"):
                os.unlink("/forcefsck")
        else:
            # -T: Don't show the title on startup
            ret = run_full("/sbin/fsck", "-C", "-T", "-R", "-A", "-a")

        if ret == 0:
            pass
        elif ret >= 2 and ret <= 3:
            ui.warn(_("Filesystem errors corrected"))
        else:
            ui.error(_("Fsck could not correct all errors, manual repair needed"))
            run_full("/sbin/sulogin")

@skip_for_lxc_guests
@plymouth_update_milestone
def mount_local_filesystems():
    """Mounts local filesystems."""

    ui.info(_("Mounting local filesystems"))
    run("/bin/mount", "-at", "noproc,nocifs,nonfs,nonfs4,noncpfs")

def mount_remote_filesystems():
    """Mounts remote filesystems."""
    from pardus.fstabutils import Fstab
    fstab = Fstab()
    if fstab.contains_remote_mounts():
        ui.info(_("Mounting remote filesystems"))
        manage_service("netfs", "start")

################################################################################
# Other system related methods for hostname setting, modules autoloading, etc. #
################################################################################

@skip_for_lxc_guests
def run_sysctl():
    run("/sbin/sysctl", "-q", "-p", "/etc/sysctl.conf")

def set_hostname():
    """Sets the system's hostname."""
    khost = capture("/bin/hostname")[0].rstrip("\n")
    uhost = None
    if os.path.exists("/etc/env.d/01hostname"):
        data = load_file("/etc/env.d/01hostname")
        i = data.find('HOSTNAME="')
        if i != -1:
            j = data.find('"', i+10)
            if j != -1:
                uhost = data[i+10:j]
        """
        try:
            data = load_file("/etc/env.d/01hostname").strip().split("HOSTNAME=")[1].strip("\"")
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
        write_to_file("/etc/env.d/01hostname", data)

    ui.info(_("Setting up hostname as '%s'") % ui.colorize("light", host))
    run("/bin/hostname", host)

@skip_for_lxc_guests
@plymouth_update_milestone
def autoload_modules():
    """Traverses /etc/modules.autoload.d to autoload kernel modules if any."""
    if os.path.exists("/proc/modules"):
        import glob
        for _file in glob.glob("/etc/modules.autoload.d/kernel-%s*" \
                % config.kernel[0]):
            data = load_file(_file, True).split("\n")
            for module in data:
                run("/sbin/modprobe", "-q", "-b", module)

@skip_for_lxc_guests
def set_disk_parameters():
    """Sets disk parameters if hdparm is available."""
    if config.get("safe") or not os.path.exists("/etc/conf.d/hdparm"):
        return

    conf = load_config("/etc/conf.d/hdparm")
    if len(conf) > 0:
        ui.info(_("Setting disk parameters"))
        if conf.has_key("all"):
            for name in os.listdir("/sys/block/"):
                if name.startswith("hd") and \
                        len(name) == 3 and not conf.has_key(name):
                    run_quiet("/sbin/hdparm", "%s" % conf["all"].split(),
                            "/dev/%s" % name)
        for key, value in conf:
            if key != "all":
                # FIXME: There's a bug here!
                run_quiet("/sbin/hdparm", "%s" % value.split(), "/dev/%s" % name)


################
# Swap methods #
################

@skip_for_lxc_guests
@plymouth_update_milestone
def enable_swap():
    """Calls swapon for all swaps in /etc/fstab."""
    ui.info(_("Activating swap space"))
    run("/sbin/swapon", "-a")

@skip_for_lxc_guests
@plymouth_update_milestone
def disable_swap():
    """Calls swapoff after unmounting tmpfs."""
    # unmount unused tmpfs filesystems before swap
    # (tmpfs can be swapped and you can get a deadlock)
    run_quiet("/bin/umount", "-at", "tmpfs")

    ui.info(_("Deactivating swap space"))
    run_quiet("/sbin/swapoff", "-a")


##############################
# Filesystem cleanup methods #
##############################

def cleanup_var():
    """Cleans up /var upon boot."""
    ui.info(_("Cleaning up /var"))
    blacklist = ["utmp", "random-seed", "livemedia"]
    for root, dirs, files in os.walk("/var/run"):
        for _file in files:
            if _file not in blacklist:
                try:
                    os.unlink(os.path.join(root, _file))
                except OSError:
                    pass

    # Prune needsrestart and needsreboot files if any
    prune_needs_action_package_list()

@plymouth_update_milestone
def cleanup_tmp():
    """Cleans up /tmp upon boot."""
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

    create_directory("/tmp/.ICE-unix")
    os.chown("/tmp/.ICE-unix", 0, 0)
    os.chmod("/tmp/.ICE-unix", 01777)

    create_directory("/tmp/.X11-unix")
    os.chown("/tmp/.X11-unix", 0, 0)
    os.chmod("/tmp/.X11-unix", 01777)

########################################
# System time/Clock management methods #
########################################

@skip_for_lxc_guests
@plymouth_update_milestone
def set_clock():
    """Sets the system time according to /etc."""
    ui.info(_("Setting system clock to hardware clock"))

    # Default is UTC
    options = "--utc"
    if config.get("clock") != "UTC":
        options = "--localtime"

    # Default is no
    if config.get("clock_adjust") == "yes":
        adj = "--adjust"
        if not touch("/etc/adjtime"):
            adj = "--noadjfile"
        elif os.stat("/etc/adjtime").st_size == 0:
            write_to_file("/etc/adjtime", "0.0 0 0.0\n")
        ret = capture("/sbin/hwclock", adj, options)
        if ret[1] != '':
            ui.error(_("Failed to adjust systematic drift of the hardware clock"))

    ret = capture("/sbin/hwclock", "--hctosys", options)
    if ret[1] != '':
        ui.error(_("Failed to set system clock to hardware clock"))

@skip_for_lxc_guests
@plymouth_update_milestone
def save_clock():
    """Saves the system time for further boots."""
    if not config.get("live"):
        options = "--utc"
        if config.get("clock") != "UTC":
            options = "--localtime"

        ui.info(_("Syncing system clock to hardware clock"))
        ret = capture("/sbin/hwclock", "--systohc", options)
        if ret[1] != '':
            ui.error(_("Failed to synchronize clocks"))

def stop_system():
    """Stops the system."""
    import shutil

    def get_fs_entry():
        ents = load_file("/proc/mounts").split("\n")
        ents = map(lambda x: x.split(), ents)
        ents = filter(lambda x: len(x) > 2, ents)
        # not the virtual systems
        vfs = ["proc", "devpts", "sysfs", "devfs", "devtmpfs", "squashfs", "tmpfs", "usbfs", "usbdevfs"]
        ents = filter(lambda x: not x[2] in vfs, ents)
        ents = filter(lambda x: x[0] != "none", ents)
        # not the root stuff
        ents = filter(lambda x: not (x[0] == "rootfs" or x[0] == "/dev/root"), ents)
        ents = filter(lambda x: x[1] != "/", ents)
        # sort for correct unmount order
        ents.sort(key=lambda x: x[1], reverse=True)
        return ents

    def remount_ro(force=False):
        ents = load_file("/proc/mounts").split("\n")
        ents = map(lambda x: x.split(), ents)
        ents = filter(lambda x: len(x) > 2, ents)
        ents = filter(lambda x: x[0] != "none", ents)
        ents.sort(key=lambda x: x[1], reverse=True)

        if ents:
            run("/bin/sync")
            run("/bin/sync")
            time.sleep(1)

        splash.update("remount_ro")
        splash.quit(retain_splash=True)
        ret = 0
        for ent in ents:
            if force:
                ret += run_quiet("/bin/umount", "-n", "-r", ent[1])
            else:
                ret += run_quiet("/bin/mount", "-n", "-o", "remount,ro", ent[1])
        if ret:
            run_quiet("killall5", "-9")
        return ret

    # Stopping system
    stop_services()
    stop_dbus()
    stop_udev()
    save_clock()
    disable_swap()

    # write a reboot record to /var/log/wtmp before unmounting
    run("/sbin/halt", "-w")

    if config.get("lxc_guest") != "yes":
        splash.update("unmount_filesystems")
        ui.info(_("Unmounting filesystems"))
        for dev in get_fs_entry():
            if run_quiet("/bin/umount", dev[1]) != 0:
                # kill processes still using this mount
                run_quiet("/bin/fuser", "-k", "-9", "-m", dev[1])
                time.sleep(2)
                run_quiet("/bin/umount", "-f", "-r", dev[1])

        ui.info(_("Remounting remaining filesystems read-only"))

        # We parse /proc/mounts but use umount, so this have to agree
        shutil.copy("/proc/mounts", "/etc/mtab")
        if remount_ro():
            if remount_ro():
                remount_ro(True)

##################
# Exception hook #
##################

def except_hook(e_type, e_value, e_trace):
    import traceback
    print
    print _("An internal error occured. Please report to the bugs.pardus.org.tr"
            "with following information:").encode("utf-8")
    print
    print e_type, e_value
    traceback.print_tb(e_trace)
    print
    run_full("/sbin/sulogin")


##################
# Global objects #
##################

config = Config()
logger = Logger()
splash = Plymouth()
ui = UI()


def main():

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    sys.excepthook = except_hook
    os.umask(022)

    # Setup path just in case
    os.environ["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:" + os.environ["PATH"]

    # We can log the event with uptime information now
    logger.log("/sbin/mudur.py %s" % sys.argv[1])

    # Activate i18n, we can print localized messages from now on
    load_translations()


    ### SYSINIT ###
    if sys.argv[1] == "sysinit":

        # This is who we are...
        ui.greet()

        # Now we know which language and keymap to use
        set_console_parameters()

        # Start udev and event triggering
        start_udev()

        # Check root file system
        check_root_filesystem()

        # Mount root file system
        mount_root_filesystem()
        splash.rootfs_is_now_rw()

        # Grab persistent rules and udev.log file from /dev
        copy_udev_rules()

        # Set hostname
        set_hostname()

        # Load modules manually written in /etc/modules.autoload.d/kernel-x.y
        autoload_modules()

        # Check all filesystems
        check_filesystems()

        # Mount local filesystems
        mount_local_filesystems()

        # Activate swap space
        enable_swap()

        # Set disk parameters using hdparm
        set_disk_parameters()

        # Set the clock
        set_clock()

        # Set the system language
        set_system_language()

        # Call udev settle
        wait_for_udev_events()

        # When we exit this runlevel, init will write a boot record to utmp
        write_to_file("/var/run/utmp")
        touch("/var/log/wtmp")

        run("/bin/chgrp", "utmp", "/var/run/utmp", "/var/log/wtmp")

        os.chmod("/var/run/utmp", 0664)
        os.chmod("/var/log/wtmp", 0664)

    ### BOOT ###
    elif sys.argv[1] == "boot":
        splash.update("boot_runlevel")

        ui.info(_("Setting up localhost"))
        run("/sbin/ifconfig", "lo", "127.0.0.1", "up")
        run("/sbin/route", "add", "-net", "127.0.0.0",
            "netmask", "255.0.0.0", "gw", "127.0.0.1", "dev", "lo")

        run_sysctl()

        # Cleanup /var
        cleanup_var()

        # Update environment variables according to the modification
        # time of the relevant files
        if mdirtime("/etc/env.d") > mtime("/etc/profile.env"):
            ui.info(_("Updating environment variables"))
            run("/sbin/update-environment")

        # Cleanup /tmp
        cleanup_tmp()

        # Start DBUS
        start_dbus()

        # Set unicode properties for ttys
        set_unicode_mode()

    ### DEFAULT ###
    elif sys.argv[1] == "default":
        splash.update("default_runlevel")

        trigger_failed_udev_events()

        # Source local.start
        if not config.get("safe") and os.path.exists("/etc/conf.d/local.start"):
            run("/bin/bash", "/etc/conf.d/local.start")

        # Start services
        start_services()

    ### SINGLE ###
    elif sys.argv[1] == "single":
        stop_services()

    ### REBOOT/SHUTDOWN ###
    elif sys.argv[1] == "reboot" or sys.argv[1] == "shutdown":
        splash.start_daemon()
        splash.rootfs_is_now_rw()
        splash.show_splash()

        # Log the operation before unmounting file systems
        logger.flush()

        # Source local.stop
        if not config.get("safe") and os.path.exists("/etc/conf.d/local.stop"):
            run("/bin/bash", "/etc/conf.d/local.stop")

        # Stop the system
        stop_system()

        if sys.argv[1] == "reboot":

            # Try to reboot using kexec, if kernel supports it.
            kexec_file = "/sys/kernel/kexec_loaded"

            if os.path.exists(kexec_file) \
                    and int(open(kexec_file, "r").read().strip()):
                ui.info(_("Trying to initiate a warm reboot "
                    "(skipping BIOS with kexec kernel)"))
                run_quiet("/usr/sbin/kexec", "-e")

            # Shut down all network interfaces just before halt or reboot,
            # When halting the system do a poweroff. This is the default
            # when halt is called as powerof. Don't write the wtmp record.
            run("/sbin/reboot", "-idp")

            # Force halt or reboot, don't call shutdown
            run("/sbin/reboot", "-f")

        else:
            run("/sbin/halt", "-ihdp")
            run("/sbin/halt", "-f")

        # Control never reaches here

    try:
        logger.flush()
    except IOError:
        pass

############################
# Main program starts here #
############################
if __name__ == "__main__":
    if get_kernel_option("mudur").has_key("profile"):
        import cProfile
        cProfile.run("main()", "/dev/.mudur-%s.log" % sys.argv[1])
    else:
        main()

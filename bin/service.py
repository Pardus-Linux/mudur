#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Service management tool
# Copyright (C) 2006-2011 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import os
import sys
import time
import comar
import dbus
import socket
import locale
import subprocess

# i18n

import gettext
__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

# Utilities

def loadConfig(path):
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

def waitBus(unix_name, timeout=10, wait=0.1, stream=True):
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

# Operations

class Service:
    types = {
        "local": _("local"),
        "script": _("script"),
        "server": _("server"),
    }

    def __init__(self, name, info=None):
        self.name = name
        self.running = ""
        self.autostart = ""
        if info:
            servicetype, self.description, state = info
            self.state = state
            self.servicetype = self.types[servicetype]
            if state in ("on", "started", "conditional_started"):
                self.running = _("running")
            if state in ("on", "stopped"):
                self.autostart = _("yes")
            if state in ("conditional_started", "conditional_stopped"):
                self.autostart = _("conditional")


def format_service_list(services, use_color=True):
    if os.environ.get("TERM", "") == "xterm":
        colors = {
            "on": '[0;32m',
            "started": '[1;32m',
            "stopped": '[0;31m',
            "off": '[0m',
            "conditional_started": '[1;32m',
            "conditional_stopped": '[1;33m',
        }
    else:
        colors = {
            "on": '[1;32m',
            "started": '[0;32m',
            "stopped": '[1;31m',
            "off": '[0m',
            "conditional_started": '[0;32m',
            "conditional_stopped": '[0;33m',
        }

    run_title  = _("Status")
    name_title = _("Service")
    auto_title = _("Autostart")
    desc_title = _("Description")

    run_size  = max(max(map(lambda x: len(x.running), services)), len(run_title))
    name_size = max(max(map(lambda x: len(x.name), services)), len(name_title))
    auto_size = max(max(map(lambda x: len(x.autostart), services)), len(auto_title))
    desc_size = len(desc_title)

    line = "%s | %s | %s | %s" % (
        name_title.center(name_size),
        run_title.center(run_size),
        auto_title.center(auto_size),
        desc_title.center(desc_size)
    )
    print line
    print "-" * (len(line))

    cstart = ""
    cend = ""
    if use_color:
        cend = "\x1b[0m"
    for service in services:
        if use_color:
            cstart = "\x1b%s" % colors[service.state]
        line = "%s%s%s | %s%s%s | %s%s%s | %s%s%s" % (
            cstart,
            service.name.ljust(name_size),
            cend, cstart,
            service.running.center(run_size),
            cend, cstart,
            service.autostart.center(auto_size),
            cend, cstart,
            service.description,
            cend
        )
        print line

def readyService(service):
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].ready()
    except dbus.DBusException, e:
        print _("Unable to start %s:") % service
        print "  %s" % e.args[0]

def startService(service, quiet=False):
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].start()
    except dbus.DBusException, e:
        print _("Unable to start %s:") % service
        print "  %s" % e.args[0]
        return
    if not quiet:
        print _("Starting %s") % service

def stopService(service, quiet=False):
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].stop()
    except dbus.DBusException, e:
        print _("Unable to stop %s:") % service
        print "  %s" % e.args[0]
        return
    if not quiet:
        print _("Stopping %s") % service

def setServiceState(service, state, quiet=False):
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].setState(state)
    except dbus.DBusException, e:
        print _("Unable to set %s state:") % service
        print "  %s" % e.args[0]
        return
    if not quiet:
        if state == "on":
            print _("Service '%s' will be auto started.") % service
        elif state == "off":
            print _("Service '%s' won't be auto started.") % service
        else:
            print _("Service '%s' will be started if required.") % service

def reloadService(service, quiet=False):
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].reload()
    except dbus.DBusException, e:
        print _("Unable to reload %s:") % service
        print "  %s" % e.args[0]
        return
    if not quiet:
        print _("Reloading %s") % service

def getServiceInfo(service):
    link = comar.Link()
    link.setLocale()
    link.useAgent(False)
    return link.System.Service[service].info()

def getServices():
    link = comar.Link()
    link.setLocale()
    link.useAgent(False)
    return list(link.System.Service)

def list_services(use_color=True):
    services = []
    for service in getServices():
        services.append((service, getServiceInfo(service), ))

    if len(services) > 0:
        services.sort(key=lambda x: x[0])
        lala = []
        for service, info in services:
            lala.append(Service(service, info))
        format_service_list(lala, use_color)

def manage_service(service, op, use_color=True, quiet=False):
    if op == "ready":
        readyService(service)
    elif op == "start":
        startService(service, quiet)
    elif op == "stop":
        stopService(service, quiet)
    elif op == "reload":
        reloadService(service, quiet)
    elif op == "on":
        setServiceState(service, "on", quiet)
    elif op == "off":
        setServiceState(service, "off", quiet)
    elif op == "conditional":
        setServiceState(service, "conditional", quiet)
    elif op in ["info", "status", "list"]:
        info = getServiceInfo(service)
        s = Service(service, info)
        format_service_list([s], use_color)
    elif op == "restart":
        manage_service(service, "stop", use_color, quiet)
        manage_service(service, "start", use_color, quiet)

def run(*cmd):
    subprocess.call(cmd)

def manage_dbus(op, use_color, quiet):
    if os.getuid() != 0 and op not in ["status", "info", "list"]:
        print _("You must be root to use that.")
        return -1

    def cleanup():
        try:
            os.unlink("/var/run/dbus/pid")
            os.unlink("/var/run/dbus/system_bus_socket")
        except OSError:
            pass
    if op == "start":
        if not quiet:
            print _("Starting %s") % "DBus"
        cleanup()
        if not os.path.exists("/var/lib/dbus/machine-id"):
            run("/usr/bin/dbus-uuidgen", "--ensure")
        run("/sbin/start-stop-daemon", "-b", "--start", "--quiet",
            "--pidfile", "/var/run/dbus/pid", "--exec", "/usr/bin/dbus-daemon",
            "--", "--system")
        if not waitBus("/var/run/dbus/system_bus_socket", timeout=20):
            print _("Unable to start DBus")
            return -1
    elif op == "stop":
        if not quiet:
            print _("Stopping %s") % "DBus"
        run("/sbin/start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/dbus/pid")
        cleanup()
    elif op == "restart":
        manage_dbus("stop", use_color, quiet)
        manage_dbus("start", use_color, quiet)
    elif op in ["info", "status", "list"]:
        try:
            dbus.SystemBus()
        except dbus.DBusException:
            print _("DBus is not running.")
            return
        print _("DBus is running.")

# Usage

def usage():
    print _("""usage: service [<options>] [<service>] <command>
where command is:
 list     Display service list
 status   Display service status
 info     Display service status
 on       Auto start the service
 off      Don't auto start the service
 start    Start the service
 stop     Stop the service
 restart  Stop the service, then start again
 reload   Reload the configuration (if service supports this)
and option is:
 -N, --no-color  Don't use color in output
 -q, --quiet     Don't print replies""")

# Main

def main(args):
    operations = ("start", "stop", "info", "list", "restart", "reload", "status", "on", "off", "ready", "conditional")
    use_color = True
    quiet = False

    # Parameters
    if "--no-color" in args:
        args.remove("--no-color")
        use_color = False
    if "-N" in args:
        args.remove("-N")
        use_color = False
    if "--quiet" in args:
        args.remove("--quiet")
        quiet = True
    if "-q" in args:
        args.remove("-q")
        quiet = True

    # Operations
    if args == []:
        list_services(use_color)

    elif args[0] == "list" and len(args) == 1:
        list_services(use_color)

    elif args[0] == "help":
        usage()

    elif len(args) < 2:
        usage()

    elif args[1] in operations and args[0] == "dbus":
        manage_dbus(args[1], use_color, quiet)
    elif args[1] in operations:
        try:
            manage_service(args[0].replace("-", "_"), args[1], use_color, quiet)
        except dbus.DBusException, e:
            if "Unable to find" in str(e):
                print _("No such service: %s") % args[0]
            else:
                print "  %s" % e.args[0]
                return -1
        except ValueError, e:
            print e
            return -1
    else:
        usage()

    return 0

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, '')
    main(sys.argv[1:])

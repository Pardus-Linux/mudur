#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2006, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import sys
import os
import locale
import comar
import time

# i18n

import gettext
__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

# Utilities

def languageCode():
    lang = locale.setlocale(locale.LC_MESSAGES)
    if "_" in lang:
        return lang.split("_")[0]
    return "en"

def comlink():
    com = comar.Link()
    com.localize(languageCode())
    return com

def collect(c):
    reply = c.read_cmd()
    if reply[0] == c.RESULT_START:
        replies = []
        while True:
            reply = c.read_cmd()
            if reply[0] == c.RESULT_END:
                return replies
            replies.append(reply)
    else:
        return [reply]

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
            type, state, self.description = info.split("\n")
            self.state = state
            self.type = self.types[type]
            if state in ("on", "started"):
                self.running = _("running")
            if state in ("on", "stopped"):
                self.autostart = _("yes")


def format_service_list(services):
    if os.environ.get("TERM", "") == "xterm":
        colors = {
            "on": '[0;32m',
            "started": '[1;32m',
            "stopped": '[0;31m',
            "off": '[0m'
        }
    else:
        colors = {
            "on": '[1;32m',
            "started": '[0;32m',
            "stopped": '[1;31m',
            "off": '[0m'
        }
    name_title = _("Service")
    run_title = _("Status")
    auto_title = _("Autostart")
    desc_title = _("Description")
    
    name_size = max(max(map(lambda x: len(x.name), services)), len(name_title)) + 1
    run_size = max(max(map(lambda x: len(x.running), services)), len(run_title)) + 1
    auto_size = max(max(map(lambda x: len(x.autostart), services)), len(auto_title)) + 1
    desc_size = len(desc_title)
    
    print "", \
        name_title.ljust(name_size), \
        run_title.ljust(run_size), \
        auto_title.ljust(auto_size), \
        desc_title
    print "-" * (name_size + run_size + auto_size + desc_size + 4)
    
    for service in services:
        print "\x1b%s" % colors[service.state], \
            service.name.ljust(name_size), \
            service.running.center(run_size), \
            service.autostart.center(auto_size), \
            service.description, \
            '\x1b[0m'

def list():
    c = comlink()
    c.call("System.Service.info")
    data = collect(c)
    services = filter(lambda x: x[0] == c.RESULT, data)
    errors = filter(lambda x: x[0] != c.RESULT, data)
    
    services.sort(key=lambda x: x[3])
    lala = []
    for item in services:
        lala.append(Service(item[3], item[2]))
    
    format_service_list(lala)

def checkDaemon(pidfile):
    if not os.path.exists(pidfile):
        return False
    pid = file(pidfile).read().rstrip("\n")
    if not os.path.exists("/proc/%s" % pid):
        return False
    return True

def manage_comar(op):
    if os.getuid() != 0:
        print _("You should be the root user in order to control the comar service.")
        sys.exit(1)
    
    comar_pid = "/var/run/comar.pid"
    
    if op == "stop" or op == "restart":
        os.system("/sbin/start-stop-daemon --stop --pidfile %s" % comar_pid)
    
    timeout = 5
    while checkDaemon(comar_pid) and timeout > 0:
        time.sleep(0.2)
        timeout -= 0.2
    
    if op == "start" or op == "restart":
        os.system("/sbin/start-stop-daemon -b --start --pidfile %s --make-pidfile --exec /usr/bin/comar" % comar_pid)

def manage_service(service, op):
    c = comlink()
    
    if op == "start":
        c.call_package("System.Service.start", service)
    elif op == "stop":
        c.call_package("System.Service.stop", service)
    elif op == "reload":
        c.call_package("System.Service.reload", service)
    elif op == "on":
        c.call_package("System.Service.setState", service, ["state", "on"])
    elif op == "off":
        c.call_package("System.Service.setState", service, ["state", "off"])
    elif op == "info":
        c.call_package("System.Service.info", service)
    elif op == "restart":
        manage_service(service, "stop")
        manage_service(service, "start")
        return
    
    reply = c.read_cmd()
    if reply[0] != c.RESULT:
        print _("Error: %s" % reply[2])
        return
    
    if op == "start":
        print _("Service '%s' started.") % service
    elif op == "stop":
        print _("Service '%s' stopped.") % service
    elif op == "info":
        s = Service(reply[3], reply[2])
        format_service_list([s])
    elif op == "reload":
        print _("Service '%s' reloaded.") % service
    elif op == "on":
        print _("Service '%s' will be auto started.") % service
    elif op == "off":
        print _("Service '%s' won't be auto started.") % service

# Usage

def usage():
    print _("""usage: service [<service>] <command>
where command is:
 list    Display service list
 info    Display service status
 on      Auto start the service
 off     Don't auto start the service
 start   Start the service
 stop    Stop the service
 restart Stop the service, then start again
 reload  Reload the configuration (if service supports this)""")

# Main

def main(args):
    operations = ("start", "stop", "info", "restart", "reload", "on", "off")
    
    if args == []:
        list()
    
    elif args[0] == "list":
        list()
    
    elif args[0] == "help":
        usage()
    
    elif len(args) < 2:
        usage()
    
    elif args[0] == "comar":
        manage_comar(args[1])
    
    elif args[1] in operations:
        manage_service(args[0], args[1])
    
    else:
        usage()

#

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, '')
    main(sys.argv[1:])

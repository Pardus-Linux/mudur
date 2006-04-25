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

# i18n

import gettext
__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

# Utilities

def comlink():
    return comar.Link()

def collect(c):
    reply = c.read_cmd()
    if reply[0] == c.RESULT_START:
        replies = []
        while True:
            reply = c.read_cmd()
            if reply[0] == c.RESULT_END:
                return replies
            if reply[0] == c.RESULT:
                replies.append(reply)
    else:
        return [reply]

# Operations

def list():
    def onoff(state):
        if state in ("on", "stopped"):
            return "on"
        if state in ("off", "started"):
            return "off"
    def color(state):
        if os.environ.has_key("TERM") and os.environ["TERM"] == "xterm":
            colors = {"on": '[0;32m',
                      "started": '[1;32m',
                      "stopped": '[0;31m',
                      "off": '[0m'}
        else:
            colors = {"on": '[1;32m',
                      "started": '[0;32m',
                      "stopped": '[1;31m',
                      "off": '[0m'}

        return "\x1b%s" % colors[state]
    c = comlink()
    c.call("System.Service.info")
    data = collect(c)
    services = filter(lambda x: x[0] == c.RESULT, data)
    errors = filter(lambda x: x[0] != c.RESULT, data)
    
    size = max(map(lambda x: len(x[3]), services))
    
    services.sort(key=lambda x: x[3])
    for item in services:
        info = item[2].split("\n")
        print color(info[1]), item[3].ljust(size), info[0].ljust(6), onoff(info[1]).ljust(3), info[2], '\x1b[0m'

def manage_comar(op):
    if os.getuid() != 0:
        print _("You should be the root user in order to control the comar service.")
        sys.exit(1)
    
    if op == "stop" or op == "restart":
        os.system("/sbin/start-stop-daemon --stop --pidfile /var/run/comar.pid")
    
    if op == "start" or op == "restart":
        os.system("/sbin/start-stop-daemon -b --start --pidfile /var/run/comar.pid --make-pidfile --exec /usr/bin/comar")

def start(service):
    c = comlink()
    c.call_package("System.Service.start", service)
    reply = c.read_cmd()
    if reply[0] == c.RESULT:
        print _("Service '%s' started.") % service
    else:
        print _("Error: %s") % reply[2]

def stop(service):
    c = comlink()
    c.call_package("System.Service.stop", service)
    reply = c.read_cmd()
    if reply[0] == c.RESULT:
        print _("Service '%s' stopped.") % service
    else:
        print _("Error: %s") % reply[2]

def restart(service):
    stop(service)
    start(service)

def reload(service):
    c = comlink()
    c.call_package("System.Service.reload", service)
    reply = c.read_cmd()
    if reply[0] == c.RESULT:
        print _("Service '%s' reloaded.") % service
    else:
        print _("Error: %s") % reply[2]

def on(service):
    c = comlink()
    c.call_package("System.Service.setState", service, ["state", "on"])
    reply = c.read_cmd()
    if reply[0] == c.RESULT:
        print _("Service '%s' turned on.") % service
    else:
        print _("Error: %s") % reply[2]

def off(service):
    c = comlink()
    c.call_package("System.Service.setState", service, ["state", "off"])
    reply = c.read_cmd()
    if reply[0] == c.RESULT:
        print _("Service '%s' turned off.") % service
    else:
        print _("Error: %s") % reply[2]

# Usage

def usage():
    print _("""usage: service [<service>] <command>
where command is:
 list    Display service list
 on      Turn on the service permamently
 off     Turn off the service permamently
 start   Start the service
 stop    Stop the service
 restart Stop the service, then start again
 reload  Reload the configuration (if service supports this)""")

# Main

def main(args):
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
    
    elif args[1] == "start":
        start(args[0])
    
    elif args[1] == "stop":
        stop(args[0])
    
    elif args[1] == "restart":
        restart(args[0])
    
    elif args[1] == "reload":
        reload(args[0])
    
    elif args[1] == "on":
        on(args[0])
    
    elif args[1] == "off":
        off(args[0])
    
    else:
        usage()

#

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, '')
    main(sys.argv[1:])

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, TUBITAK/UEKAE
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

#

def collect(c):
    reply = c.read_cmd()
    if reply.command == "start":
        replies = []
        while True:
            reply = c.read_cmd()
            if reply.command == "end":
                return replies
            replies.append(reply)
    else:
        return [reply]

#


class Link:
    def __init__(self, data):
        for line in data.split("\n"):
            key, value = line.split("=", 1)
            if key == "name":
                self.name = unicode(value)
            elif key == "modes":
                self.modes = value.split(",")
            elif key == "type":
                self.type = value
            elif key == "remote_name":
                self.remote_name = value


class Device:
    def __init__(self, script, data):
        self.script = script
        self.uid, self.name = data.split(" ", 1)


class Profile:
    def __init__(self, script, name):
        self.script = script
        self.name = unicode(name)
        self.state = "down"
        self.current = None
        self.address = ""
    
    def parse(self, data):
        for line in data.split("\n"):
            key, value = line.split("=", 1)
            if key == "device_name":
                self.devname = value
            elif key == "state":
                self.state = value
                if " " in value:
                    self.state, self.current = value.split(" ", 1)
            elif key == "net_mode":
                self.mode = value
            elif key == "net_address":
                self.address = value
    
    def get_state(self):
        if self.state == "up":
            return _("Up")
        return _("Down")
    
    def get_address(self):
        if self.state == "up":
            if self.current:
                return self.current
            return self.address
        return ""


class Remote:
    def __init__(self, data):
        self.quality = 100
        self.encryption = None
        for arg in data.split("\t"):
            key, value = arg.split("=", 1)
            if key == "remote":
                self.remote = value
            elif key == "quality":
                self.quality = int(value)
            elif key == "encryption":
                self.encryption = value
    
    def __str__(self):
        if self.encryption and self.encryption != "none":
            txt = ">-~"
        else:
            txt = "   "
        txt += " %4s %s" % ("+" * (self.quality / 25), self.remote)
        return txt


def queryLinks(com):
    com.Net.Link.linkInfo()
    links = {}
    for rep in collect(com):
        links[rep.script] = Link(rep.data)
    return links

def queryDevices(com):
    com.Net.Link.deviceList()
    devs = []
    for rep in collect(com):
        if rep.data != "":
            for line in rep.data.split("\n"):
                devs.append(Device(rep.script, line))
    return devs

def queryProfiles(com):
    com.Net.Link.connections()
    profiles = []
    for rep in collect(com):
        if rep.data != "":
            for name in rep.data.split("\n"):
                profiles.append(Profile(rep.script, name))
    for profile in profiles:
        com.Net.Link[profile.script].connectionInfo(name=profile.name)
        profile.parse(com.read_cmd().data)
    return profiles

#

def listDevices(args=None):
    com = comar.Link()
    com.localize()
    links = queryLinks(com)
    devs = queryDevices(com)
    
    for script, link in links.items():
        print "%s:" % link.name
        for dev in filter(lambda x: x.script == script, devs):
            print " %s" % dev.name

def listProfiles(args=None):
    com = comar.Link()
    com.localize()
    links = queryLinks(com)
    profiles = queryProfiles(com)
    
    profiles.sort(key=lambda x: x.devname + x.name)
    
    name_title = "" # _("Profile")
    state_title = "" # _("Status")
    addr_title = "" # _("Address")
    
    name_size = max(max(map(lambda x: len(x.name), profiles)), len(name_title))
    state_size = max(max(map(lambda x: len(x.get_state()), profiles)), len(state_title))
    
    cstart = ""
    cend = ""
    link_list = links.items()
    link_list.sort(key=lambda x: x[1].name)
    for script, link in link_list:
        link_profiles = filter(lambda x: x.script == script, profiles)
        if len(link_profiles) > 0:
            print "%s:" % link.name
        for profile in link_profiles:
            line = "  %s%s%s | %s%s%s | %s%s%s" % (
                cstart,
                profile.name.ljust(name_size),
                cend, cstart,
                profile.get_state().center(state_size),
                cend, cstart,
                profile.get_address(),
                cend
            )
            print line

def upProfile(args):
    if len(args) != 1:
        usage()
        return
    name = args[0]
    
    com = comar.Link()
    com.localize()
    com.Net.Link.connectionInfo(name=name)
    for reply in collect(com):
        if reply.command == "result":
            com.Net.Link[reply.script].setState(name=name, state="up")

def downProfile(args):
    if len(args) != 1:
        usage()
        return
    name = args[0]
    
    com = comar.Link()
    com.localize()
    com.Net.Link.connectionInfo(name=name)
    for reply in collect(com):
        if reply.command == "result":
            com.Net.Link[reply.script].setState(name=name, state="down")

def createWizard(args):
    com = comar.Link()
    com.localize()
    
    # Ask connection type
    links = queryLinks(com)
    print _("Select connection type:")
    for i, link in enumerate(links.values()):
        print "%2d." % (i + 1), link.name
    s = int(raw_input('-> '))
    link = links.values()[s-1]
    script = links.keys()[s-1]
    
    # Ask device
    com.Net.Link[script].deviceList()
    devs = []
    for rep in collect(com):
        if rep.data != "":
            for line in rep.data.split("\n"):
                devs.append(Device(rep.script, line))
    if len(devs) == 1:
        device = devs[0]
        print _("Device '%s' selected.") % device.name
    else:
        print _("Select connection device:")
        for i, dev in enumerate(devs):
            print "%2d." % (i + 1), dev.name
        s = int(raw_input('-> '))
        device = devs[s-1]
    
    # Remote point
    if "remote" in link.modes:
        print
        print link.remote_name
        if "scan" in link.modes:
            remotes = []
            while True:
                print " 1. %s" % _("Enter manually")
                print " 2. %s" % _("Scan")
                if remotes:
                    for i, remote in enumerate(remotes):
                        print "%2d." % (i + 3), str(remote)
                s = int(raw_input('->'))
                if s == 2:
                    com.Net.Link[script].scanRemote(device=device.uid)
                    remotes = []
                    reply = com.read_cmd()
                    if reply.data != "":
                        for arg in reply.data.split("\n"):
                            remotes.append(Remote(arg))
                    print
                    print link.remote_name
    
    # Network settings
    
    # Authentication

#

def usage(args=None):
    print _("""usage: network <command> <arguments>
where command is:
 devices      List network devices
 connections  List connections
 create       Create a new connection
 up           Connect given connection
 down         Disconnect given connection""")

def main(args):
    operations = {
        "devices":      listDevices,
        "connections":  listProfiles,
        "up":           upProfile,
        "down":         downProfile,
        "create":       createWizard,
    }
    
    if len(args) == 0:
        args = ["connections"]
    
    func = operations.get(args.pop(0), usage)
    func(args)

#

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, '')
    main(sys.argv[1:])

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Network configuration tool
# Copyright (C) 2006-2009, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import comar
import dbus
import sys

link = comar.Link()
useColor = True

# Color characters
colors = {'red'       : '\x1b[31;01m',
         'blue'       : '\x1b[34;01m',
         'cyan'       : '\x1b[36;01m',
         'gray'       : '\x1b[30;01m',
         'green'      : '\x1b[32;01m',
         'light'      : '\x1b[37;01m',
         'yellow'     : '\x1b[33;01m',
         'magenta'    : '\x1b[35;01m',
         'reddark'    : '\x1b[31;0m',
         'bluedark'   : '\x1b[34;0m',
         'cyandark'   : '\x1b[36;0m',
         'graydark'   : '\x1b[30;0m',
         'greendark'  : '\x1b[32;0m',
         'magentadark': '\x1b[35;0m',
         'normal'     : '\x1b[0m'}


def colorize(msg, color):
    global useColor
    if not useColor:
        return msg
    else:
        return "%s%s%s" % (colors[color], msg, colors['normal'])

def printUsage():
    print "Usage: %s <command> <option>" % sys.argv[0]
    print
    print "Commands:"
    print "    connections     Show connections"
    print "    devices         Show devices"
    print "    create          Create profile"
    print "    delete          Delete profile"
    print "    up <profile>    Bring profile up"
    print "    down <profile>  Bring profile down"
    print
    print "Options:"
    print "    --no-color      Don't colorize output"
    print

def getInput(label):
    try:
        return raw_input(colorize(("%s > " % label), 'light'))
    except (KeyboardInterrupt, EOFError):
        print
        sys.exit(1)

def getNumber(label, min_, max_):
    index_ = min_ - 1
    while index_ < min_ or index_ > max_:
        try:
            index_ = int(raw_input(colorize(("%s > " % label), 'light')))
        except ValueError:
            pass
        except (KeyboardInterrupt, EOFError):
            print
            sys.exit(1)
    return index_

def printConnections():
    for package in link.Network.Link:
        info = link.Network.Link[package].linkInfo()
        profiles = link.Network.Link[package].connections()
        if len(profiles) > 0:
            maxstringlen = max([len(l) for l in profiles])
            print colorize("%s profiles" % info["name"], 'green')
            for profile in profiles:
                profileInfo = link.Network.Link[package].connectionInfo(profile)
                devname = profileInfo["device_name"].split(" - ")[0]
                stateInfo = link.Network.Link[package].getState(profile)
                if stateInfo.startswith("up"):
                    stateMark = "X"
                else:
                    stateMark = " "
                print "[%s]  %s%s    [%s]" % (colorize(stateMark, 'green'), colorize(profile, 'cyan'), (' ' * (maxstringlen-len(profile))), devname)
    return 0

def printDevices():
    for package in link.Network.Link:
        info = link.Network.Link[package].linkInfo()
        devices = link.Network.Link[package].deviceList().values()
        if len(devices) > 0:
            print colorize("%s devices" % info["name"], 'green')
            for d in devices:
                print "  %s" % d
    return 0

def getPackage():
    packages = []
    devicecount = 0
    index_ = 1

    for package in link.Network.Link:
        devicecount += len(link.Network.Link[package].deviceList())

    if devicecount == 0:
        print colorize("No network interface found", "red")
        return -1

    print colorize("Select interface:", "yellow")

    for package in link.Network.Link:
        if len(link.Network.Link[package].deviceList()) > 0:
            info = link.Network.Link[package].linkInfo()
            packages.append(package)
            print "  [%s] %s" % (index_, info["name"])
            index_ += 1

    if not len(packages):
        print colorize("No network backends registered", "red")
        return -1

    packageNo = getNumber("Interface", 1, len(packages)) - 1
    return packages[packageNo]

def getDevice(package):
    devices = []
    index_ = 1
    _devices = link.Network.Link[package].deviceList()

    if len(_devices) > 0:
        print
        print colorize("Select device:", "yellow")

    for devid, devname in _devices.iteritems():
        devices.append(devid)
        print "  [%s] %s" % (index_, devname)
        index_ += 1

    if not len(devices):
        print colorize("No devices on that backend", "red")
        return -1

    devNo = getNumber("Device", 1, len(devices)) - 1
    return devices[devNo]

def getDeviceMode(package):
    device_modes = []
    index_ = 1
    print
    print colorize("Select device mode:", "yellow")
    for modeName, modeDesc  in link.Network.Link[package].deviceModes():
        print "  [%s] %s" % (index_, modeDesc)
        device_modes.append(modeName)
        index_ += 1
    modeNo = getNumber("Device Mode", 1, len(device_modes)) - 1
    return device_modes[modeNo]

def getRemote(package, device):
    remote = None
    remoteName = link.Network.Link[package].remoteName()

    def scanRemote():
        remotes = []
        print
        index_ = 1
        for remotePoint in link.Network.Link[package].scanRemote(device):
            remotes.append(remotePoint["remote"])
            print "  [%s] %s" % (index_, remotePoint["remote"])
            index_ += 1
        print "  [%s] Rescan" % index_
        print "  [%s] Enter SSID manually" % (index_ + 1)
        remoteNo = getNumber(remoteName, 1, len(remotes) + 2) - 1
        if remoteNo < len(remotes):
            return remotes[remoteNo]
        elif remoteNo == len(remotes):
            return None
        else:
            return getInput(remoteName)

    while not remote:
        remote = scanRemote()
    return remote

def getAuth(package):
    auths = []
    index_ = 2
    print
    print colorize("Select authentication method:", "yellow")
    print "  [1] No authentication"
    for authName, authDesc in link.Network.Link[package].authMethods():
        auths.append(authName)
        print "  [%s] %s" % (index_, authDesc)
        index_ += 1
    authNo = getNumber("Method", 1, len(auths) + 1) - 1
    if authNo == 0:
        return ""
    return auths[authNo - 1]

def getAuthSettings(package, auth):
    settings = []
    if auth:
        print
        for paramName, paramDesc, paramType in link.Network.Link[package].authParameters(auth):
            value = getInput(paramDesc)
            settings.append((paramName, value,))
    return settings

def createProfile():
    settings = []

    # Select package
    package = getPackage()

    if package == -1:
        # No network devices
        return 1

    # Get backend info
    info = link.Network.Link[package].linkInfo()
    modes = info["modes"].split(",")

    # Select device
    if "device" in modes:
        device = getDevice(package)
        if device == -1:
            # Backend provides no device
            return 1

        settings.append(("device", device))

        # Select device mode
        if "device_mode" in modes:
            deviceMode = getDeviceMode(package)
            settings.append(("device_mode", deviceMode))

    # Remote
    if "remote" in modes:
        if "remote_scan" in modes and "device" in modes:
            remote = getRemote(package, device)
        else:
            print
            remote = getInput("Enter Remote")
        settings.append(("remote", remote,))

    # Authentication
    if "auth" in modes:
        auth = getAuth(package)
        settings.append(("auth", auth,))
        if auth:
            for key, value in getAuthSettings(package, auth):
                settings.append(("auth_%s" % key, value,))

    # Address
    if "net" in modes:
        print
        print colorize("Select IP assignment method:", "yellow")
        auto = False
        if "auto" in modes:
            print "  [1] Enter an IP address manually"
            print "  [2] Automatically obtain an IP address"
            auto = getNumber("Type", 1, 2) == 2
        if auto:
            settings.append(("net", ("auto", "", "", "")))
        else:
            net_address = getInput("Address")
            net_mask = getInput("Mask")
            net_gateway = getInput("Gateway")
            settings.append(("net", ("manual", net_address, net_mask, net_gateway)))

    # Get name and create it
    profile = None
    print
    while not profile:
        profile = getInput("Profile name").strip()

    try:
        for key, value in settings:
            if key == "device":
                link.Network.Link[package].setDevice(profile, value)
            elif key == "device_mode":
                link.Network.Link[package].setDeviceMode(profile, value)
            elif key == "remote":
                link.Network.Link[package].setRemote(profile, value)
            elif key == "auth":
                link.Network.Link[package].setAuthMethod(profile, value)
            elif key.startswith("auth_"):
                link.Network.Link[package].setAuthParameters(profile, key[5:], value)
            elif key == "net":
                mode_, address_, mask_, gateway_ = value
                link.Network.Link[package].setAddress(profile, mode_, address_, mask_, gateway_)
    except dbus.DBusException, e:
        print e
        return 1
    return 0

def deleteProfile():
    _index = 1
    profiles = []
    for package in link.Network.Link:
        _profiles = link.Network.Link[package].connections()
        if len(_profiles) > 0:
            maxstringlen = max([len(l) for l in _profiles])
            info = link.Network.Link[package].linkInfo()
            print colorize("%s profiles" % info["name"], 'green')

            for profile in _profiles:
                profileInfo = link.Network.Link[package].connectionInfo(profile)
                devname = profileInfo["device_name"].split(" - ")[0]

                print "  [%d] %s%s    [%s]" % (_index, profile, (' '*(maxstringlen-len(profile))), devname)
                profiles.append((package, profile, ))
                _index += 1

    package, profile = profiles[getNumber("Delete", 1, _index - 1) - 1]
    link.Network.Link[package].deleteConnection(profile)
    return 0

def stateProfile(state):
    try:
        profile = sys.argv[2]
    except:
        printUsage()
        return 1

    for package in link.Network.Link:
        if profile in link.Network.Link[package].connections():
            ifname = link.Network.Link[package].connectionInfo(profile)["device_id"].split("_")[-1]
            print "Bringing %s %s (%s)" % (state, colorize(profile, "light"), colorize(ifname, "cyan"))
            link.Network.Link[package].setState(profile, state)

    return 0

def main():
    try:
        command = sys.argv[1]
    except:
        printUsage()
        return 1

    if "--no-color" in sys.argv:
        global useColor
        useColor = False
        sys.argv.remove("--no-color")

    if command == "connections":
        return printConnections()
    elif command == "devices":
        return printDevices()
    elif command == "create":
        return createProfile()
    elif command == "delete":
        return deleteProfile()
    elif command in ("up", "down"):
        return stateProfile(command)
    else:
        printUsage()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import dbus

import gettext
__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

SUCCESS, FAIL = xrange(2)


class AuthenticationMode:
    """ Authentication Mode : identifier: used when calling methods, type: specifies login options, name: readable name for users """
    def __init__ (self, data):
        self.identifier, self.type, self.name = data.split(",")

class Profile:
    """ Network service profile """
    def __init__(self, script, name):
        self.script = script
        self.name = unicode(name)
        self.state = "down"
        self.current = None
        self.address = ""
        self.devname=""
        self.devid=""
        self.netmode =""
        self.namemode =""
        self.mask=""                      # special attribute for ethernet
        self.gateway=""                   # special attribute for ethernet
        self.remote=""                    # special attribute for dial up&wireless

    def parse(self, data):
        """ Adds attributes if their value exists : 'devname','devid','state' and/or 'current','mode','address','mask','gateaway'
            and parses their value from 'data' input parameter
        """
        for key, value in data.iteritems():
            if key == "device_name":
                self.devname = value
            elif key == "device_id":
                self.devid = value
            elif key == "state":
                self.state = value
                if " " in value:
                    self.state, self.current = value.split(" ", 1)
            elif key == "net_mode":
                self.netmode = value
            elif key == "net_address":
                self.address = value
            elif key == "net_mask":
                self.mask=value
            elif key == "net_gateway":
                self.gateway = value
            elif key =="namemode":
                self.namemode = value
            elif key =="remote":
                self.remote = value

    def print_info (self):
        """ Prints object's attributes and their values """
        print _("Connection Name : %s ") % self.name
        print _("Status          : %s ") % self.get_state()
        print _("Adress          : %s ") % self.get_address()

        if(self.devname):
            print _("Device Name     : %s ") % self.devname
        if (self.devid):
            print _("Device Id       : %s ") % self.devid
        if(self.mask):
            print _("Mask            : %s ") % self.mask
        if(self.gateway):
            print _("Gateway         : %s ") % self.gateway
        if(self.netmode):
            print _("Netmode         : %s ") % self.netmode
        if(self.namemode):
            print _("Namemode        : %s ") % self.namemode
        if (self.remote):
            print _("Remote          : %s ") % self.remote

    def get_state(self):
        """ Returns state of profile """
        if self.state == "up":
            return _("Up")
        return _("Down")

    def get_address(self):
        """ If profile's state is "up" returns 'current'( or 'address' if current doesnt exist ) """
        if self.state == "up":
            if self.current:
                return self.current
            return self.address
        return ""

def input_number(_label, _min, _max):
    """ Checks limits of read input from command line -any excess will cause warning- """
    index = _min - 1
    while index < _min or index > _max:
        try:
            index = int(raw_input('%s > ' % _label))
        except ValueError:
            pass
    return index

def input_text(_label):
    return raw_input("%s > " % _label)


def usage():
    """ Prints 'network' script usage """
    print _("""usage: %s <command> <arguments>
where command is:
 devices      List network devices
 connections  List connections
 info         List properties of a given connection
 create       Create a new connection
 delete       Delete a connection
 up           Connect given connection
 down         Disconnect given connection""") % sys.argv[0]
    return FAIL

def getScripts(bus):
    """Returns a list of packages that provide Net.Link"""
    obj = bus.get_object("tr.org.pardus.comar", "/", introspect=False)
    return obj.listModelApplications("Net.Link", dbus_interface="tr.org.pardus.comar")

def getScriptDetails(bus, script):
    """Returns details of given script"""
    obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
    return obj.linkInfo(dbus_interface="tr.org.pardus.comar.Net.Link")

def getConnectionDetails(bus, script, profile):
    """Returns details of given script/profile"""
    obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
    return obj.connectionInfo(profile, dbus_interface="tr.org.pardus.comar.Net.Link")

def getDevices(bus, script):
    """Returns devices related to script."""
    obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
    return obj.deviceList(dbus_interface="tr.org.pardus.comar.Net.Link")

def getProfiles(bus, script):
    """Returns profiles of a script."""
    obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
    return obj.connections(dbus_interface="tr.org.pardus.comar.Net.Link")

def getRemotes(bus, script, device):
    """Returns profiles of a script."""
    obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
    return obj.scanRemote(device, dbus_interface="tr.org.pardus.comar.Net.Link")

def listProfiles(bus, args):
    """Lists network profiles."""
    try:
        scripts = {}
        profiles = []
        for script in getScripts(bus):
            scripts[script] = getScriptDetails(bus, script)["name"]
            for profile in getProfiles(bus, script):
                profile_details = getConnectionDetails(bus, script, profile)

                profile_info = Profile(script, profile)
                profile_info.parse(profile_details)

                try:
                    device = profile_details["device_id"].split("_")[-1]
                    state = profile_info.get_state()
                    address = profile_info.get_address()
                except KeyError:
                    continue

                profiles.append((script, profile, device, state, address, ))
    except dbus.DBusException, e:
        print _("Error: %s") % str(e)
        return FAIL

    if not profiles:
        return

    name_size = max(map(lambda x: len(x[1]), profiles))
    device_size = max(map(lambda x: len(x[2]), profiles))
    state_size = max(map(lambda x: len(x[3]), profiles))

    cstart = ""
    cend = ""
    last = None
    for script, profile, device, state, address in profiles:
        if last != script:
            last = script
            print "%s:" % scripts[script]
        line = "  %s%s%s | %s%s%s | %s%s%s | %s%s%s" % (
            cstart,
            profile.ljust(name_size),
            cend, cstart,
            device.ljust(device_size),
            cend, cstart,
            state.center(state_size),
            cend, cstart,
            address,
            cend
        )
        print line

    return SUCCESS

def listDevices(bus, args):
    try:
        devices = []
        scripts = {}
        for script in getScripts(bus):
            scripts[script] = getScriptDetails(bus, script)["name"]
            for devid, devname in getDevices(bus, script).iteritems():
                devices.append((script, devid, devname, ))
    except dbus.DBusException, e:
        print _("Error: %s") % str(e)
        return FAIL

    id_size = max(map(lambda x: len(x[1]), devices))

    cstart = ""
    cend = ""
    last = None
    for script, devid, devname in devices:
        if last != script:
            print "%s:" % scripts[script]
            last = script
        line = "  %s%s%s | %s%s%s" % (
            cstart,
            devid.ljust(id_size),
            cend, cstart,
            devname,
            cend
        )
        print line

    return SUCCESS

def setState(bus, state, args):
    try:
        if not 0 < len(args) < 3:
            return usage()

        if len(args) == 2:
            obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % args[1], introspect=False)
            obj.setState(unicode(args[0]), state, dbus_interface="tr.org.pardus.comar.Net.Link")
        else:
            profiles = {}
            for script in getScripts(bus):
                for profile in getProfiles(bus, script):
                    if profile not in profiles:
                        profiles[profile] = []
                    profiles[profile].append(script)

            if unicode(args[0]) not in profiles:
                print _("No such profile.")
                return FAIL

            if len(profiles[unicode(args[0])]) > 1:
                print _("There are more than one profiles named '%s'") % profile
                print _("Use one of the following commands:")
                for script in profiles[unicode(args[0])]:
                    print "  %s %s '%s' %s" % (sys.argv[0], state, profile, script)
                return FAIL
            else:
                script = profiles[unicode(args[0])][0]

            obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
            obj.setState(unicode(args[0]), state, dbus_interface="tr.org.pardus.comar.Net.Link")
    except dbus.DBusException, e:
        print _("Error: %s") % str(e)
        return FAIL

    return SUCCESS

def upProfile(bus, args):
    """Changes status of given named profile to 'up'"""
    return setState(bus, "up", args)

def downProfile(bus, args):
    """Changes status of given named profile to 'down'"""
    return setState(bus, "down", args)

def createWizard(bus, args):
    """Creates network connection"""

    profile = input_text(_("Profile name"))

    # Ask connection type
    scripts = getScripts(bus)
    index = 0
    print
    print _("Connection types:")
    for script in scripts:
        index += 1
        print "  [%s] %s" % (index, script)
    index = input_number(_("Type"), 1, len(scripts))
    script = scripts[index - 1]
    script_info = getScriptDetails(bus, script)

    selected_auth_type = None
    modes = script_info["modes"].split(",")

    auth_modes = []
    if "auth_modes" in script_info:
        auth_modes = script_info["auth_modes"].split(";")

    # Ask device
    devices = getDevices(bus, script)
    if not len(devices):
        print _("No avaible device for this type of connection")
        return FAIL

    # {k:v, k: v, ...} -> ((k, v), (k, v), ...)
    devices = zip(devices.keys(), devices.values())

    index = 0
    print
    print _("Devices:")
    for devid, devname in devices:
        index += 1
        print "  [%s] %s %s" % (index, devname, devid)
    index = input_number(_("Device"), 1, len(devices))
    device = devices[index - 1][0]

    # Remote point
    if "remote" in modes:
        print
        print _("%s:") % script_info["remote_name"]
        if "scan" in modes:
            remotes = []
            name_size = 0
            while True:
                print "  [1] %s" % _("Enter manually")
                print "  [2] %s" % _("Scan")
                if remotes:
                    for i, remote in enumerate(remotes):
                        enc = ""
                        quality = (int(remote["quality"]) / 25) + 1
                        if remote["encryption"] != "none":
                            enc = remote["encryption"]
                        print "  [%s] %s [%s] | %s | %s" % (i + 3, remote["remote"].ljust(name_size), remote["mac"], str("=" * quality).ljust(5), enc)
                s = input_number("", 1, len(remotes) + 2)
                if s == 1:
                    remote = input_text(script_info["remote_name"])
                    apmac = ""
                    break
                elif s == 2:
                    remotes = getRemotes(bus, script, device)
                    if remotes:
                        name_size = max(map(lambda x: len(x["remote"]), remotes))
                        print
                        print _("%s:") % script_info["remote_name"]
                    else:
                        print _("No remote access points found")
                        print
                        print _("%s:") % script_info["remote_name"]
                else:
                    remote = remotes[s - 3]["remote"]
                    apmac = remotes[s - 3]["mac"]
                    selected_auth_type = remotes[s - 3]["encryption"]
                    break
        else:
            remote = input_text("")

    # Authentication settings
    if auth_modes:
        chosen_mode = None
        if selected_auth_type and selected_auth_type != "none":
            chosen_mode = AuthenticationMode("%s,pass,%s" % (selected_auth_type, selected_auth_type))
        else:
            index = 1
            print
            print _("Choose authentication type:")
            for mode in auth_modes:
                mode = AuthenticationMode(mode)
                print "  [%s] %s" % (index, mode.name)
                index += 1
            print "  [%s] No authentication" % index
            mode_no = input_number("Authentication", 1, index + 1)
            if (mode_no != index) :
                chosen_mode = AuthenticationMode(auth_modes[mode_no - 1])
        if chosen_mode:
            if (chosen_mode.type == "pass" ):
                print
                user_name = ""
                password = input_text(_("Password"))
            elif (chosen_mode.type == "login") :
                print
                user_name = input_text(_("Username"))
                password = input_text(_("Password"))

            obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
            obj.setAuthentication(profile, chosen_mode.identifier, user_name, password, dbus_interface="tr.org.pardus.comar.Net.Link")

    # Network settings
    if "net" in modes:
        print
        print _("Network settings:")
        is_auto = False
        if "auto" in modes:
            print "  [1] %s" % _("Automatic query (DHCP)")
            print "  [2] %s" % _("Manual configuration")
            s = input_number("", 1, 2)
            if s == 1:
                is_auto = True
        if not is_auto:
            address = input_text(_("IP Address"))
            mask = input_text(_("Network mask"))
            gateway = input_text(_("Gateway"))

    # Create profile
    obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
    obj.setConnection(profile, device, dbus_interface="tr.org.pardus.comar.Net.Link")
    if "remote" in modes:
        obj.setRemote(profile, remote, apmac, dbus_interface="tr.org.pardus.comar.Net.Link")
    if "net" in modes:
        if is_auto:
            obj.setAddress(profile, "auto", "", "", "", dbus_interface="tr.org.pardus.comar.Net.Link")
        else:
            obj.setAddress(profile, "manual", address, mask, gateway, dbus_interface="tr.org.pardus.comar.Net.Link")

def deleteWizard(bus, args):
    try:
        scripts = {}
        profiles = []
        for script in getScripts(bus):
            scripts[script] = getScriptDetails(bus, script)["name"]
            for profile in getProfiles(bus, script):
                profile_details = getConnectionDetails(bus, script, profile)
                try:
                    device = profile_details["device_id"].split("_")[-1]
                except KeyError:
                    continue
                profiles.append((script, profile, device, ))
    except dbus.DBusException, e:
        print _("Error: %s") % str(e)
        return FAIL

    name_size = max(map(lambda x: len(x[1]), profiles))
    num_size = int(len(profiles) / 10)

    index = 0
    last = None
    for script, profile, device in profiles:
        if last != script:
            last = script
            print "%s:" % scripts[script]
        print "  [%s] %s | %s" % (str(index + 1).rjust(num_size), profile.ljust(name_size), device)
        index += 1

    profile_index = input_number(_("Profile"), 1, len(profiles))

    try:
        script, profile, device = profiles[profile_index - 1]
        obj = bus.get_object("tr.org.pardus.comar", "/package/%s" % script, introspect=False)
        obj.deleteConnection(profile, dbus_interface="tr.org.pardus.comar.Net.Link")
    except dbus.DBusException, e:
        print _("Error: %s") % str(e)
        return FAIL

    print _("Profile %s removed.") % profile

    return SUCCESS


def infoProfile(bus, args):
    """ Prints detailed information about a given profile """
    try:
        if not 0 < len(args) < 3:
            return usage()

        if len(args) == 2:
            profile, script = args
            info = getConnectionDetails(bus, script, unicode(profile))
        else:
            profiles = {}
            for script in getScripts(bus):
                for profile in getProfiles(bus, script):
                    if profile not in profiles:
                        profiles[profile] = []
                    profiles[profile].append(script)

            if unicode(args[0]) not in profiles:
                print _("No such profile.")
                return FAIL

            if len(profiles[unicode(args[0])]) > 1:
                print _("There are more than one profiles named '%s'") % profile
                print _("Use one of the following commands:")
                for script in profiles[unicode(args[0])]:
                    print "  %s info '%s' %s" % (sys.argv[0], profile, script)
                return FAIL
            else:
                script = profiles[unicode(args[0])][0]

            profile = unicode(args[0])
            info = getConnectionDetails(bus, script, profile)
    except dbus.DBusException, e:
        print _("Error: %s") % str(e)
        return FAIL

    profile_info = Profile(script, profile)
    profile_info.parse(info)
    profile_info.print_info()

    return SUCCESS

def main(args):
    try:
        bus = dbus.SystemBus()
    except dbus.DBusException, e:
        print _("D-Bus Error: %s") % str(e)
        return FAIL

    operations = {
        "devices":      listDevices,
        "connections":  listProfiles,
        "up":           upProfile,
        "down":         downProfile,
        "create":       createWizard,
        "delete":       deleteWizard,
        "info":         infoProfile,
    }

    if len(args) == 0:
        return usage()

    try:
        func = operations[args.pop(0)]
    except KeyError:
        return usage()
    try:
        return func(bus, args)
    except (KeyboardInterrupt, EOFError,):
        print
        print _("Cancelled")
        return FAIL

    return SUCCESS

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

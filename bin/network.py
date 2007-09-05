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


def input_number(max_no):
    """ Checks limits of read input from command line -any excess will cause warning- """
    input = int(raw_input('-> '))
    while ( input >= max_no or input <= 0 ) :
        print _("Limit excess, please enter a valid number: ( interval: 0 < entry < %s )") % max_no
        input = int(raw_input('-> '))
    return input

def collect(c):
    """ Reads commands -to 'replies' list- if exist between "start" and "end" commands """
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

class AuthenticationMode :
    """ Authentication Mode : identifier: used when calling methods, type: specifies login options, name: readable name for users """
    def __init__ (self,data):
        list = data.split(",")
        self.identifier = list[0]
        self.type = list[1]
        self.name = list[2]

class Link:
    """ Link class: possible attributes : name, modes, type, remote_name , auth"""
    def __init__(self, data):
        """ reads attributes' values from input text -read command's data fielad, generally from comar-"""
        self.auth_modes = []
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
            elif key == "auth_modes":
                self.parse(value)
    def parse(self,data):                    
        """ Parser for reading avaible authentication modes for current Link """
        for line in data.split(";"):                
            mode = AuthenticationMode(line)     #related authentication mode objects are created and added to auth_modes list   
            self.auth_modes.append(mode)
        
class Device:
    """ Device class : attributes : script, uid, name """
    def __init__(self, script, data):
        self.script = script
        self.uid, self.name = data.split(" ", 1)

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
        for line in data.split("\n"):
            key, value = line.split("=", 1)
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
        label = self.remote
        quality = "+" * ((self.quality / 25) + 1)
        txt = _("Found: %(essid)s [%(quality)s]") % {"essid": label.ljust(20), "quality": quality.ljust(5)}
        if self.encryption and self.encryption != "none":
            txt += " " + _("[encrypted]")
        return txt

def queryLinks(com):
    """ Input parameter : 'com' is comar's Link object. Retrieves script and data variable for each link from 
        'com.Net.Link.linkInfo' method and returns them as 'links' dictionary
    """ 
    com.Net.Link.linkInfo()                 #group
    links = {}
    for rep in collect(com):                # reads scrip-data values ( by collect method ) and stores them in dictionary
        links[rep.script] = Link(rep.data)
        
        ################# TEST code for parsing operations of Link authentication properties ###########################
        if (links[rep.script].auth_modes):
            print "\nAuthentication mode properties for % s \n" % links[rep.script].name
            for item in links[rep.script].auth_modes :
                line = "identifier: " + item.identifier.ljust(15) + "type: "+ item.type + "\t name: "+item.name
                print line
        ################################################################################################################
    print    
    return links

def queryDevices(com):
    """ Input parameter : 'com' is comar's Link object. Retrieves deviceList from 'com.Net.Link.deviceList'
        method and creates Device objects for each, returns list of them 
    """ 
    com.Net.Link.deviceList()
    devs = []
    for rep in collect(com):
        if rep.data != "":
            for line in rep.data.split("\n"):
                devs.append(Device(rep.script, line))
    return devs

def queryProfiles(com):
    """ Input parameter : 'com' is comar's Link object. Retrieves connections' info  from 'com.Net.Link.connections'
        method and creates Profile objects for each, returns a list of them 
    """ 
    com.Net.Link.connections()
    profiles = []
    for rep in collect(com):
        if rep.data != "":
            for name in rep.data.split("\n"):
                profiles.append(Profile(rep.script, name))
    for profile in profiles:
        com.Net.Link[profile.script].connectionInfo(name=profile.name)  
        profile.parse(com.read_cmd().data)                   # read_cmd reads reply message from comar deamon
    return profiles

def listDevices(args=None):
    """ Prints list of avaible network devices"""
    com = comar.Link()                     #communicating with comar deamon
    com.localize()                         #set language for translated replies
    links = queryLinks(com)
    devs = queryDevices(com)
    
    #print link names and related device names
    for script, link in links.items():
        print "%s:" % link.name
        for dev in filter(lambda x: x.script == script, devs):
            print " %s" % dev.name

def listProfiles(args=None):
    """ Prints profiles of each kind of link """
    com = comar.Link()                     #communicating with comar deamon
    com.localize()                         #set language for translated replies
    links = queryLinks(com)
    profiles = queryProfiles(com)
    
    profiles.sort(key=lambda x: x.devname + x.name)     #profiles are sorted by device_name + name
    
    name_title = "" # _("Profile")
    state_title = "" # _("Status")
    addr_title = "" # _("Address")
    
    #name_size and state_size are set  to the maximum length of name/state of profiles
    # -for ljust operations in output format-
    name_size = max(max(map(lambda x: len(x.name), profiles)), len(name_title))
    state_size = max(max(map(lambda x: len(x.get_state()), profiles)), len(state_title))
    
    cstart = ""
    cend = ""
    link_list = links.items()
    link_list.sort(key=lambda x: x[1].name)
    profile_names_list=[]
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
            profile_names_list.append(profile.name)             
    return profile_names_list                   # returns all profile_names defined on comp.

def upProfile(args):
    """ Changes status of given named profile to 'up'"""
    if len(args) == 0:
        usage()
        return
    else:                  
        name=args[0]
        i = 1
        while ( i!= len(args)):                 # for profiles that has names having more than one word
            name = name + " "+ args[i]
            i += 1
    com = comar.Link()                          #communicating with comar deamon
    com.localize()                              #set language for translated replies
    com.Net.Link.connectionInfo(name=name)      #get connection info from comar deamon
    for reply in collect(com):
        if reply.command == "result":           #reply has related 'script'(net-tools)'command' and 'data' fields. 
            com.Net.Link[reply.script].setState(name=name, state="up")  #Link group's avaible methods are declared in 'comar/comar/etc/model.xml'

def downProfile(args):
    """ Changes status of given named profile to 'down'"""
    if len(args) == 0:
        usage()
        return
    else:                  
        name=" ".join(args)
    com = comar.Link()                          #communicating with comar deamon
    com.localize()                              #set language for translated replies
    com.Net.Link.connectionInfo(name=name)      #get connection info from comar deamon
    for reply in collect(com):
        if reply.command == "result":
            com.Net.Link[reply.script].setState(name=name, state="down")

def createWizard(args):
    """ Creates network connection """
    com = comar.Link()              #communicating with comar deamon
    com.localize()                  #set language for translated replies
    
    conn_name = raw_input('%s -> ' % _("Enter new connection name"))    #read connection name from command line
    
    # Ask connection type
    links = queryLinks(com)
    print _("Select connection type:")
    for i, link in enumerate(links.values()):
        print "%2d." % (i + 1), link.name
    s = input_number(len(links.values())+1)
    
    link = links.values()[s-1]
    script = links.keys()[s-1]
    script_object = com.Net.Link[script]
    
    # Ask device
    script_object.deviceList()
    devs = []
    for rep in collect(com):
        if rep.data != "":
            for line in rep.data.split("\n"):
                devs.append(Device(rep.script, line))
    if len(devs) == 1:
        device = devs[0]
        print _("Device '%s' selected.") % device.name
    elif(len(devs) == 0):
        print _("No avaible device for this type of connection")
        return
    else:
        print _("Select connection device:")
        for i, dev in enumerate(devs):
            print "%2d." % (i + 1), dev.name
        s = input_number(len(devs)+1)
        device = devs[s-1]
    
    # Remote point
    global selected_auth_type
    selected_auth_type = None
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
                s = int( raw_input('-> ') )
                if s == 1:
                    remote = raw_input('%s -> ' % link.remote_name)
                    break
                elif s == 2:
                    script_object.scanRemote(device=device.uid)
                    remotes = []
                    reply = com.read_cmd()
                    if reply.data != "":
                        for arg in reply.data.split("\n"):
                            remotes.append(Remote(arg))
                    print
                    print link.remote_name
                else:
                    remote = remotes[s-3].remote
                    selected_auth_type = remotes[s-3].encryption
                    break
        else:
            remote = raw_input('-> ')
    
    # Network settings
    if "net" in link.modes:
        print
        print _("Network settings:")
        is_auto = False
        if "auto" in link.modes:
            print " 1. %s" % _("Automatic query (DHCP)")
            print " 2. %s" % _("Manual configuration")
            s = input_number(3)
            if s == 1:
                is_auto = True
        if not is_auto:
            address = raw_input('%s -> ' % _("IP Address"))
            mask = raw_input('%s -> ' % _("Network mask"))
            gateway = raw_input('%s -> ' % _("Gateway"))
    
    # Authentication settings 
    if ( link.auth_modes ):
        if ( selected_auth_type ):
            chosen_mode = AuthenticationMode( selected_auth_type + ",pass,"+ selected_auth_type )
        else:
            i = 1
            print _("Choose authentication type:")
            for mode in link.auth_modes:
                print "%s -> %s" % ( i,mode.name)
                i += 1
            print "%s -> No authentication" % i            
            mode_no = input_number(i+1)
            if (mode_no != i) :
                chosen_mode = link.auth_modes [mode_no-1]    
                if (chosen_mode.type == "pass" ):
                    user_name = ""
                    password = raw_input('%s -> ' % _("Enter password "))
                elif (chosen_mode.type == "login") :
                    user_name = raw_input('%s -> ' % _("Enter user name "))
                    password = raw_input('%s -> ' % _("Enter password "))

                script_object.setAuthentication(name= conn_name, authmode=chosen_mode.identifier, user=user_name, password=password) 
    
    # Create profile
    script_object.setConnection(name=conn_name, device=device.uid)
    if "remote" in link.modes:
        script_object.setRemote(name=conn_name, remote=remote)
    if "net" in link.modes:
        if is_auto:
            script_object.setAddress(name=conn_name, mode="auto", address="", mask="", gateway="")
        else:
            script_object.setAddress(name=conn_name, mode="manual", address=address, mask=mask, gateway=gateway)

def deleteWizard(args):
    """ Deletes a given/chosen profile """
    if len(args)== 0:
        print _("Profiles :")
        profile_names_list = listProfiles(args)
        profile_name = raw_input('%s -> ' % _("Name of profile to delete "))
        while ( not ( profile_names_list.__contains__(profile_name) )):
            print _("Please enter a valid profile name ")
            profile_name = raw_input()
    else:                                     
        profile_name=" ".join(args)
    com = comar.Link()
    com.localize()
    com.Net.Link.connectionInfo(name=profile_name)
    for reply in collect(com):
        if reply.command == "result":
            com.Net.Link[reply.script].deleteConnection(name=profile_name)

def infoProfile (args):
    """ Prints detailed information about a given profile """
    profile_name = ""
    if ( len(args) == 0 ):
        profile_name = raw_input('%s -> ' % _("Enter name of profile"))
    else:                 
        profile_name=" ".join(args)
    com = comar.Link()
    com.localize()    
    com.Net.Link.connectionInfo(name=profile_name)

    global found
    found = False
    for reply in collect(com):
        if reply.command == "result":
            found = True
            profile = Profile(reply.script, profile_name)
            profile.parse( reply.data )
            print
            profile.print_info()
    if ( not found ) :
        print _("No such profile")
   
def usage(args=None):
    """ Prints 'network' script usage """
    print _("""usage: network <command> <arguments>
where command is:
 devices      List network devices
 connections  List connections
 info         List properties of a given connection
 create       Create a new connection
 delete       Delete a connection
 up           Connect given connection
 down         Disconnect given connection""")
    
def main(args):
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
        args = ["connections"]
        
    #    Related functions according to command_line_parameters[0] -default:'connections'('listProfiles' function),
    #    for any improper command : 'usage'function-

    func = operations.get(args.pop(0), usage)
    func(args)
    
if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, '')
    main(sys.argv[1:])


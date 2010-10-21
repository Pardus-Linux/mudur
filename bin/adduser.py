#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is a script to easily add a user to system with comar
#

import os
import sys
import dbus
import time
from optparse import OptionParser


# uid = -1 means next available uid
# first group in the groups list is the main group

user = {"uid": -1,
        "username": "kaplan",
        "realname": "Pardus",
        "home": "/home/kaplan",
        "shell": "/bin/bash",
        "password": "pardus",
        "defaultgroup": "users",
        "groups": [],
        "admingroups": ["wheel"],
        "grants": [],
        "blocks": []
}

defaultGroups = "users,cdrom,plugdev,floppy,disk,audio,video,power,dialout,lp,lpadmin"

def fail(_message):
    print _message
    sys.exit(1)

def connectToDBus():
    global bus
    bus = None

    try:
        bus = dbus.SystemBus()
    except dbus.DBusException:
        return False

    if bus:
        return True

def addUser():
    obj = bus.get_object("tr.org.pardus.comar", "/package/baselayout")
    try:
        obj.addUser(user["uid"], user["username"], user["realname"],
                    user["home"], user["shell"], user["password"],
                    user["groups"], user["grants"], user["blocks"],
                    dbus_interface="tr.org.pardus.comar.User.Manager")
    except dbus.DBusException, e:
        fail("Error: %s" % e)


if __name__ == "__main__":
    usage = "usage: %prog [options] username"
    parser = OptionParser(usage=usage)

    parser.add_option("-c", "--comment", dest="realname", type="string", default="Pardus",
            help="comment for the user, usually used for Full Name")

    parser.add_option("-u", "--uid", dest="uid", type="int", default=-1,
            help="user id number, default is -1 meaning next available")

    parser.add_option("-g", "--gid", dest="defaultgroup", type="string", default=user["defaultgroup"],
            help="default group name for user")

    parser.add_option("-G", "--groups", dest="groups", type="string", default=defaultGroups,
            help="groups that user is member of")

    parser.add_option("-p", "--password", dest="password", type="string", default="pardus",
            help="password")

    parser.add_option("-d", "--home", dest="home", type="string", default="",
            help="password")

    parser.add_option("-s", "--shell", dest="shell", type="string", default="/bin/bash",
            help="default login shell")

    parser.add_option("--admin", action="store_true", dest="isadmin", default=False,
            help="give user admin rights, adding to wheel group")

    parser.add_option("--dry-run", action="store_true", dest="dryrun", default=False,
            help="do not add user, only show what will be done")


    (opts, args) = parser.parse_args()

    if len(args) != 1:
        fail("Please provide a username.")

    user["username"] = args[0]
    groups = opts.groups.split(",")


    if opts.home == "":
        user["home"] = "/home/%s" % user["username"]
    else:
        user["home"] = opts.home


    if opts.defaultgroup in groups:
        groups.remove(user["defaultgroup"])
    user["defaultgroup"] = opts.defaultgroup
    user["groups"].append(user["defaultgroup"])

    if opts.isadmin:
        for i in user["admingroups"]:
            if i not in groups:
                groups.append(i)


    user["groups"].extend(groups)
    user["shell"] = opts.shell
    user["realname"] = opts.realname
    user["password"] = opts.password
    user["uid"] = opts.uid

    if opts.dryrun:
        for i in user.keys():
            print "%s\t%s" % (i, user[i])
    else:
        if os.getuid() != 0:
            fail("You must have root permissions to add a user")

        if not connectToDBus():
            fail("Could not connect to D-Bus, please check your system settings")
        addUser()


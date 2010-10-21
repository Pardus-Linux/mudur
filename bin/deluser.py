#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is a script to easily add a user to system with comar
#

import os
import pwd
import sys
import dbus
import time
from optparse import OptionParser

user = {"uid": None,
        "deletefiles": False
}

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

def delUser():
    obj = bus.get_object("tr.org.pardus.comar", "/package/baselayout")
    try:
        obj.deleteUser(user["uid"], user["deletefiles"],
                    dbus_interface="tr.org.pardus.comar.User.Manager")
    except dbus.DBusException, e:
        fail("Error: %s." % e)


if __name__ == "__main__":
    usage = "usage: %prog [options] username"
    parser = OptionParser(usage=usage)

    parser.add_option("-r", "--remove-home", dest="removehome", action="store_true",
            help="Also remove user home directory")

    (opts, args) = parser.parse_args()

    if len(args) != 1:
        fail("please give one username to delete")

    try:
        user["uid"] = pwd.getpwnam(args[0]).pw_uid
    except KeyError:
        fail("Error: No such user '%s'" % args[0])

    user["deletefiles"] = opts.removehome

    if os.getuid() != 0:
        fail("you must have root permissions to delete a user")

    if not connectToDBus():
        fail("Could not connect to DBUS, please check your system settings")
    delUser()


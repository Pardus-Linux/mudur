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

    for i in range(5):
        try:
            print "trying to start dbus.."
            bus = dbus.bus.BusConnection(address_or_type="unix:path=/var/run/dbus/system_bus_socket")
            break
        except dbus.DBusException:
            time.sleep(1)
            print "wait dbus for 1 second..."

    if bus:
        return True

    return False

def delUser():
    obj = bus.get_object("tr.org.pardus.comar", "/package/baselayout")
    obj.deleteUser(user["uid"], user["deletefiles"],
                dbus_interface="tr.org.pardus.comar.User.Manager")


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
        fail("no such user")

    user["deletefiles"] = opts.removehome

    if os.getuid() != 0:
        fail("you must have root permissions to delete a user")

    if not connectToDBus():
        fail("Could not connect to DBUS, please check your system settings")
    delUser()


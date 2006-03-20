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

i18n_source_list = [ "mudur.py", "service.py" ]

def update_messages():
    os.system("xgettext -o po/mudur.pot %s" % " ".join(i18n_source_list))
    for item in os.listdir("po"):
        if item.endswith(".po"):
            os.system("msgmerge -q -o temp.po po/%s po/mudur.pot" % item)
            os.system("cp temp.po po/%s" % item)
    os.system("rm -f temp.po")

def install(args):
    if args == []:
        prefix = "/"
    else:
        prefix = args[0]
    
    os.system("cp mudur.py %s" % os.path.join(prefix, "sbin/mudur.py"))
    os.system("cp hotplug.py %s" % os.path.join(prefix, "sbin/hotplug.py"))
    os.system("cp service.py %s" % os.path.join(prefix, "bin/service"))
    
    for item in os.listdir("po"):
        if item.endswith(".po"):
            lang = item[:-3]
            dest = "usr/share/locale/%s/LC_MESSAGES/mudur.mo" % lang
            os.system("msgfmt po/%s -o %s" % (item, os.path.join(prefix, dest)))

def usage():
    print "setup.py install [prefix]"
    print "setup.py update_messages"

def do_setup(args):
    if args == []:
        usage()
    
    elif args[0] == "install":
        install(args[1:])
    
    elif args[0] == "update_messages":
        update_messages()
    
    else:
        usage()

if __name__ == "__main__":
    do_setup(sys.argv[1:])

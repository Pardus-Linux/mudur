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

source_list = [ "mudur.py", "service.py" ]

def update_messages():
    os.system("xgettext -o po/mudur.pot %s" % " ".join(source_list))
    # FIXME: merge with old translations

def install(args):
    if args == []:
        prefix = "/"
    else:
        prefix = args[0]
    
    os.system("cp mudur.py %s" % os.path.join(prefix, "sbin/mudur.py"))
    os.system("cp service.py %s" % os.path.join(prefix, "bin/service"))
    
    # FIXME: compile and install translations

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

if __name__ == "__main__":
    do_setup(sys.argv[1:])

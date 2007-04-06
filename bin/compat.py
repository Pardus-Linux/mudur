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
import subprocess

def wrap_service(package, op):
    cmd = ["service", package, op]
    return subprocess.call(cmd)

def populate_initd():
    for name in os.listdir("/var/db/comar/code"):
        if name.startswith("System_Service_"):
            srvname = name[15:-3]
            if not os.path.exists("/etc/init.d/%s" % srvname):
                os.symlink("compat.py", "/etc/init.d/%s" % srvname)

if __name__ == "__main__":
    myname = os.path.basename(sys.argv[0])
    if len(sys.argv) == 2:
        sys.exit(wrap_service(myname, sys.argv[1]))
    elif myname == "compat.py" and os.getuid() == 0:
        populate_initd()

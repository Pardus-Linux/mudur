#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2009 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import subprocess
import sys
import os

# This script populates the /etc/init.d directory by creating symlinks to the
# compat.py. This way, when /etc/init.d/<service_name> <action> is called, the symlink
# delegates this transparently to the /bin/service command.

# Usage:
# python compat.py
# /etc/init.d/samba start


def wrap_service(package, op):
    cmd = ["service", package, op]
    return subprocess.call(cmd)

def populate_initd():
    for name in os.listdir("/var/db/comar3/scripts/System.Service"):
        if not os.path.exists("/etc/init.d/%s" % name[:-3]):
            os.symlink("compat.py", "/etc/init.d/%s" % name[:-3])

if __name__ == "__main__":
    myname = os.path.basename(sys.argv[0])
    if len(sys.argv) == 2:
        sys.exit(wrap_service(myname, sys.argv[1]))
    elif myname == "compat.py" and os.getuid() == 0:
        populate_initd()

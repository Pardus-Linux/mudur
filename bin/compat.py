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

if __name__ == "__main__":
    sys.exit(wrap_service(os.path.basename(sys.argv[0]), sys.argv[1]))

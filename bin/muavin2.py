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
import re


class Modalias:
    def _getAliases(self):
        aliases = []
        for root, dirs, files in os.walk("/sys", topdown=False):
            if "modalias" in files:
                path = os.path.join(root, "modalias")
                aliases.append(file(path).read().rstrip("\n"))
        return aliases
    
    def _match(self, match, alias, mod):
        # bu garip fonksiyon pythonun re ve fnmatch modullerinin
        # acayip yavas olmasindan turedi, 5 sn yerine 0.5 saniyede
        # islememizi sagliyor
        # C library deki fnmatch'i direk kullanabilsek daha hizli
        # ve temiz olacak bu isler
        i = 0
        while True:
            if i >= len(match):
                return alias == ""
            part = match[i]
            if not alias.startswith(part):
                return False
            alias = alias[len(part):]
            i += 1
            if i >= len(match):
                return alias == ""
            part = match[i]
            if part == "" and i + 1 == len(match):
                return True
            j = alias.find(part)
            if j == -1:
                return False
            alias = alias[j:]
    
    def _getModules(self, aliases):
        modules = set()
        path = "/lib/modules/%s/modules.alias" % os.uname()[2]
        for line in file(path):
            try:
                cmd, match, mod = line.split()
            except ValueError:
                continue
            a = match.split("*")
            for alias in aliases:
                if self._match(a, alias, mod):
                    modules.add(mod)
        return modules
    
    def coldDevices(self):
        aliases = self._getAliases()
        modules = self._getModules(aliases)
        for mod in modules:
            print mod


a = Modalias()
a.coldDevices()

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2010 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import sys
import os
import glob
import shutil
import parser

version = "4.1.4"

distfiles = """
    setup.py
    bin/*.py
    etc/mudur.conf
    po/mudur.pot
    po/*.po
"""

i18n_source_list = ["bin/mudur.py", "bin/service.py"]

def update_messages():
    os.system("xgettext -o po/mudur.pot %s" % " ".join(i18n_source_list))
    for item in os.listdir("po"):
        if item.endswith(".po"):
            os.system("msgmerge -q -o temp.po po/%s po/mudur.pot" % item)
            os.system("cp temp.po po/%s" % item)
    os.system("rm -f temp.po")

def make_dist():
    distdir = "mudur-%s" % version
    list = []
    for t in distfiles.split():
        list.extend(glob.glob(t))
    if os.path.exists(distdir):
        shutil.rmtree(distdir)
    os.mkdir(distdir)
    for file_ in list:
        cum = distdir[:]
        for d in os.path.dirname(file_).split('/'):
            dn = os.path.join(cum, d)
            cum = dn[:]
            if not os.path.exists(dn):
                os.mkdir(dn)
        shutil.copy(file_, os.path.join(distdir, file_))
    os.popen("tar -cjf %s %s" % ("mudur-" + version + ".tar.bz2", distdir))
    shutil.rmtree(distdir)

def install_file(source, prefix, dest):
    dest = os.path.join(prefix, dest)
    if os.path.islink(dest):
        os.unlink(dest)
    try:
        os.makedirs(os.path.dirname(dest))
    except:
        pass
    print "installing '%s' to '%s'" % (source, dest)
    os.system("cp %s %s" % (source, dest))

def install(args):
    if args == []:
        prefix = "/"
    else:
        prefix = args[0]

    # Make sure that there isn't a syntax error in mudur.py
    code = file("bin/mudur.py").read()
    parser.suite(code).compile()

    install_file("bin/mudur.py", prefix, "sbin/mudur.py")
    install_file("bin/update-environment.py", prefix, "sbin/update-environment")
    install_file("bin/update-fstab.py", prefix, "sbin/update-fstab")
    install_file("bin/compat.py", prefix, "etc/init.d/compat.py")
    install_file("bin/service.py", prefix, "bin/service")
    install_file("bin/adduser.py", prefix, "sbin/adduser")
    install_file("bin/deluser.py", prefix, "sbin/deluser")
    install_file("etc/mudur.conf", prefix, "etc/conf.d/mudur")

    for item in os.listdir("po"):
        if item.endswith(".po"):
            lang = item[:-3]
            dest = "usr/share/locale/%s/LC_MESSAGES/mudur.mo" % lang
            try:
                os.makedirs(os.path.dirname(os.path.join(prefix, dest)))
            except:
                pass
            path = os.path.join(prefix, dest)
            print "compiling '%s' translation '%s'" % (lang, path)
            os.system("msgfmt po/%s -o %s" % (item, path))

def usage():
    print "setup.py install [prefix]"
    print "setup.py update_messages"
    print "setup.py dist"

def do_setup(args):
    if args == []:
        usage()

    elif args[0] == "install":
        install(args[1:])

    elif args[0] == "update_messages":
        update_messages()

    elif args[0] == "dist":
        make_dist()

    else:
        usage()

if __name__ == "__main__":
    do_setup(sys.argv[1:])

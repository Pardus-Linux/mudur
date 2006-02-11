#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Pardus boot and initialization system
# Copyright (C) 2006, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import sys
import comar

# Utilities

def comlink():
    return comar.Link()

def collect(c):
    reply = c.read_cmd()
    if reply[0] == c.RESULT_START:
        replies = []
        while True:
            reply = c.read_cmd()
            if reply[0] == c.RESULT_END:
                return replies
            replies.append(reply)
    else:
        return [reply]

# Operations

def list():
    c = comlink()
    c.call("System.Service.info")
    data = collect(c)
    services = filter(lambda x: x[0] == c.RESULT, data)
    errors = filter(lambda x: x[0] != c.RESULT, data)
    
    size = max(map(lambda x: len(x[3]), services))
    
    for item in services:
        info = item[2].split("\n")
        print item[3].ljust(size), info[0].ljust(6), info[1].ljust(3), info[2]

# Usage

def usage():
    print "usage: service command [options]"
    print "commands:"
    print " list"

# Main

def main(args):
    if args == []:
        list()
    
    elif args[0] == "list":
        list()
    
    elif args[0] == "help":
        usage()
    
    else:
        usage()

#

if __name__ == "__main__":
    main(sys.argv[1:])

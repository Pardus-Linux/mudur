#!/bin/bash
hav register System.Service dbus dbus-serv.py
hav register System.Service hal hald-serv.py
hav register System.Service xorg xdm-serv.py
hav register System.Service alsa-utils alsa-serv.py
hav register System.Service openssh ssh-serv.py
hav register System.Service zemberek-server zemberek-serv.py
hav register System.Service hotplug coldplug-serv.py
cp mudur.py /sbin/mudur.py

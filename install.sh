#!/bin/bash
hav register System.Service acpid `pwd`/acpid-serv.py
hav register System.Service alsa-utils `pwd`/alsa-serv.py
hav register System.Service cpufreqd `pwd`/cpufreqd-serv.py
hav register System.Service cupsd `pwd`/cupsd-serv.py
hav register System.Service dbus `pwd`/dbus-serv.py
hav register System.Service hal `pwd`/hald-serv.py
hav register System.Service hotplug `pwd`/coldplug-serv.py
hav register System.Service local `pwd`/local-serv.py
hav register System.Service openssh `pwd`/ssh-serv.py
hav register System.Service xorg `pwd`/xdm-serv.py
hav register System.Service zemberek-server `pwd`/zemberek-serv.py
cp mudur.py /sbin/mudur.py

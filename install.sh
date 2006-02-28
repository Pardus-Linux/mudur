#!/bin/bash
hav register System.Service acpid `pwd`/scripts/acpid-serv.py
hav register System.Service alsa-utils `pwd`/scripts/alsa-serv.py
hav register System.Service cpufreqd `pwd`/scripts/cpufreqd-serv.py
hav register System.Service cups `pwd`/scripts/cupsd-serv.py
hav register System.Service cron `pwd`/scripts/cron-serv.py
hav register System.Service dbus `pwd`/scripts/dbus-serv.py
hav register System.Service hal `pwd`/scripts/hald-serv.py
hav register System.Service hotplug `pwd`/scripts/coldplug-serv.py
hav register System.Service local `pwd`/scripts/local-serv.py
hav register System.Service mdnsd `pwd`/scripts/mdnsd-serv.py
hav register System.Service sysklogd `pwd`/scripts/sysklogd-serv.py
hav register System.Service openssh `pwd`/scripts/ssh-serv.py
hav register System.Service xorg `pwd`/scripts/xdm-serv.py
hav register System.Service zemberek-server `pwd`/scripts/zemberek-serv.py
cp mudur.py /sbin/mudur.py
cp service.py /bin/service

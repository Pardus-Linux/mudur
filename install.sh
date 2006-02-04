#!/bin/bash
hav register System.Service dbus /home/gurer/pardus/uludag/trunk/comar/mudur/dbus-serv.py
hav register System.Service hal /home/gurer/pardus/uludag/trunk/comar/mudur/hald-serv.py
hav register System.Service xorg /home/gurer/pardus/uludag/trunk/comar/mudur/xdm-serv.py
hav register System.Service alsa-utils /home/gurer/pardus/uludag/trunk/comar/mudur/alsa-serv.py
hav register System.Service openssh /home/gurer/pardus/uludag/trunk/comar/mudur/ssh-serv.py
hav register System.Service zemberek-server /home/gurer/pardus/uludag/trunk/comar/mudur/zemberek-serv.py
hav register System.Service hotplug /home/gurer/pardus/uludag/trunk/comar/mudur/coldplug-serv.py
cp mudur.py /sbin/mudur.py

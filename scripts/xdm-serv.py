from comar.service import *
import os

def ensureDirs(path):
    """Create missing directories in the path"""
    if not os.path.exists(path):
        os.makedirs(path)

def write(filename, data):
    """Write data to file"""
    f = file(filename, "w")
    f.write(data)

def configure():
    if not os.path.exists("/etc/X11/xorg.conf"):
        run("/sbin/xorg.py")
   
    # FIXME: change startDM.sh in xorg package
    ensureDirs("/var/lib/init.d/options/xdm")
    write("/var/lib/init.d/options/xdm/service", "/usr/kde/3.5/bin/kdm")

def start():
    configure()
    run("/sbin/telinit a")

def stop():
    run("/sbin/start-stop-daemon --stop --quiet --exe /usr/kde/3.5/bin/kdm")

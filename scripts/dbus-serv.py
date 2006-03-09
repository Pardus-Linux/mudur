from comar.service import *
import os

serviceType = "server"
serviceDesc = "DBUS Message Bus"

def unlink(path):
    try:
        os.unlink(path)
    except:
        pass

def start():
    run("/sbin/start-stop-daemon --start --pidfile /var/run/dbus.pid --exec /usr/bin/dbus-daemon-1 -- --system")

def stop():
    run("/sbin/start-stop-daemon --stop --pidfile /var/run/dbus.pid")
    unlink("/var/run/dbus.pid")

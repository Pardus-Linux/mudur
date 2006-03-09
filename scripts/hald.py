from comar.service import *
import os
import time
import socket

serviceType = "local"
serviceDesc = "Hald"

def wait_for_bus(unix_name, retry=10, wait=0.2):
    sock = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    count = 0
    while count < retry:
        try:
            sock.connect(unix_name)
            return True
        except:
            count += 1
        time.sleep(wait)
    return False

def start():
    call("System.Service.start", "dbus")
    call("System.Service.start", "acpid")
    wait_for_bus("/var/lib/dbus/system_bus_socket")
    run("/sbin/start-stop-daemon --start -q --exec /usr/sbin/hald -- --retain-privileges")

def stop():
    run("/sbin/start-stop-daemon --stop -q --pidfile /var/run/hald.pid")

import os
from comar.service import *

def start():
    call("System.Service.start", "sysklogd")
    run("/sbin/start-stop-daemon --start -q --pidfile /var/run/mdnsd.pid --exec /usr/sbin/mdnsd")

def stop():
    run("/sbin/start-stop-daemon --stop -q --pidfile /var/run/mdnsd.pid")

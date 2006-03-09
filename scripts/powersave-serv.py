import os
from comar.service import *

serviceType = "server"
serviceDesc = "Powersave"

def start():
    call("System.Service.start", "hald")
    run("/sbin/start-stop-daemon --start -q --exec /usr/sbin/powersaved -- -f /etc/acpi/events -d")

def stop():
    run("/sbin/start-stop-daemon --stop -q --exec /usr/sbin/powersaved")

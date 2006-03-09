from comar.service import *
import os

serviceType = "local"
serviceDesc = "ACPID"

def check_config():
    if not os.path.exists("/proc/acpi"):
        fail("ACPI support has not been compiled into the kernel")

def start():
    check_config()
    run("/sbin/start-stop-daemon --start --quiet --exec /usr/sbin/acpid -- -c /etc/acpi/events")

def stop():
    run("/sbin/start-stop-daemon --stop --quiet --exec /usr/sbin/acpid")

def reload():
    run("/sbin/start-stop-daemon --stop --quiet --exec /usr/sbin/acpid --signal HUP")

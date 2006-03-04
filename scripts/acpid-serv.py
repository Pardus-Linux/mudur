
import os
import subprocess

def run(*cmd):
    """Run a command without running a shell"""
    return subprocess.call(cmd)

#

def check_config():
    if not os.path.exists("/proc/acpi"):
        fail("ACPI support has not been compiled into the kernel")
#

def get_state():
    s = get_profile("System.Service.setState")
    if s:
        state = s["state"]
    else:
        state = "on"
    
    return state

#

def info():
    state = get_state()
    return "local\n" + state + "\nACPID"

def start():
    check_config()
    run("/sbin/start-stop-daemon", "--start", "--quiet", "--exec", "/usr/sbin/acpid", "--", "-c", "/etc/acpi/events")

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--quiet", "--exec", "/usr/sbin/acpid")

#FIXME: Gürer reload ekleyince
#def reload():
#    run("/sbin/start-stop-daemon", "--stop", "--quiet", "--exec", "/usr/sbin/acpid", "--signal", "HUP")

def ready():
    s = get_state()
    if s == "on":
        start()

def setState(state=None):
    if state == "on":
        start()
    elif state == "off":
        stop()
    else:
        fail("Unknown state '%s'" % state)

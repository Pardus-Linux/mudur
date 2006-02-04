
import os
import subprocess

def unlink(path):
    try:
        os.unlink(path)
    except:
        pass

def run(*cmd):
    """Run a command without running a shell"""
    return subprocess.call(cmd)

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
    return "local\n" + state + "\nD-BUS System Messagebus"

def start():
    run("/sbin/start-stop-daemon", "--start", "--pidfile",
        "/var/run/dbus.pid", "--exec", "/usr/bin/dbus-daemon-1",
        "--", "--system")

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--pidfile", "/var/run/dbus.pid")
    unlink("/var/run/dbus.pid")

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

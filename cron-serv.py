import os
import subprocess

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
    return "local\n" + state + "\nVixie Cron"

def start():
    run("start-stop-daemon", "--start", "--quiet", "--exec", "/usr/sbin/cron")

def stop():
    run("start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/cron.pid")
    
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

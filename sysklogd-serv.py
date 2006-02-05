import os
import time
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
    return "local\n" + state + "\nLogger"

def start():
    run("start-stop-daemon", "--start", "--quiet", "--background", "--exec", "/usr/sbin/syslogd", "--", "-m", "15")

    # klogd do not always start proper if started too early
    time.sleep(1)
    run("start-stop-daemon", "--start", "--quiet", "--background", "--exec", "/usr/sbin/klogd", "--", "-c", "3", "-2")
            
def stop():
    run("start-stop-daemon", "--stop" "--oknodo", "--retry", "15", "--quiet", "--pidfile", "/var/run/klogd.pid")
    run("start-stop-daemon", "--stop", "--oknodo", "--retry", "15", "--quiet", "--pidfile", "/var/run/syslogd.pid")
            
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

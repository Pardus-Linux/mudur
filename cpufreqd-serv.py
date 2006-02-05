
import os
import subprocess

def run(*cmd):
    """Run a command without running a shell"""
    return subprocess.call(cmd)

#

def check_config():
    if not os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq"):
        fail("CPUFreq support has not been compiled into the kernel")
#

def get_state():
    s = get_profile("System.Service.setState")
    if s:
        state = s["state"]
    else:
        state = "off"
    
    return state

#

def info():
    state = get_state()
    return "local\n" + state + "\nCPU Freqd"

def start():
    check_config()
    run("/sbin/start-stop-daemon", "--start", "--quiet", "--exec", "/usr/sbin/cpufreqd")

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--quiet", "--exec", "/usr/sbin/cpufreqd")

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

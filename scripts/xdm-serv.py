
import os
import subprocess

def run(*cmd):
    """Run a command without running a shell"""
    return subprocess.call(cmd)

def ensureDirs(path):
    """Create missing directories in the path"""
    if not os.path.exists(path):
        os.makedirs(path)

def write(filename, data):
    """Write data to file"""
    f = file(filename, "w")
    f.write(data)
    f.close()

#

def configure():
    if not os.path.exists("/etc/X11/xorg.conf"):
        run("/sbin/xorg.py")
   
    # FIXME: change startDM.sh in xorg package
    ensureDirs("/var/lib/init.d/options/xdm")
    write("/var/lib/init.d/options/xdm/service", "/usr/kde/3.5/bin/kdm")

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
    return "local\n" + state + "\nX Window System"

def start():
    configure()
    run("/sbin/telinit", "a")

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--quiet",
        "--exe", "/usr/kde/3.5/bin/kdm")

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

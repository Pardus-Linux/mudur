
import os
import subprocess

#

cfg_file = "/etc/asound.state"

#

oss_modules = [
"snd-seq-oss",
"snd-pcm-oss",
"snd-mixer-oss"
]

def run(*cmd):
    """Run a command without running a shell"""
    return subprocess.call(cmd)

def capture(*cmd):
    """Capture the output of command without running a shell"""
    a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return a.communicate()

#

def get_state():
    s = get_profile("System.Service.setState")
    if s:
        state = s["state"]
    else:
        state = "on"
    
    return state

def load_oss_support():
    for drv in oss_modules:
        run("/sbin/modprobe", drv)

def restore_mixer():
    if os.path.exists(cfg_file):
        run("/usr/sbin/alsactl", "-f", cfg_file, "restore", "0")
    else:
        for a in capture("/usr/bin/amixer", "scontrols")[0].split("\n"):
            # strange, but "a" may not exist
            if a:
                run("/usr/bin/amixer", "-q", "set", a.split("'")[1], "75%", "unmute")

def save_mixer():
    if os.path.exists("/usr/sbin/alsactl"):
        run("/usr/sbin/alsactl", "-f", cfg_file, "store")

#

def info():
    state = get_state()
    return "script\n" + state + "\nAdvanced Linux Sound System"

def start():
    load_oss_support()
    restore_mixer()

def stop():
    save_mixer()

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

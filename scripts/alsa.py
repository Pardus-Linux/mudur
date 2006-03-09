from comar.service import *
import os

serviceType = "local"
serviceDesc = "Alsa"

cfg_file = "/etc/asound.state"

oss_modules = [
"snd-seq-oss",
"snd-pcm-oss",
"snd-mixer-oss"
]

def capture(*cmd):  
    # FIXME: delete when api has capture func.
    import subprocess
    """Capture the output of command without running a shell"""
    a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return a.communicate()

def load_oss_support():
    for drv in oss_modules:
        run("/sbin/modprobe", drv)

def restore_mixer():
    if os.path.exists(cfg_file):
        run("/usr/sbin/alsactl -f %s restore 0" % cfg_file)
    else:
        for a in capture("/usr/bin/amixer", "scontrols")[0].split("\n"):
            # strange, but "a" may not exist
            if a:
                run("/usr/bin/amixer -q set %s 75% unmute" % a.split("'")[1])

def save_mixer():
    if os.path.exists("/usr/sbin/alsactl"):
        run("/usr/sbin/alsactl", "-f", cfg_file, "store")

def start():
    load_oss_support()
    restore_mixer()

def stop():
    save_mixer()

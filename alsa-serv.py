
import os
import subprocess

#

cfg_file = "/etc/asound.state"

#

alsa_drivers = [
"snd_ad1889",
"snd_ali5451",
"snd_als4000",
"snd_asihpi",
"snd_atiixp",
"snd_atiixp_modem",
"snd_au8810",
"snd_au8820",
"snd_au8830",
"snd_azt3328",
"snd_bt87x",
"snd_ca0106",
"snd_cmipci",
"snd_cs4281",
"snd_cs46xx",
"snd_darla20",
"snd_darla24",
"snd_echo3g",
"snd_emu10k1",
"snd_emu10k1x",
"snd_ens1370",
"snd_ens1371",
"snd_es1938",
"snd_es1968",
"snd_fm801",
"snd_gina20",
"snd_gina24",
"snd_hda_intel",
"snd_hdsp",
"snd_hdspm",
"snd_ice1712",
"snd_ice1724",
"snd_indigo",
"snd_indigodj",
"snd_indigoio",
"snd_intel8x0",
"snd_intel8x0m",
"snd_korg1212",
"snd_layla20",
"snd_layla24",
"snd_maestro3",
"snd_mia",
"snd_mixart",
"snd_mona",
"snd_nm256",
"snd_pcxhr",
"snd_riptide",
"snd_rme32",
"snd_rme96",
"snd_rme9652",
"snd_sonicvibes",
"snd_trident",
"snd_via82xx",
"snd_via82xx_modem",
"snd_vx222",
"snd_ymfpci"
]

oss_modules = [
"snd-seq-oss",
"snd-pcm-oss",
"snd-mixer-oss"
]

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

def load_modules():
    for drv in alsa_drivers:
        run("/sbin/modprobe", drv)

def load_oss_support():
    for drv in oss_modules:
        run("/sbin/modprobe", drv)

def restore_mixer():
    if os.path.exists(cfg_file):
        run("/usr/sbin/alsactl", "-f", cfg_file, "restore", "0")
    else:
        run("/usr/bin/amixer", "-q", "set", "Master", "75%", "unmute")
        run("/usr/bin/amixer", "-q", "set", "PCM", "75%", "unmute")
        run("/usr/bin/amixer", "-q", "set", "CD", "75%", "unmute")
        run("/usr/bin/amixer", "-q", "set", "Line", "75%", "unmute")
        run("/usr/bin/amixer", "-q", "set", "Mic", "75%", "unmute")

def save_mixer():
    if os.path.exists("/usr/sbin/alsactl"):
        run("/usr/sbin/alsactl", "-f", cfg_file, "store")

#

def info():
    state = get_state()
    return "script\n" + state + "\nAdvanced Linux Sound System"

def start():
    #FIXME: Use discover
    load_modules()
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

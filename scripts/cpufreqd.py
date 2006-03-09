from comar.service import *
import os

serviceType = "local"
serviceDesc = "CpuFreqd"

def check_config():
    if not os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq"):
        fail("CPUFreq support has not been compiled into the kernel")

def start():
    check_config()
    run("/sbin/start-stop-daemon --start --quiet --exec /usr/sbin/cpufreqd")

def stop():
    run("/sbin/start-stop-daemon --stop --quiet --exec /usr/sbin/cpufreqd")

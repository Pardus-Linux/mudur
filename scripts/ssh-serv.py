
import os
import subprocess

def run(*cmd):
    """Run a command without running a shell"""
    return subprocess.call(cmd)

#

def check_config():
    if not os.path.exists("/etc/ssh/sshd_config"):
        fail("You need /etc/ssh/sshd_config to run sshd")
    
    if not os.path.exists("/etc/ssh/ssh_host_key"):
        run("/usr/bin/ssh-keygen", "-t", "rsa1", "-b", "1024",
            "-f", "/etc/ssh/ssh_host_key", "-N", "")
    
    if not os.path.exists("/etc/ssh/ssh_host_dsa_key"):
        run("/usr/bin/ssh-keygen", "-d", "-f",
            "/etc/ssh/ssh_host_dsa_key", "-N", "")
    
    if not os.path.exists("/etc/ssh/ssh_host_rsa_key"):
        run("/usr/bin/ssh-keygen", "-t", "rsa",
            "-f", "/etc/ssh/ssh_host_rsa_key", "-N", "")

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
    return "server\n" + state + "\nSecure Shell Server"

def start():
    check_config()
    run("/sbin/start-stop-daemon", "--start", "--quiet",
        "--pidfile", "/var/run/sshd.pid",
        "--startas", "/usr/sbin/sshd")

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--quiet",
        "--pidfile", "/var/run/sshd.pid")

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

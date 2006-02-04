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
    return "local\n" + state + "\nZemberek Spell Checker"

def start():
    os.chdir("/opt/zemberek-server")
    os.system("source /etc/profile; export LC_ALL=tr_TR.UTF-8; " +
        "/sbin/start-stop-daemon -b --start --quiet --pidfile " +
        "/var/run/zemberek.pid --make-pidfile --exec ${JAVA_HOME}/bin/java " +
        "-- -jar zemberek_server-0.3.jar >/dev/null"
    )

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/zemberek.pid")

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

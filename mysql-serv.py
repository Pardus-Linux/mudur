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
        state = "off"
    return state
#
def info():
    state = get_state()
    return "server\n" + state + "\nMySQL DB Server"

def start():
    run("/sbin/start-stop-daemon", "--start", "--quiet", "--background", "--exec", "/usr/bin/mysqld_safe", "--", "--user=mysql", "--basedir=/usr", "--datadir=/var/lib/mysql", \
        "--max_allowed_packet=8M", "--net_buffer_length=16K", "--socket=/var/run/mysqld/mysqld.sock", "--pid-file=/var/run/mysqld/mysqld.pid")

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--retry", "5", "--quiet", "--pidfile=/var/run/mysqld/mysqld.pid")

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

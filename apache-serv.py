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
    return "server\n" + state + "\nApache Web Server"

def start():
    run("/usr/sbin/apachec2tl", "-d", "/usr/lib/apache2/", "-f", "/etc/apache2/httpd.conf", get_config_vars(), "-k", "start")

def stop():
    run("/usr/sbin/apachec2tl", "-d", "/usr/lib/apache2/", "-f", "/etc/apache2/httpd.conf", get_config_vars(), "-k", "stop")

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

def get_config_vars():
    return map(lambda x: x.split('=')[1].strip().strip('"'), [line for line in open('/etc/conf.d/apache2').readlines() if line.strip().startswith('APACHE2_OPTS')])[0]

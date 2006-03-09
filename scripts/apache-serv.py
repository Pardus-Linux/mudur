import os
from comar.service import *

serviceType = "server"
serviceDesc = "Apache Web Server"

def check_apache():
    if not os.path.exists("/etc/apache2"):
        fail("apache2 is not installed.")

def check_config():
    if not os.path.exists("/etc/apache2/httpd.conf"):
        fail("apache2 configuration file (httpd.conf) not exists")

def start():
    check_apache()
    check_config()
    run("/usr/sbin/apache2ctl", "-d", "/usr/lib/apache2/", "-f", "/etc/apache2/httpd.conf", get_config_vars(), "-k", "start")

def stop():
    run("/usr/sbin/apache2ctl", "-d", "/usr/lib/apache2/", "-f", "/etc/apache2/httpd.conf", get_config_vars(), "-k", "stop")

def get_config_vars():
    return map(lambda x: x.split('=')[1].strip().strip('"'), [line for line in open('/etc/conf.d/apache2').readlines() if line.strip().startswith('APACHE2_OPTS')])[0]

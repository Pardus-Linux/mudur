import os
import time
from comar.service import *

serviceType = "server"
serviceDesc = "System Logger"

def start():
    run("start-stop-daemon --start --quiet --background --exec /usr/sbin/syslogd -- -m 15")

    # klogd do not always start proper if started too early
    time.sleep(1)
    run("start-stop-daemon --start --quiet --background --exec /usr/sbin/klogd -- -c 3 -2")
            
def stop():
    run("start-stop-daemon --stop --oknodo --retry 15 --quiet --pidfile /var/run/klogd.pid")
    run("start-stop-daemon --stop --oknodo --retry 15 --quiet --pidfile /var/run/syslogd.pid")

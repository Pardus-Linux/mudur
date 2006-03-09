import os
from comar.service import *


serviceType = "local"
serviceDesc = "Zemberek Spell Checker"

def start():
    os.chdir("/opt/zemberek-server")
    os.system("source /etc/profile.env; export LC_ALL=tr_TR.UTF-8; " +
        "/sbin/start-stop-daemon -b --start --quiet --pidfile " +
        "/var/run/zemberek.pid --make-pidfile --exec ${JAVA_HOME}/bin/java " +
        "-- -jar zemberek_server-0.3.jar >/dev/null"
    )

def stop():
    run("/sbin/start-stop-daemon", "--stop", "--quiet", "--pidfile", "/var/run/zemberek.pid")

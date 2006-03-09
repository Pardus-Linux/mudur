from comar.service import *

serviceType = "local"
serviceDesc = "Cron"

def start():
    run("start-stop-daemon --start --quiet --exec /usr/sbin/cron")

def stop():
    run("start-stop-daemon --stop --quiet --pidfile /var/run/cron.pid")

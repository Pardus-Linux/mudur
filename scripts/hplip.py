from comar.service import *

serviceType = "local"
serviceDesc = "HP Printer/Scanner Services"

def start():
    run("start-stop-daemon --start --quiet --exec /usr/sbin/hpiod")
    run('start-stop-daemon --quiet --start --exec /usr/share/hplip/hpssd.py --pidfile /var/run/hpssd.pid')

def stop():
    run("start-stop-daemon --stop --quiet -n hpiod")
    run("start-stop-daemon --stop --pidfile /var/run/hpssd.pid")


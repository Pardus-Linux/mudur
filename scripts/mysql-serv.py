from comar.service import *
import os

serviceType="server"
serviceDesc = "MySQL DB Server"

def check_mysql():
    if not os.path.exists("/var/lib/mysql"):
        fail("MySQL is not installed")

    return "server\n" + state + "\nMySQL DB Server"

def start():
    check_mysql()
    run("/sbin/start-stop-daemon --start --quiet --background --exec /usr/bin/mysqld_safe -- --user=mysql \
    --basedir=/usr --datadir=/var/lib/mysql --max_allowed_packet=8M --net_buffer_length=16K \
    --socket=/var/run/mysqld/mysqld.sock --pid-file=/var/run/mysqld/mysqld.pid")

def stop():
    run("/sbin/start-stop-daemon --stop --retry 5 --quiet --pidfile=/var/run/mysqld/mysqld.pid")

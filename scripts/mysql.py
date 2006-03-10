from comar.service import *
import os

serviceType="server"
serviceDesc = "MySQL DB Server"

def check_mysql():
    if not os.path.exists("/var/lib/mysql"):
        fail("MySQL is not installed")

def start():
    check_mysql()
    run("/sbin/start-stop-daemon --start --quiet --background --exec /usr/sbin/mysqld -- \
         --basedir=/usr --datadir=/var/lib/mysql --pid-file=/var/run/mysqld/mysqld.pid \
         --skip-locking --port=3306 --socket=/var/run/mysqld/mysqld.sock --max_allowed_packet=8M \
         --net_buffer_length=16K")

def stop():
    run("/sbin/start-stop-daemon --stop --retry 5 --quiet --pidfile=/var/run/mysqld/mysqld.pid")

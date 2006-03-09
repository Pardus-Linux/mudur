from comar.service import *
import os

serviceType = "local"
serviceDesc = "Custom startup commands"

def start():
    if os.path.exists("/etc/conf.d/local.start"):
        os.system("source /etc/conf.d/local.start")

def stop():
    if os.path.exists("/etc/conf.d/local.stop"):
        os.system("source /etc/conf.d/local.stop")

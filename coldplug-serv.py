import os

#

def get_state():
    s = get_profile("System.Service.setState")
    if s:
        state = s["state"]
    else:
        state = "on"
    
    return state

#

def info():
    state = get_state()
    return "script\n" + state + "\nColdplug Device Drivers"

def start():
    for rc in os.listdir("/etc/hotplug/"):
        if rc.endswith(".rc"):
            os.system(os.path.join("/etc/hotplug", rc) + " start")

def stop():
    pass

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

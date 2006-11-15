/*
** Copyright (c) 2006, TUBITAK/UEKAE
**
** Coldplug program for initrd
** Unfortunately we cant use muavin.py there
**
** This program is free software; you can redistribute it and/or modify it
** under the terms of the GNU General Public License as published by the
** Free Software Foundation; either version 2 of the License, or (at your
** option) any later version. Please read the COPYING file.
*/

#include <stddef.h>
#include <sys/utsname.h>

#include "utility.h"

int pci_probe_modules(const char *mappath);
int usb_probe_modules(const char *mappath);
int scsi_probe_modules(void);
int devnodes_populate(void);

int
main(int argc, char *argv[])
{
	struct utsname name;
	char *mappath;

	uname(&name);
	mappath = concat("/lib/modules/", name.release);
	mappath = concat(mappath, "/modules.alias");
//	pci_probe_modules(concat(mappath, "/modules.pcimap"));
//	usb_probe_modules(concat(mappath, "/modules.usbmap"));
//	scsi_probe_modules();
load_modules(mappath, "/sys/bus/pci/devices/");
load_modules(mappath, "/sys/bus/usb/devices/");
//	devnodes_populate();

	return 0;
}

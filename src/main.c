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

#include <unistd.h>
#include "common.h"

int cfg_debug = 0;

int
main(int argc, char *argv[])
{
	struct list *modules;
	struct list *item;
	int has_scsi_storage = 0;

	if (argc == 2 && strcmp(argv[1], "--debug") == 0)
		cfg_debug = 1;

	// First, load PCI modules
	modules = module_get_list("/sys/bus/pci/devices/");
	for (item = modules; item; item = item->next)
		module_probe(item->data);

	// Second, load USB modules
	modules = module_get_list("/sys/bus/usb/devices/");
	if (list_has(modules, "usb_storage"))
		has_scsi_storage = 1;
	for (item = modules; item; item = item->next)
		module_probe(item->data);

	// Then, check if there is a need for scsi disk/cdrom drivers
	// If these are on usb bus, they need some time to properly
	// setup, so we wait a little bit.
	if (has_scsi_storage) {
		sleep(2);
	}
	modules = scsi_get_list();
	for (item = modules; item; item = item->next)
		module_probe(item->data);

	// Populate /dev directory for probed disk/cdrom devices
	// Again, wait a bit for devices to settle
	if (has_scsi_storage) {
		sleep(1);
	}
	devnode_populate();

	return 0;
}

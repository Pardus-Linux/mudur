/*
** Copyright (c) 2006, TUBITAK/UEKAE
**
** This program is free software; you can redistribute it and/or modify it
** under the terms of the GNU General Public License as published by the
** Free Software Foundation; either version 2 of the License, or (at your
** option) any later version. Please read the COPYING file.
*/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <dirent.h>
#include <sys/stat.h>

#include "utility.h"

struct pci_device {
	struct pci_device *next;
	unsigned int vendor;
	unsigned int device;
	unsigned int subvendor;
	unsigned int subdevice;
	unsigned int class;
};

struct pci_device *
pci_probe_device(const char *name)
{
	char *path;
	struct pci_device *dev;

	path = concat("/sys/bus/pci/devices/", name);
	dev = zalloc(sizeof(struct pci_device));
	dev->vendor = strtoul(sys_value(path, "vendor"), NULL, 16);
	dev->device = strtoul(sys_value(path, "device"), NULL, 16);
	dev->subvendor = strtoul(sys_value(path, "subsystem_vendor"), NULL, 16);
	dev->subdevice = strtoul(sys_value(path, "subsystem_device"), NULL, 16);
	dev->class = strtoul(sys_value(path, "class"), NULL, 16);

	return dev;
}

int
pci_probe_modules(const char *mapname)
{
	FILE *f;
	DIR *dir;
	struct dirent *dirent;
	struct modlist *modules = NULL;
	struct pci_device *devices = NULL;
	struct pci_device *dev;
	char line[256];

	dir = opendir("/sys/bus/pci/devices");
	if (!dir) return -1;
	while((dirent = readdir(dir))) {
		char *name = dirent->d_name;
		if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
			continue;

		dev = pci_probe_device(name);
		dev->next = devices;
		devices = dev;
	}
	closedir(dir);

	if (!devices) return 0;

	f = fopen(mapname, "r");
	if (!f) return -1;
	while (fgets(line, 255, f)) {
		char *tmp;
		unsigned int vals[6];
		int i;
		if (line[0] == '#' || line[0] == '\n' || line[0] == '\0')
			continue;
		strtok(line, " \t");
		for (i = 0; i < 6; i++) {
			tmp = strtok(NULL, " \t");
			if (!tmp) break;
			vals[i] = strtoul(tmp, NULL, 16);
		}
		if (i != 6) continue;
		for (dev = devices; dev; dev = dev->next) {
			if (vals[0] != 0xffffffff && vals[0] != dev->vendor)
				continue;
			if (vals[1] != 0xffffffff && vals[1] != dev->device)
				continue;
			if (vals[2] != 0xffffffff && vals[2] != dev->subvendor)
				continue;
			if (vals[3] != 0xffffffff && vals[3] != dev->subdevice)
				continue;
			if ((dev->class & vals[5]) != vals[4])
				continue;
			modules = modlist_add(modules, line);
		}
	}
	fclose(f);

	return modlist_probe(modules);
}

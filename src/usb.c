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

struct usb_device {
	struct usb_device *next;
	unsigned int vendor;
	unsigned int product;
	unsigned int device;
	unsigned int dclass;
	unsigned int dsub;
	unsigned int dproto;
	unsigned int iclass;
	unsigned int isub;
	unsigned int iproto;
};

struct usb_device *
usb_probe_device(const char *path)
{
	struct usb_device *dev;

	dev = zalloc(sizeof(struct usb_device));
	dev->vendor = strtoul(sys_value(path, "../idVendor"), NULL, 16);
	dev->product = strtoul(sys_value(path, "../idProduct"), NULL, 16);
	dev->device = strtoul(sys_value(path, "../bcdDevice"), NULL, 16);

	if (sys_value(path, "bDeviceClass")) {
		dev->dclass = strtoul(sys_value(path, "bDeviceClass"), NULL, 16);
		dev->dsub = strtoul(sys_value(path, "bDeviceSubClass"), NULL, 16);
		dev->dproto = strtoul(sys_value(path, "bDeviceProtocol"), NULL, 16);
	} else {
		dev->dclass = 0x1000;
		dev->dsub = 0x1000;
		dev->dproto = 0x1000;
	}

	if (sys_value(path, "bInterfaceClass")) {
		dev->iclass = strtoul(sys_value(path, "bInterfaceClass"), NULL, 16);
		dev->isub = strtoul(sys_value(path, "bInterfaceSubClass"), NULL, 16);
		dev->iproto = strtoul(sys_value(path, "bInterfaceProtocol"), NULL, 16);
	} else {
		dev->iclass = 0x1000;
		dev->isub = 0x1000;
		dev->iproto = 0x1000;
	}

	return dev;
}

int
usb_probe_modules(const char *mapname)
{
	FILE *f;
	DIR *dir;
	struct dirent *dirent;
	struct modlist *modules = NULL;
	struct usb_device *devices = NULL;
	struct usb_device *dev;
	char line[256];

	dir = opendir("/sys/bus/usb/devices");
	if (!dir) return -1;
	while((dirent = readdir(dir))) {
		char *path;
		char *name = dirent->d_name;
		if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
			continue;
		if (name[0] < '0' || name[0] > '9')
			continue;
		path = concat("/sys/bus/usb/devices/", name);
		path = my_readlink(path);
		if (sys_value(path, "../idVendor")) {
			dev = usb_probe_device(path);
			dev->next = devices;
			devices = dev;
		}
	}
	closedir(dir);

	if (!devices) return 0;

	f = fopen(mapname, "r");
	if (!f) return -1;
	while (fgets(line, 255, f)) {
		char *tmp;
		unsigned int flags;
		unsigned int vals[10];
		int i;
		if (line[0] == '#' || line[0] == '\n' || line[0] == '\0')
			continue;
		strtok(line, " \t");
		tmp = strtok(NULL, " \t");
		while (tmp != NULL && tmp[0] == '\0')
			tmp = strtok(NULL, " \t");
		if (!tmp) continue;
		flags = strtoul(tmp, NULL, 16);
		for (i = 0; i < 10; i++) {
			tmp = strtok(NULL, " \t");
			while (tmp != NULL && tmp[0] == '\0')
				tmp = strtok(NULL, " \t");
			if (!tmp) break;
			vals[i] = strtoul(tmp, NULL, 16);
		}
		if (i != 10) continue;
		for (dev = devices; dev; dev = dev->next) {
			if (flags & 0x0001 && dev->vendor != vals[0])
				continue;
			if (flags & 0x0002 && dev->product != vals[1])
				continue;
			if (flags & 0x0004 && dev->device < vals[2])
				continue;
			if (flags & 0x0008 && dev->device > vals[3])
				continue;
			if (flags & 0x0010 && dev->dclass != vals[4])
				continue;
			if (flags & 0x0020 && dev->dsub != vals[5])
				continue;
			if (flags & 0x0040 && dev->dproto != vals[6])
				continue;
			if (flags & 0x0080 && dev->iclass != vals[7])
				continue;
			if (flags & 0x0100 && dev->isub != vals[8])
				continue;
			if (flags & 0x0200 && dev->iproto != vals[9])
				continue;
			modules = modlist_add(modules, line);
		}
	}
	fclose(f);

	return modlist_probe(modules);
}

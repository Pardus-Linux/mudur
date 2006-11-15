/*
** Copyright (c) 2006, TUBITAK/UEKAE
**
** This program is free software; you can redistribute it and/or modify it
** under the terms of the GNU General Public License as published by the
** Free Software Foundation; either version 2 of the License, or (at your
** option) any later version. Please read the COPYING file.
*/

#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
#include <sys/stat.h>

#include "common.h"

struct list *
scsi_get_list(void)
{
	DIR *dir;
	struct dirent *dirent;
	struct list *modules = NULL;

	dir = opendir("/sys/bus/scsi/devices");
	if (!dir) return NULL;
	while((dirent = readdir(dir))) {
		char *path;
		char *tmp;
		char *name = dirent->d_name;
		if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
			continue;
		if (name[0] < '0' || name[0] > '9')
			continue;
		path = concat("/sys/bus/scsi/devices/", name);
		path = my_readlink(path);
		tmp = sys_value(path, "type");
		if (tmp) {
			if (strcmp(tmp, "0") == 0 || strcmp(tmp, "7") == 0)
				modules = list_add(modules, "sd_mod");
			if (strcmp(tmp, "1") == 0)
				modules = list_add(modules, "st");
			if (strcmp(tmp, "4") == 0 || strcmp(tmp, "5") == 0)
				modules = list_add(modules, "sr_mod");
		}
	}
	closedir(dir);

	return modules;
}

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

int
devnodes_populate(void)
{
	DIR *dir;
	struct dirent *dirent;
	struct modlist *modules = NULL;

	dir = opendir("/sys/block");
	if (!dir) return -1;
	while((dirent = readdir(dir))) {
		char *path;
		char *tmp;
		char *dev;
		char *major;
		char *minor;
		char *name = dirent->d_name;
		if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0 || strlen(name) < 3)
			continue;
		tmp = NULL;
		if (name[0] == 'h' && name[1] == 'd')
			tmp = name;
		if (name[0] == 's' && name[1] == 'd')
			tmp = name;
		if (name[0] == 's' && name[1] == 'r')
			tmp = name;
		if (tmp) {
			path = concat("/sys/block/", tmp);
			dev = sys_value(path, "dev");
			major = strtok(dev, ":");
			minor = strtok(NULL, "");
			if (minor) {
				char buf[512];
				sprintf(buf, "/bin/mknod /dev/%s b %s %s", tmp, major, minor);
				system(buf);
			}
		}
	}
	closedir(dir);

	return modlist_probe(modules);
}

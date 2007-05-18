/*
** Copyright (c) 2006-2007, TUBITAK/UEKAE
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

static void
ensure_path(char *path)
{
	struct stat fs;
	char *t, *cur;

	path = strdup(path);
	cur = path;
	if (path[0] == '/') ++cur;
	while (1) {
		t = strchr(cur, '/');
		if (!t) break;
		*t = '\0';
		if (stat(path, &fs) != 0) {
			mkdir(path, 0755);
		}
		*t = '/';
		cur = t + 1;
	}
}

int
devnode_mknod(const char *name, const char *major, const char *minor)
{
	struct stat fs;
	char buf[512];
	char *path;
	char *t;

	path = concat("/dev/", name);
	for (t=path; *t != '\0'; t++) {
		 if (*t == '!') *t = '/';
	}

	if (stat(path, &fs) == 0) {
		if (cfg_debug) printf("exists: mknod %s b %s %s\n", path, major, minor);
	} else {
		sprintf(buf, "mknod %s b %s %s", path, major, minor);
		if (cfg_debug)
			puts(buf);
		else {
			ensure_path(path);
			system(buf);
		}
	}
	return 0;
}

static int
mknod_parts(char *dev)
{
	char *path;
	DIR *dir;
	struct dirent *dirent;
	char *tmp;
	char *major;
	char *minor;

	path = concat("/sys/block/", dev);
	dir = opendir(path);
	if (!dir) return -1;
	while((dirent = readdir(dir))) {
		char *name = dirent->d_name;
		if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
			continue;
		if (strncmp(name, dev, strlen(dev)) != 0)
			continue;
		tmp = concat(concat(path, "/"), name);
		tmp = sys_value(tmp, "dev");
		major = strtok(tmp, ":");
		minor = strtok(NULL, "");
		if (minor) devnode_mknod(name, major, minor);
	}
	closedir(dir);
	return 0;
}

int
devnode_populate(void)
{
	DIR *dir;
	struct dirent *dirent;

	dir = opendir("/sys/block");
	if (!dir) return -1;
	while((dirent = readdir(dir))) {
		char *path;
		char *dev;
		char *major;
		char *minor;
		char *name = dirent->d_name;
		if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
			continue;
		
		path = concat("/sys/block/", name);
		dev = sys_value(path, "dev");
		major = strtok(dev, ":");
		minor = strtok(NULL, "");
		if (minor) {
			devnode_mknod(name, major, minor);
			mknod_parts(name);
		}
	}
	closedir(dir);

	return 0;
}

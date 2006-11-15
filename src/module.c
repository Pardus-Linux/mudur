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
#include <unistd.h>
#include <dirent.h>
#include <sys/utsname.h>

#include "common.h"

static struct list *
find_aliases(const char *syspath)
{
	FILE *f;
	DIR *dir;
	struct dirent *dirent;
	struct list *aliases = NULL;
	char modalias[256];
	size_t size;
	char *path;

	dir = opendir(syspath);
	if (!dir) return NULL;
	while((dirent = readdir(dir))) {
		char *name = dirent->d_name;
		if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
			continue;
		path = concat(syspath, name);
		path = concat(path, "/modalias");
		f = fopen(path, "rb");
		if (f) {
			size = fread(modalias, 1, 254, f);
			if (size < 1) return NULL;
			modalias[size] = '\0';
			if (modalias[size-1] == '\n')
				modalias[size-1] = '\0';

			aliases = list_add(aliases, modalias);

			fclose(f);
		}
	}
	closedir(dir);

	return aliases;
}

static struct list *
find_modules(const char *mapfile, struct list *aliases)
{
	FILE *f;
	struct list *modules = NULL;
	struct list *alias;
	char line[256];
	char *modalias, *modname;

	if (!aliases) return NULL;

	f = fopen(mapfile, "rb");
	while (fgets(line, 255, f)) {
		if (line[0] == '#' || line[0] == '\n' || line[0] == '\0')
			continue;
		strtok(line, " \t");
		if (strncmp(line, "alias", 5) != 0)
			continue;

		modalias = strtok(NULL, " \t");
		modname = strtok(NULL, " \t\r\n");

		for (alias = aliases; alias; alias = alias->next) {
			if (0 == fnmatch(modalias, alias->data)) {
				modules = list_add(modules, modname);
			}
		}
	}
	return modules;
}

struct list *
module_get_list(const char *syspath)
{
	struct list *aliases;
	struct utsname name;
	char *mapfile;

	uname(&name);
	mapfile = concat("/lib/modules/", name.release);
	mapfile = concat(mapfile, "/modules.alias");

	aliases = find_aliases(syspath);
	return find_modules(mapfile, aliases);
}

int
module_probe(const char *name)
{
	char *cmd;

	cmd = concat("modprobe ", name);
	if (cfg_debug)
		puts(cmd);
	else
		system(cmd);
	return 0;
}

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

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <dirent.h>

#include "common.h"

struct list {
	struct list *next;
	char *data;
};

struct list *
list_add(struct list *listptr, const char *data)
{
	struct list *tmp;

	// We dont want duplicate module names, etc in our lists
	// Lists arent too big either, so no need to use a hash or something
	for (tmp = listptr; tmp; tmp = tmp->next) {
		if (0 == strcmp(tmp->data, data))
			return listptr;
	}

	tmp = zalloc(sizeof(struct list));
	tmp->next = listptr;
	tmp->data = strdup(data);
	return tmp;
}

struct list *
find_aliases(const char *syspath)
{
	FILE *f;
	DIR *dir;
	struct dirent *dirent;
	char modalias[256];
	size_t size;
	char *path;
	struct list *aliases = NULL;

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

struct list *
find_modules(const char *mapfile, struct list *aliases)
{
	FILE *f;
	struct list *modules = NULL;
	struct list *alias;
	char line[256];
	char *modalias, *modname;

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

int
load_modules(char *mapfile, char *path)
{
	struct list *aliases;

	aliases = find_aliases(path);
	aliases = find_modules(mapfile, aliases);
	while (aliases) {
		printf("la [%s]\n", aliases->data);
		aliases = aliases->next;
	}
	return 0;
}

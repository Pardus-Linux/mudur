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

void *
zalloc(size_t size)
{
	void *ptr = 0;
	// For small allocations we shouldn't really fail
	while (ptr == 0) {
		// we usually need zeroed buffers
		ptr = calloc(1, size);
	}
	return ptr;
}

char *
concat(const char *str, const char *append)
{
	char *buf;
	size_t str_len = strlen(str);
	size_t append_len = strlen(append);

	buf = zalloc(str_len + 1 + append_len);
	memcpy(buf, str, str_len);
	memcpy(buf + str_len, append, append_len);
	buf[str_len + append_len] = '\0';
	return buf;
}

char *
my_readlink(const char *path)
{
	char buf[512];
	size_t size;
	printf("[%s]\n", path);
	size = readlink(path, buf, 510);
	if (size == -1) {
		buf[0] = '\0';
		printf("e[%s]\n", buf);
		return strdup(buf);
	}
	buf[size] = '\0';
	printf("f[%s]\n", buf);
	return strdup(buf);
}

char *
sys_value(const char *path, const char *value)
{
	static char valbuf[32];
	static char *buf = NULL;
	static size_t buf_size = 0;
	FILE *f;
	size_t size;
	size_t path_len = strlen(path);
	size_t value_len = strlen(value);

	size = path_len + value_len + 2;
	if (buf_size < size) {
		free(buf);
		buf = zalloc(size * 2);
		buf_size = size * 2;
	}
	memcpy(buf, path, path_len);
	buf[path_len] = '/';
	memcpy(buf + path_len + 1, value, value_len);
	buf[path_len + 1 + value_len] = '\0';

	f = fopen(buf, "rb");
	if (!f) return NULL;
	size = fread(valbuf, 1, 30, f);
	if (size < 1) {
		fclose(f);
		return NULL;
	}
	fclose(f);
	valbuf[30] = '\0';
	if (valbuf[size-1] == '\n')
		valbuf[size-1] = '\0';
	return valbuf;
}

struct modlist {
	struct modlist *next;
	char *name;
};

struct modlist *
modlist_add(struct modlist *list, const char *name)
{
	struct modlist *item;

	for (item = list; item; item = item->next) {
		if (strcmp(name, item->name) == 0)
			return list;
	}

	item = zalloc(sizeof(struct modlist));
	item->name = strdup(name);

	item->next = list;
	return item;
}

int
modlist_probe(struct modlist *list)
{
	struct modlist *item;

	for (item = list; item; item = item->next) {
		printf("lala[%s]\n", item->name);
		//system(concat("/sbin/modprobe ", item->name));
	}
	return 0;
}

/*
** Copyright (c) 2006, TUBITAK/UEKAE
**
** This program is free software; you can redistribute it and/or modify it
** under the terms of the GNU General Public License as published by the
** Free Software Foundation; either version 2 of the License, or (at your
** option) any later version. Please read the COPYING file.
*/

void *zalloc(size_t size);
char *concat(const char *str, const char *append);
int fnmatch(const char *p, const char *s);
char *my_readlink(const char *path);
char *sys_value(const char *path, const char *value);

struct modlist;
struct modlist *modlist_add(struct modlist *list, const char *name);
int modlist_probe(struct modlist *list);

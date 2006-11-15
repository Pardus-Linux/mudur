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

#include "common.h"

int
main(int argc, char *argv[])
{
	struct list *modules;

	modules = module_get_list();
	for (; modules; modules = modules->next)
		printf("%s\n", modules->data);

	return 0;
}

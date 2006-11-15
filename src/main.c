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

int cfg_debug = 0;

int
main(int argc, char *argv[])
{
	struct list *modules;
	struct list *item;
cfg_debug = 1;
	modules = module_get_list();
	for (item = modules; item; item = item->next)
		module_probe(item->data);

	modules = scsi_get_list();
	for (item = modules; item; item = item->next)
		module_probe(item->data);

	devnode_populate();

	return 0;
}

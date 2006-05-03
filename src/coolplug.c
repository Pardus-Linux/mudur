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

int pci_probe_modules(const char *mappath);
int usb_probe_modules(const char *mappath);
int scsi_probe_modules(void);
int devnodes_populate(void);

int
main(int argc, char *argv[])
{
	puts("pci");
	pci_probe_modules("/lib/modules/2.6.16.12-37/modules.pcimap");
	puts("usb");
	usb_probe_modules("/lib/modules/2.6.16.12-37/modules.usbmap");
	puts("scsi");
	scsi_probe_modules();

	devnodes_populate();

	return 0;
}


CC= klcc
EXE= coolplug
OBJS= coolplug.c utility.c pci.c usb.c scsi.c devnodes.c
CFLAGS= -Os -Wall
LDFLAGS=

$(EXE): $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(EXE) $(OBJS)
	strip -s --remove-section=.note --remove-section=.comment $(EXE)

clean:
	rm -f $(EXE)

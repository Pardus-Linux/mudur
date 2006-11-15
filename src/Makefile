
CC= klcc
EXE= coolplug
OBJS= main.c utility.c module.c scsi.c devnode.c
INCLUDES= common.h
CFLAGS= -Os -Wall
LDFLAGS=

$(EXE): $(OBJS) $(INCLUDES)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(EXE) $(OBJS)
	strip -s --remove-section=.note --remove-section=.comment $(EXE)

clean:
	rm -f $(EXE)

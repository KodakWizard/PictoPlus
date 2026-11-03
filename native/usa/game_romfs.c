#include <3ds.h>
int picto_mount_game(void){return R_SUCCEEDED(romfsMountFromCurrentProcess("pictogame"));}
void picto_unmount_game(void){romfsUnmount("pictogame");}

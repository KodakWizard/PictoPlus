#include "game_region.h"
/* PictoPlus SD book discovery probe. No game-memory writes. */
#include <3ds.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>

/* Use only the plugin loader's mapped heap, leaving game allocations alone. */
extern char *fake_heap_start, *fake_heap_end;
#ifdef NATIVE_CATALOGUE
/* Streaming buffers can nest during catalogue construction. */
uint32_t __stacksize__ = 128 * 1024;
#endif
void __system_allocateHeaps(void) {
    const uint32_t *header = (const uint32_t *)0x07000000;
    fake_heap_start = (char *)header[2];
    fake_heap_end = fake_heap_start + header[3];
    mappableInit(OS_MAP_AREA_BEGIN,OS_MAP_AREA_END);
}
void _init(void) {}
void _fini(void) {}
void __appInit(void) {
    srvInit();
    fsInit();
    archiveMountSdmc();
}
void __appExit(void) {
    archiveUnmountAll();
    fsExit();
    srvExit();
}

static uint32_t le32(const unsigned char *p) {
    return p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}

static uint32_t checksum(const unsigned char *p, unsigned n) {
    uint32_t crc = ~0u;
    while (n--) {
        crc ^= *p++;
        for (unsigned bit=0; bit<8; bit++) crc = (crc>>1) ^ (0xedb88320u & (0u-(crc&1)));
    }
    return ~crc;
}

#ifdef NATIVE_CATALOGUE
extern int compile_native_books(FILE *log);
extern int install_native_catalogue(FILE *log,int compiled_count);
extern void loader_progress_end(void);
#endif

int prepare_books_main(int argc, char **argv) {
    (void)argc; (void)argv;
    mkdir("sdmc:/PictoPlus", 0777);
    mkdir(PP_SD "Books", 0777);
    FILE *log = fopen(PP_STATE_SD "native-loader-status.txt", "w");
    if (!log) return 1;
    setvbuf(log,NULL,_IONBF,0);
    fputs("DIAGNOSTIC: entered main; SD filesystem mounted. Combined test; preparation deferred until native graphics initialization.\n",log);
#ifdef NATIVE_CATALOGUE
    fputs("PictoPlus native SD catalogue loader v3\n",log);
#else
    fputs("PictoPlus native loader: discovery probe v1\n"
          "This probe reads SD books; it does not add them to the game yet.\n", log);
#endif
    DIR *dir = opendir(PP_SD "Books");
    unsigned accepted=0, rejected=0;
    if (!dir) fputs("Could not open Books folder.\n", log);
    else {
        struct dirent *entry;
        while ((entry=readdir(dir))) {
            size_t len = strlen(entry->d_name);
            if (!((len>=8&&!strcasecmp(entry->d_name+len-8,".voxbook"))||(len>=10&&!strcasecmp(entry->d_name+len-10,".pictobook")))) continue;
            char path[512];
            if (snprintf(path, sizeof(path), PP_SD "Books/%s", entry->d_name) >= sizeof(path)) {
                rejected++; continue;
            }
            FILE *file = fopen(path, "rb");
            unsigned char header[160];
            int valid=0;
            unsigned count=0;
            if (file) {
                fseek(file, 0, SEEK_END);
                long size=ftell(file);
                rewind(file);
                if (fread(header,1,sizeof(header),file)==sizeof(header)) {
                    uint32_t crc=le32(header+136);
                    memset(header+136,0,4);
                    count=header[36] | (unsigned)header[37]<<8;
                    valid = !memcmp(header,"VXBOOK01",8) && le32(header+8)==1 &&
                        le32(header+12)==160 && count>=1 && count<=210 &&
                        header[38]<=1 && header[39]==0 && le32(header+40)==160 &&
                        le32(header+44)==640 && size>=160+count*640 &&
                        size<=256*1024*1024 && le32(header+132)==(uint32_t)size &&
                        checksum(header,160)==crc;
                }
                fclose(file);
            }
            if (valid) {
                accepted++;
                fprintf(log,"FOUND %s: %u puzzles, revision %lu, ID ",entry->d_name,count,(unsigned long)le32(header+32));
                for (unsigned i=16;i<32;i++) fprintf(log,"%02x",header[i]);
                fputc('\n',log);
            } else {rejected++; fprintf(log,"REJECTED %s: unsupported or damaged header\n",entry->d_name);}
        }
        closedir(dir);
    }
    fprintf(log,"Books found: %u; rejected: %u\n",accepted,rejected);
#ifdef NATIVE_CATALOGUE
    fputs("DIAGNOSTIC: starting catalogue compiler.\n",log);
    int count=compile_native_books(log);
    fprintf(log,"DIAGNOSTIC: compiler returned %d. Starting hooks.\n",count);
    int hooks=install_native_catalogue(log,count);
    fprintf(log,"DIAGNOSTIC: hooks returned %d.\n",hooks);
    loader_progress_end();
#endif
    fputs("DIAGNOSTIC: main complete; returning to game startup.\n",log);
    fclose(log);
    return 0;
}

/* Prepare books only after the game's own GSP initialization returns.
 * The one-shot call is restored before executable CRC verification. */
extern void deferred_startup_hook(void);
extern uint32_t deferred_stack;
extern void loader_display_reserve(void);
static uint8_t plugin_thread_state[0x80];
extern void svcFlushEntireDataCache(void),svcInvalidateEntireInstructionCache(void);
int prepare_books_main(int argc,char**argv);
int main(int argc,char**argv){
 mkdir(PP_SD,0777);
#ifdef PICTOPLUS_EUR
 mkdir(PP_STATE_SD,0777);
#endif
 mkdir(PP_SD "Books",0777);
 memcpy(plugin_thread_state,getThreadLocalStorage(),sizeof(plugin_thread_state));
 FILE*f=fopen(PP_STATE_SD "startup-display.txt","w");
 if(f){fputs("EARLY: waiting for native game graphics initialization.\n",f);fclose(f);}
 uint32_t*call=(uint32_t*)PP_STARTUP_CALL;
 int supported=*call==PP_STARTUP_WORD;
#ifdef PICTOPLUS_EUR
 extern int native_game_supported(void);
 supported=supported&&native_game_supported();
#endif
 if(!supported){
  f=fopen(PP_STATE_SD "startup-display.txt","a");
  if(f){fputs("Unsupported startup call; deferred hook not installed.\n",f);fclose(f);}return 0;
 }
 loader_display_reserve();
 /* Reserved executable RO padding, independently checked by the builder. */
 uint32_t*v=(uint32_t*)PP_STARTUP_VENEER;v[0]=0xe51ff004;v[1]=(uint32_t)deferred_startup_hook;
 *call=0xeb000000|(((PP_STARTUP_VENEER-PP_STARTUP_CALL-8)>>2)&0xffffff);
 svcFlushEntireDataCache();svcInvalidateEntireInstructionCache();return 0;
}
void deferred_prepare_books(void){
 uint8_t game_thread_state[0x200];void*tls=getThreadLocalStorage();
 memcpy(game_thread_state,tls,sizeof(game_thread_state));
 memcpy(tls,plugin_thread_state,sizeof(plugin_thread_state));
 *(uint32_t*)PP_STARTUP_CALL=PP_STARTUP_WORD;
 /* Clear the temporary veneer too, before any native patch CRC checks. */
 memset((void*)PP_STARTUP_VENEER,0,8);
 svcFlushEntireDataCache();svcInvalidateEntireInstructionCache();
 FILE*f=fopen(PP_STATE_SD "startup-display.txt","a");
 if(f){fprintf(f,"DEFERRED: native GSP initialization returned; game session %08lx.\n",(unsigned long)*(uint32_t*)PP_GSP_SESSION);fclose(f);}
 prepare_books_main(0,0);
 __appExit();
 memcpy(tls,game_thread_state,sizeof(game_thread_state));
}

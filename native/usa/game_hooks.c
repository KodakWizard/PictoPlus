/* Revision-pinned native SD redirection. No external SAVEDATA access. */
#include <3ds.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "csvc.h"
#include "paging_payloads.h"

extern void native_mount_hook(void),native_open_hook(void),native_save_hook(void);
extern void install_page_timing(void);
uint32_t direct_trampoline[4] __attribute__((aligned(4)));
uint32_t open_trampoline[4] __attribute__((aligned(4)));
static unsigned active_books;
static char active_cache;
static int mounted;
#ifdef NATIVE_TRACE
static Handle trace_handle;
static uint64_t trace_offset;
static unsigned trace_count;

static void trace(const char*message){
    if(!trace_handle||trace_count++>48)return;
    uint32_t written=0;unsigned n=strlen(message);
    if(R_SUCCEEDED(FSFILE_Write(trace_handle,&written,trace_offset,message,n,FS_WRITE_FLUSH)))trace_offset+=written;
}
#else
static void trace(const char*message){(void)message;}
#endif

static int cached_path(const uint16_t*path){
    char name[160];unsigned n=0;
    while(path[n]&&n<sizeof(name)-1){if(path[n]>127)return 0;name[n]=(char)path[n];n++;}
    if(path[n])return 0;name[n]=0;
    if(!strcmp(name,"master/default.bms")||!strcmp(name,"master/default.pms")||!strcmp(name,"layout/Body_PuzzleSelect.arc"))return 1;
    const char*prefixes[]={"puzzle/pack_","completemodel/cm_pack_","texture/thumbnail/pack_","texture/book/cover/Pack","texture/book/icon/Pack"};
    for(unsigned i=0;i<sizeof(prefixes)/sizeof(prefixes[0]);i++)if(!strncmp(name,prefixes[i],strlen(prefixes[i])))return 1;
    if(strncmp(name,"text/",5))return 0;
    if(strncmp(name+5,"en/",3)&&strncmp(name+5,"fr/",3)&&strncmp(name+5,"de/",3)&&strncmp(name+5,"es/",3)&&strncmp(name+5,"it/",3))return 0;
    const char*resources[]={"BookNo.msbt","BookName.msbt","PuzzleNo.msbt","PuzzleName.msbt","Trivia.msbt"};
    for(unsigned i=0;i<sizeof(resources)/sizeof(resources[0]);i++)if(!strcmp(name+8,resources[i]))return 1;
    return 0;
}

static uint32_t checksum(const void*data,unsigned n){
    uint32_t table[256];
    for(unsigned i=0;i<256;i++){uint32_t c=i;for(int bit=0;bit<8;bit++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));table[i]=c;}
    uint32_t c=~0u;const uint8_t*p=data;
    while(n--)c=table[(c^*p++)&255]^(c>>8);return ~c;
}
static void jump(uint32_t at,const void*target){uint32_t*p=(uint32_t*)at;p[0]=0xe51ff004;p[1]=(uint32_t)target;}
/* Each four-book group has a separate three-profile band. The first group
 * retains the exact legacy offsets. Official SAVEDATA remains unchanged. */
#define SAVE_HEAD 45688u
#define SAVE_TOTAL 917504u
#define EXTRA_SIZE (SAVE_TOTAL-SAVE_HEAD)
#define LEGACY_EXTRA 65528u
static Handle progress_files[2];
static uint8_t extra_progress[EXTRA_SIZE];
static unsigned progress_sequence,progress_generation,progress_span=LEGACY_EXTRA;
static void*progress_loaded_data;
static int progress_valid;
extern unsigned native_progress_span(void);
static uint32_t progress_crc(const uint8_t*p,unsigned n){return checksum(p,n);}
static __attribute__((noinline)) int progress_prepare(FILE*log){
 uint8_t*candidate=malloc(EXTRA_SIZE);if(!candidate)return 0;
 unsigned needed=native_progress_span();if(needed>progress_span)progress_span=needed;
 if(progress_span>EXTRA_SIZE){free(candidate);return 0;}
 for(unsigned i=0;i<2;i++){
  const char*path=i?"/PictoPlus/progress-USA-B.bin":"/PictoPlus/progress-USA-A.bin";
  Result result=FSUSER_OpenFileDirectly(&progress_files[i],ARCHIVE_SDMC,fsMakePath(PATH_EMPTY,""),fsMakePath(PATH_ASCII,path),FS_OPEN_READ|FS_OPEN_WRITE|FS_OPEN_CREATE,0);
  if(R_FAILED(result)){free(candidate);return 0;}
  uint64_t size=0;if(R_FAILED(FSFILE_GetSize(progress_files[i],&size))){free(candidate);return 0;}if(!size)continue;
  uint32_t h[8],read=0;result=FSFILE_Read(progress_files[i],&read,0,h,32);
  if(R_FAILED(result)||read!=32||memcmp(h,"PPLUSUS1",8)||h[2]!=1||h[3]<LEGACY_EXTRA||h[3]>EXTRA_SIZE||size!=32+h[3])continue;
  result=FSFILE_Read(progress_files[i],&read,32,candidate,h[3]);
  if(R_FAILED(result)||read!=h[3]||progress_crc(candidate,h[3])!=h[5])continue;
  if(!progress_valid||(int32_t)(h[4]-progress_sequence)>0){
   memset(extra_progress,0,EXTRA_SIZE);memcpy(extra_progress,candidate,h[3]);progress_sequence=h[4];progress_generation=i;progress_valid=1;
   if(h[3]>progress_span)progress_span=h[3];
  }
 }
 free(candidate);fprintf(log,"Progress ready: %u bytes; generation %u; original save unchanged.\n",progress_span,progress_sequence);return 1;
}
static void progress_restore(void*data){
 if(progress_loaded_data==data)return;
 memcpy((uint8_t*)data+SAVE_HEAD,extra_progress,EXTRA_SIZE);progress_loaded_data=data;
}
int native_store_progress(void*object){
 if(!object)return 0;uint8_t*data=*(uint8_t**)((uint8_t*)object+4);if(!data)return 0;
 unsigned next=progress_valid?1-progress_generation:0;uint32_t written=0,h[8]={0};
 memcpy(h,"PPLUSUS1",8);h[2]=1;h[3]=progress_span;h[4]=progress_sequence+1;h[5]=progress_crc(data+SAVE_HEAD,progress_span);
 Result result=FSFILE_Write(progress_files[next],&written,32,data+SAVE_HEAD,progress_span,0);
 if(R_FAILED(result)||written!=progress_span)return 0;
 result=FSFILE_SetSize(progress_files[next],32+progress_span);if(R_FAILED(result))return 0;
 result=FSFILE_Write(progress_files[next],&written,0,h,32,FS_WRITE_FLUSH);if(R_FAILED(result)||written!=32)return 0;
 memcpy(extra_progress,data+SAVE_HEAD,progress_span);progress_sequence++;progress_generation=next;progress_valid=1;return 1;
}
uint32_t save_write_trampoline[4] __attribute__((aligned(4)));
extern void native_save_write_hook(void);

/* Extra records live outside the game's 23 official dirty-tracked chunks.
 * Request a normal save using the existing last 8-byte official chunk; never
 * enlarge its disk range or change the original save's bytes.
 */
extern int native_progress_changed(const uint8_t*data,const uint8_t*snapshot);
void native_progress_dirty(void*object){
 if(!object)return;
 uint8_t*data=*(uint8_t**)((uint8_t*)object+4);
 if(!data||data!=progress_loaded_data)return;
 if(native_progress_changed(data,extra_progress))
  *((uint8_t*)object+0x34+22*20+0x10)=1;
}
uint32_t save_dirty_trampoline[4] __attribute__((aligned(4)));
extern void native_save_dirty_hook(void);

static void trampoline(uint32_t*out,uint32_t original){
    out[0]=*(uint32_t*)original;out[1]=*(uint32_t*)(original+4);out[2]=0xe51ff004;out[3]=original+8;
}
/* Collision-free keys for the resource names generated by this loader. */
static uint32_t direct_number(const char*s,const char*prefix,const char*suffix,unsigned kind){
 size_t n=strlen(prefix);if(strncmp(s,prefix,n))return 0;s+=n;
 if(*s<'0'||*s>'9')return 0;unsigned value=0;
 do{value=value*10+(*s++-'0');if(value>65535)return 0;}while(*s>='0'&&*s<='9');
 return strcmp(s,suffix)?0:(kind<<16)|value;
}
static uint32_t direct_key(const char*s){
 uint32_t key;
 if((key=direct_number(s,"puzzle/pack_",".qpp",1)))return key;
 if((key=direct_number(s,"completemodel/cm_pack_",".bch",2)))return key;
 if((key=direct_number(s,"texture/thumbnail/pack_",".ctpk",3)))return key;
 if((key=direct_number(s,"texture/book/cover/Pack",".bch",4)))return key;
 if((key=direct_number(s,"texture/book/icon/Pack",".ctpk",5)))return key;
 if(!strcmp(s,"master/default.bms"))return 0x60001;
 if(!strcmp(s,"master/default.pms"))return 0x60002;
 if(!strcmp(s,"layout/Body_PuzzleSelect.arc"))return 0x60003;
 const char*languages[]={"en/","fr/","de/","es/","it/"};
 const char*names[]={"BookNo.msbt","BookName.msbt","PuzzleNo.msbt","PuzzleName.msbt","Trivia.msbt"};
 if(strncmp(s,"text/",5))return 0;
 for(unsigned l=0;l<5;l++)if(!strncmp(s+5,languages[l],3))
  for(unsigned r=0;r<5;r++)if(!strcmp(s+8,names[r]))return 0x70000+l*8+r;
 return 0;
}

#define DIRECT_MAX 45000
#define DIRECT_OPEN_MAX 128
typedef struct {uint32_t key,source,offset,size,patch_id,crc;} DirectEntry;
_Static_assert(sizeof(DirectEntry)==24,"Compact direct index layout");
static DirectEntry direct_entries[DIRECT_MAX];
static char direct_sources[72][256];
static unsigned direct_count;
typedef struct {volatile uint32_t claimed;Handle handle;uint32_t owner;const DirectEntry*entry;} DirectOpen;
static DirectOpen direct_open_files[DIRECT_OPEN_MAX];
static uint32_t direct_read_original[4] __attribute__((aligned(4)));
static uint32_t direct_size_original[4] __attribute__((aligned(4)));
static uint32_t direct_close_original[4] __attribute__((aligned(4)));
static uint32_t direct_thread(void){uint32_t t;__asm__("mrc p15,0,%0,c13,c0,3":"=r"(t));return t;}
static DirectOpen*direct_handle(Handle h){for(unsigned i=0;i<DIRECT_OPEN_MAX;i++)if(direct_open_files[i].claimed&&direct_open_files[i].handle==h)return direct_open_files+i;return 0;}
static DirectOpen*direct_pending(void){uint32_t t=direct_thread();for(unsigned i=0;i<DIRECT_OPEN_MAX;i++)if(direct_open_files[i].claimed&&!direct_open_files[i].handle&&direct_open_files[i].owner==t)return direct_open_files+i;return 0;}
static __attribute__((noinline)) int direct_init(FILE*log){
 direct_count=0;if(!active_books)return 1;
 char path[96];snprintf(path,sizeof(path),"sdmc:/PictoPlus/direct%c/catalogue.bin",active_cache);
 FILE*f=fopen(path,"rb");if(!f)return 0;
 uint32_t h[8];int ok=fread(h,1,32,f)==32&&!memcmp(h,"PPLUSID2",8)&&h[2]==2&&h[3]<=DIRECT_MAX&&h[6]&&h[6]<=72&&h[7]==32+h[6]*256+h[3]*24&&h[5]>=h[7]&&h[5]<=0x8000000;
 if(ok)ok=fread(direct_sources,256,h[6],f)==h[6]&&fread(direct_entries,24,h[3],f)==h[3];
 if(ok){
  /* Incremental CRC across the two table regions avoids a temporary copy. */
  uint32_t table[256];for(unsigned k=0;k<256;k++){uint32_t c=k;for(unsigned b=0;b<8;b++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));table[k]=c;}
  uint32_t c=~0u;for(unsigned block=0;block<2;block++){
   const uint8_t*p=block?(uint8_t*)direct_entries:(uint8_t*)direct_sources;unsigned n=block?h[3]*24:h[6]*256;
   while(n--)c=table[(c^*p++)&255]^(c>>8);
  }ok=~c==h[4];
 }
 if(ok){fseek(f,0,SEEK_END);ok=ftell(f)==h[5];}
 for(unsigned i=0;ok&&i<h[6];i++){
  const char*p=direct_sources[i];ok=memchr(p,0,256)&&!strstr(p,"..")&&
   (!strncmp(p,"vx:/PictoPlus/Books/",20)||!strcmp(p,"vx:/PictoPlus/directA/catalogue.bin")||!strcmp(p,"vx:/PictoPlus/directB/catalogue.bin"));
 }
 for(unsigned i=0;ok&&i<h[3];i++){
  DirectEntry*e=direct_entries+i;ok=e->key&&(!i||direct_entries[i-1].key<e->key)&&e->source<h[6]&&e->size&&e->offset<=0x10000000&&e->size<=0x10000000-e->offset;
  if(!ok)break;
  if(strncmp(direct_sources[e->source],"vx:/PictoPlus/direct",20))continue;
  if(e->offset<h[7]||e->offset>h[5]||e->size>h[5]-e->offset){ok=0;break;}
  fseek(f,e->offset,SEEK_SET);static uint8_t buffer[4096];uint32_t table[256];
  for(unsigned k=0;k<256;k++){uint32_t c=k;for(unsigned b=0;b<8;b++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));table[k]=c;}
  unsigned left=e->size;uint32_t c=~0u;while(left){unsigned n=left>sizeof(buffer)?sizeof(buffer):left;
   if(fread(buffer,1,n,f)!=n){ok=0;break;}for(unsigned k=0;k<n;k++)c=table[(c^buffer[k])&255]^(c>>8);left-=n;
  }if(~c!=e->crc)ok=0;
 }
 fclose(f);if(!ok){fputs("Compact direct index rejected.\n",log);return 0;}
 direct_count=h[3];fprintf(log,"Compact direct reader: %u resources, %u source files.\n",direct_count,h[6]);return 1;
}

static int direct_utf16(const char*s,uint16_t*out,unsigned capacity){
 unsigned n=0;while(*s){uint32_t c=(unsigned char)*s++;unsigned extra=0;
  if(c>=0xf0){if(c>0xf4)return 0;c&=7;extra=3;}else if(c>=0xe0){c&=15;extra=2;}else if(c>=0xc2){c&=31;extra=1;}else if(c>=0x80)return 0;
  while(extra--){unsigned b=(unsigned char)*s++;if((b&0xc0)!=0x80)return 0;c=(c<<6)|(b&63);}
  if(c>0x10ffff||(c>=0xd800&&c<=0xdfff))return 0;
  if(c>=0x10000){if(n+2>=capacity)return 0;c-=0x10000;out[n++]=0xd800+(c>>10);out[n++]=0xdc00+(c&1023);}else{if(n+1>=capacity)return 0;out[n++]=c;}
 }out[n]=0;return 1;
}
static __attribute__((noinline)) int direct_open_asset(void*object,const uint16_t*path,unsigned mode,unsigned extra){
 char name[128];unsigned n=0;while(path[n]){if(n>=127||path[n]>127)return 0;name[n]=(char)path[n];n++;}name[n]=0;
 uint32_t key=direct_key(name);if(!key)return 0;
 unsigned lo=0,hi=direct_count;while(lo<hi){unsigned mid=(lo+hi)/2;if(direct_entries[mid].key<key)lo=mid+1;else hi=mid;}
 const DirectEntry*entry=lo<direct_count&&direct_entries[lo].key==key?direct_entries+lo:0;if(!entry)return 0;
 DirectOpen*slot=0;for(unsigned i=0;i<DIRECT_OPEN_MAX;i++)if(__sync_bool_compare_and_swap(&direct_open_files[i].claimed,0,1)){slot=direct_open_files+i;break;}if(!slot)return -1;
 slot->handle=0;slot->owner=direct_thread();slot->entry=entry;
 uint16_t book[256];if(!direct_utf16(direct_sources[entry->source],book,256)){slot->claimed=0;return -1;}
 int result=((int(*)(void*,const uint16_t*,unsigned,unsigned))open_trampoline)(object,book,mode,extra);
 if(result<0){slot->claimed=0;return -1;}
 void*file=*(void**)object;if(!file){slot->claimed=0;return -1;}
 Handle handle=*(Handle*)((uint8_t*)file+4);
 if(!handle||(slot->handle&&slot->handle!=handle)){slot->claimed=0;return -1;}
 slot->handle=handle;slot->owner=0;__sync_synchronize();return 1;
}
static int direct_read(Handle*file,uint32_t*count,uint64_t offset,void*data,uint32_t size){
 DirectOpen*s=direct_handle(*file);if(!s)return ((int(*)(Handle*,uint32_t*,uint64_t,void*,uint32_t))direct_read_original)(file,count,offset,data,size);
 const DirectEntry*e=s->entry;if(offset>=e->size){*count=0;return 0;}if(size>e->size-offset)size=e->size-offset;
 int result=((int(*)(Handle*,uint32_t*,uint64_t,void*,uint32_t))direct_read_original)(file,count,(uint64_t)e->offset+offset,data,size);
 if(result>=0&&e->patch_id&&offset<8&&offset+*count>4){uint8_t*p=data;for(unsigned i=0;i<*count&&offset+i<8;i++)if(offset+i>=4)p[i]=(e->patch_id>>(8*(offset+i-4)))&255;}
 return result;
}
static int direct_size(Handle*file,uint64_t*size){
 DirectOpen*s=direct_handle(*file);if(!s){s=direct_pending();if(s)s->handle=*file;}
 if(s){*size=s->entry->size;return 0;}return ((int(*)(Handle*,uint64_t*))direct_size_original)(file,size);
}
static int direct_close(Handle*file){
 DirectOpen*s=direct_handle(*file);int result=((int(*)(Handle*))direct_close_original)(file);
 if(result>=0&&s){s->handle=0;s->owner=0;__sync_synchronize();s->claimed=0;}return result;
}
static void install_direct_hooks(void){
 trampoline(direct_read_original,0x21e668);jump(0x21e668,direct_read);
 trampoline(direct_size_original,0x21e74c);jump(0x21e74c,direct_size);
 trampoline(direct_close_original,0x21e6c0);jump(0x21e6c0,direct_close);
}

void native_mount_sd(void){
    if(mounted)return;
    void*archive=0;
    int result=((int(*)(void**,unsigned))0x134ec8)(&archive,9);
    trace(result<0?"SD archive mount failed\n":"SD archive mounted\n");
    if(result<0)return;
    result=((int(*)(const char*,void*,unsigned,unsigned))0x1ec580)("vx:",archive,0,0);
    if(result>=0)mounted=1;
    trace(result<0?"SD alias registration failed\n":"SD alias registered\n");
}
int native_redirect_open(void*object,const uint16_t*path,unsigned mode,unsigned extra){
    if(!path)return 0;
    unsigned start=0;
    if(path[0]=='r'&&path[1]==':')start=2;
    else if(path[0]=='r'&&path[1]=='o'&&path[2]=='m'&&path[3]==':')start=4;
    else return 0;
    while(path[start]=='/')start++;
    // Never probe SD for unmodified game resources. These misses previously
    // added an extra filesystem open before every original ROMFS read.
    if(!cached_path(path+start))return 0;if(!mounted)native_mount_sd();if(!mounted)return 0;
    int direct=direct_open_asset(object,path+start,mode,extra);if(direct)return direct>0;
    uint16_t redirected[256];const char*prefix="vx:/PictoPlus/directA/";unsigned n=0;
    while(prefix[n]){redirected[n]=prefix[n];n++;}redirected[n-2]=active_cache;
    for(unsigned i=start;;i++){
        if(n>=255)return 0;redirected[n++]=path[i];if(!path[i])break;
    }
    int result=((int(*)(void*,const uint16_t*,unsigned,unsigned))open_trampoline)(object,redirected,mode,extra);
    if(result!=0&&path[start]=='m')trace("Custom catalogue open failed; original fallback\n");
    return result==0;
}
extern void native_initialize_records(void*data);
void native_prune_books(void*save_object,unsigned loaded){
    if(!loaded||!save_object)return;
    uint8_t*data=*(uint8_t**)((uint8_t*)save_object+4);if(!data)return;progress_restore(data);
    // Book availability must match the current catalogue. Puzzle progress in
    // all permanent banks remains intact when a book is temporarily removed.
    for(unsigned profile=0;profile<3;profile++){
        uint16_t*selection=(uint16_t*)(data+12+profile*0x3b78+0x2220);
        if(*selection!=0xffff&&*selection>=57+active_books)
            *selection=active_books?57:0;
        for(unsigned book=57;book<128;book++){
            uint32_t*p=(uint32_t*)(data+12+profile*0x3b78+0x20+book*4);
            if(book>=57+active_books)*p=0;else if(!*p)*p=3;
        }
    }
    native_initialize_records(data);
}
static int apply_ips(const uint8_t*p,unsigned size){
    if(size<8||memcmp(p,"PATCH",5))return 0;
    unsigned at=5;
    while(at+3<=size){
        if(!memcmp(p+at,"EOF",3))return at+3==size;
        if(at+5>size)return 0;
        unsigned offset=(p[at]<<16)|(p[at+1]<<8)|p[at+2],length=(p[at+3]<<8)|p[at+4];at+=5;
        if(!length||length>size-at||offset>0x1d4000||length>0x1d4000-offset)return 0;
        memcpy((void*)(0x100000+offset),p+at,length);at+=length;
    }return 0;
}
int install_native_catalogue(FILE*log,int compiled_count){
    if(compiled_count<0)compiled_count=0;unsigned char state[2]={0,0};
    if(compiled_count!=0){
        FILE*f=fopen("sdmc:/PictoPlus/direct-active-cache.txt","rb");
        int ok=0;if(f){ok=fread(state,1,2,f)==2;fclose(f);}
        if(!ok||(state[0]!='A'&&state[0]!='B')||state[1]<1||state[1]>71){
            fputs("No valid cache; original catalogue with custom books hidden.\n",log);state[0]=state[1]=0;
        }
    }
    if(checksum((void*)0x100000,0x193b3c)!=ORIGINAL_TEXT_CRC){fputs("Unsupported or already modified game executable; no native patch applied.\n",log);return 0;}
    if(!progress_prepare(log))return 0;active_cache=state[0];active_books=state[1];if(!direct_init(log)){active_cache=0;active_books=0;}
#ifdef NATIVE_TRACE
    FSUSER_OpenFileDirectly(&trace_handle,ARCHIVE_SDMC,fsMakePath(PATH_EMPTY,""),
        fsMakePath(PATH_ASCII,"/PictoPlus/native-hook-trace.txt"),FS_OPEN_WRITE|FS_OPEN_CREATE,0);
    if(trace_handle)FSFILE_SetSize(trace_handle,0);
#endif
    trampoline(direct_trampoline,0x11de2c);trampoline(open_trampoline,0x1ee99c);
    if(!apply_ips(paging_payloads[0],paging_sizes[0])){fputs("Invalid built-in paging patch.\n",log);return 0;}
    if(active_books){jump(0x11de2c,native_mount_hook);jump(0x1ee99c,native_open_hook);}
    // A near branch reaches an absolute-jump veneer in verified RO padding.
    // The 3GX loader maps game memory executable, including this padding.
    uint32_t veneer=0x2cbfc0;
    jump(veneer,native_save_hook);
    *(uint32_t*)0x2543a4=0xea000000|(((veneer-0x2543a4-8)>>2)&0xffffff);
    trampoline(save_write_trampoline,0x25409c);jump(0x25409c,native_save_write_hook);trampoline(save_dirty_trampoline,0x253d08);jump(0x253d08,native_save_dirty_hook);install_direct_hooks();install_page_timing();
    svcFlushEntireDataCache();svcInvalidateEntireInstructionCache();
    fprintf(log,"Native game patch installed: %u SD books; cache%c.\n",active_books,active_cache);
    return 1;
}

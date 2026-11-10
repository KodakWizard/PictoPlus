#include "game_region.h"
/* Read-only diagnostic counters in plugin RAM. No runtime SD writes. */
#include <3ds.h>
#include <stdint.h>

typedef struct {uint32_t sequence,stage,scene,selection,ticks,reads,bytes,read_ticks;} Sample;
struct {uint32_t magic,version,published,capacity;Sample samples[64];} page_timing={0x5043544d,1,0,64,{{0}}};
static volatile uint32_t read_calls,read_bytes,read_ticks;
static uint32_t originals[5][4] __attribute__((aligned(4)));

typedef uint32_t(*SceneFn)(void*,uint32_t,uint32_t,uint32_t);
typedef int(*ReadFn)(void*,uint32_t*,uint64_t,void*,uint32_t);
static uint32_t timed_scene(unsigned stage,void*scene,uint32_t a,uint32_t b,uint32_t c){
    uint64_t start=svcGetSystemTick();uint32_t calls=read_calls,bytes=read_bytes,ticks=read_ticks;
    uint32_t result=((SceneFn)originals[stage-1])(scene,a,b,c);
    uint32_t sequence=page_timing.published+1;
    Sample sample={sequence,stage,(uint32_t)scene,a,(uint32_t)(svcGetSystemTick()-start),read_calls-calls,read_bytes-bytes,read_ticks-ticks};
    page_timing.samples[(sequence-1)%64]=sample;
    __sync_synchronize();page_timing.published=sequence;
    return result;
}
static uint32_t timed_cards(void*s,uint32_t a,uint32_t b,uint32_t c){return timed_scene(1,s,a,b,c);}
static uint32_t timed_selection(void*s,uint32_t a,uint32_t b,uint32_t c){return timed_scene(2,s,a,b,c);}
static uint32_t timed_preview(void*s,uint32_t a,uint32_t b,uint32_t c){return timed_scene(3,s,a,b,c);}
static uint32_t timed_model(void*s,uint32_t a,uint32_t b,uint32_t c){return timed_scene(4,s,a,b,c);}
static int timed_read(void*file,uint32_t*count,uint64_t offset,void*data,uint32_t size){
    uint64_t start=svcGetSystemTick();int result=((ReadFn)originals[4])(file,count,offset,data,size);
    __sync_fetch_and_add(&read_calls,1);
    if(result>=0&&count)__sync_fetch_and_add(&read_bytes,*count);
    __sync_fetch_and_add(&read_ticks,(uint32_t)(svcGetSystemTick()-start));
    return result;
}
void install_page_timing(void){
    const uint32_t addresses[]={PP_PAGE_LOAD,PP_PAGE_REBUILD,PP_PAGE_RESOURCE_LOAD,PP_PAGE_RESOURCE_RELEASE,PP_READ};
    const void*hooks[]={timed_cards,timed_selection,timed_preview,timed_model,timed_read};
    for(unsigned i=0;i<5;i++){
        uint32_t*source=(uint32_t*)addresses[i];
        originals[i][0]=source[0];originals[i][1]=source[1];originals[i][2]=0xe51ff004;originals[i][3]=addresses[i]+8;
        source[0]=0xe51ff004;source[1]=(uint32_t)hooks[i];
    }
}

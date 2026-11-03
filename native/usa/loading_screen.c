/* Temporary native loading screen, released before the game starts. */
#include <3ds.h>
#include <stdio.h>
#include <string.h>
#include "loading_font.h"
#include "loading_logo.h"

static int visible;
static FILE*progress_log;
static uint64_t began;
static char logged_phase[32];
static unsigned logged_done=~0u;
static uint8_t*prepared[2];
static uint64_t last_update;
static char last_phase[32];
static void pixel(uint8_t*fb,int x,int y,uint8_t r,uint8_t g,uint8_t b){
    unsigned p=(x*240+239-y)*3;fb[p]=b;fb[p+1]=g;fb[p+2]=r;
}
static void fill(uint8_t*fb,unsigned width,int x,int y,int w,int h,uint8_t r,uint8_t g,uint8_t b){
    for(int xx=x;xx<x+w;xx++)for(int yy=y;yy<y+h;yy++)if(xx>=0&&xx<(int)width&&yy>=0&&yy<240)pixel(fb,xx,yy,r,g,b);
}
static void ink(uint8_t*fb,unsigned width,int x,int y,unsigned alpha,unsigned r,unsigned g,unsigned b){
    if(x<0||x>=(int)width||y<0||y>=240||!alpha)return;
    unsigned p=(x*240+239-y)*3;
    fb[p]=(b*alpha+fb[p]*(255-alpha))/255;fb[p+1]=(g*alpha+fb[p+1]*(255-alpha))/255;fb[p+2]=(r*alpha+fb[p+2]*(255-alpha))/255;
}
static void label(uint8_t*fb,unsigned width,const char*text,int y){
    unsigned length=0;for(const char*p=text;*p;p++)if(*p>=32&&*p<127)length+=loading_widths[*p-32];
    int x=((int)width-(int)length)/2;
    while(*text){unsigned c=(unsigned char)*text++;
        if(c>=32&&c<127){const uint8_t*glyph=loading_glyphs+(c-32)*24*24;
            for(int row=0;row<24;row++)for(int col=0;col<24;col++)ink(fb,width,x+col,y+row,glyph[row*24+col],99,74,47);
            x+=loading_widths[c-32];
        }
    }
}
static void roundbox(uint8_t*fb,unsigned width,int x,int y,int w,int h,int radius,unsigned r,unsigned g,unsigned b){
    for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++){
        int dx=xx<radius?radius-xx:xx>=w-radius?xx-(w-radius-1):0;
        int dy=yy<radius?radius-yy:yy>=h-radius?yy-(h-radius-1):0;
        if(dx*dx+dy*dy<=radius*radius)fill(fb,width,x+xx,y+yy,1,1,r,g,b);
    }
}
static void paper(uint8_t*fb,unsigned width){
    for(unsigned x=0;x<width;x++)for(int y=0;y<240;y++){
        int stripe=((x/14)%2)*3+((y/14)%2)*2;
        pixel(fb,x,y,249-stripe,239-stripe,207-stripe);
    }
    // Mint gingham header echoes the game's bookshelf fabric.
    for(unsigned x=0;x<width;x++)for(int y=0;y<13;y++){
        int stripe=(x/12)%2;pixel(fb,x,y,stripe?206:236,stripe?225:238,stripe?193:208);
    }
    fill(fb,width,0,13,width,2,221,203,161);
}
typedef struct{int x,y;} Point;
static void polygon(uint8_t*fb,Point*a,unsigned r,unsigned g,unsigned b){
    int minx=a[0].x,maxx=minx,miny=a[0].y,maxy=miny;
    for(int i=1;i<4;i++){if(a[i].x<minx)minx=a[i].x;if(a[i].x>maxx)maxx=a[i].x;if(a[i].y<miny)miny=a[i].y;if(a[i].y>maxy)maxy=a[i].y;}
    for(int x=minx;x<=maxx;x++)for(int y=miny;y<=maxy;y++){
        int positive=0,negative=0;for(int i=0;i<4;i++){Point p=a[i],q=a[(i+1)%4];int cross=(q.x-p.x)*(y-p.y)-(q.y-p.y)*(x-p.x);positive|=cross>0;negative|=cross<0;}
        if(!(positive&&negative))pixel(fb,x,y,r,g,b);
    }
}
static void cube(uint8_t*fb,int x,int y){
    Point top[]={{x,y},{x+8,y-8},{x+28,y-8},{x+20,y}};
    Point side[]={{x+20,y},{x+28,y-8},{x+28,y+12},{x+20,y+20}};
    polygon(fb,top,106,221,233);polygon(fb,side,20,128,158);
    fill(fb,400,x,y,20,20,41,176,195);
    fill(fb,400,x+1,y,18,1,86,211,222);
    fill(fb,400,x,y+1,1,18,65,194,208);
}
static void logo(uint8_t*fb){
 for(int y=0;y<90;y++)for(int x=0;x<90;x++){
  const uint8_t*p=loading_logo+(y*90+x)*4;ink(fb,400,155+x,58+y,p[3],p[0],p[1],p[2]);
 }
}
/* Use the game's initialized GSP session. Do not initialize APT/GSP a second
 * time, acquire/release GPU rights, or register a competing event thread. */
static FILE*display_log;
static uint32_t display_memory;
static int display_attempted,display_failed;
static unsigned display_frames;
#define DISPLAY_BYTES 1040384u
#define TOP_BYTES (400u*240u*3u)
#define BOTTOM_BYTES (320u*240u*3u)
static void display_note(const char*phase,Result result){
 if(!display_log)display_log=fopen("sdmc:/PictoPlus/startup-display.txt","a");
 if(display_log){fprintf(display_log,"DISPLAY %s: %08lx\n",phase,(unsigned long)result);fflush(display_log);}
}
void loader_display_reserve(void){
 FILE*f=fopen("sdmc:/PictoPlus/disable-startup-graphics.flag","rb");
 if(f){fclose(f);display_failed=1;display_note("disabled by flag",0);return;}
 /* Reserve before the native heap allocator divides remaining process RAM. */
 Result r=svcControlMemory(&display_memory,0,0,DISPLAY_BYTES,MEMOP_ALLOC_LINEAR,MEMPERM_READWRITE);
 display_note("linear framebuffer allocation",r);
 if(R_FAILED(r)||!display_memory){display_failed=1;return;}
 memset((void*)display_memory,0,DISPLAY_BYTES);
}
static int display_begin(void){
 if(display_attempted)return !display_failed;
 display_attempted=1;
 if(display_failed||!display_memory)return 0;
 Handle session=*(Handle*)0x2d3488;
 if(!session){display_failed=1;display_note("native GSP session absent",-1);return 0;}
 *gspGetSessionHandle()=session;
 display_note("native session ready (no GPU acquisition)",0);return 1;
}
static uint8_t*display_buffer(unsigned screen){
 unsigned frame=display_frames&1;
 return (uint8_t*)(display_memory+frame*(TOP_BYTES+BOTTOM_BYTES)+(screen?TOP_BYTES:0));
}
static void display_present(void){
 for(unsigned screen=0;screen<2;screen++){
  uint8_t*fb=display_buffer(screen);
  Result r=GSPGPU_FlushDataCache(fb,screen?BOTTOM_BYTES:TOP_BYTES);
  if(R_FAILED(r)){display_failed=1;display_note("framebuffer flush failed",r);return;}
  GSPGPU_FramebufferInfo info={0};info.active_framebuf=display_frames&1;
  info.framebuf0_vaddr=info.framebuf1_vaddr=(uint32_t*)fb;
  info.framebuf_widthbytesize=240*3;
  info.format=GSP_BGR8_OES|(1u<<8)|(screen?0:(1u<<6));
  info.framebuf_dispselect=info.active_framebuf;
  r=GSPGPU_SetBufferSwap(screen,&info);
  if(R_FAILED(r)){display_failed=1;display_note("present failed",r);return;}
 }
 if(!display_frames){Result r=GSPGPU_SetLcdForceBlack(0);display_note("first frame unblack",r);}
 /* No unbounded VBlank wait, and no dependency on a plugin event thread. */
 svcSleepThread(17000000);display_frames++;
}
static void display_end(void){
 if(display_memory){
  /* The game has not created its render targets yet. Hide our buffers before
   * freeing them; native graphics startup will install its own targets. */
  display_note("handover black",GSPGPU_SetLcdForceBlack(1));
  uint32_t ignored;Result r=svcControlMemory(&ignored,display_memory,0,DISPLAY_BYTES,MEMOP_FREE,MEMPERM_DONTCARE);
  display_note("framebuffer release",r);display_memory=0;
 }
 if(display_log){fprintf(display_log,"DISPLAY presented %u frames; failed=%d; returning to game.\n",display_frames,display_failed);fclose(display_log);display_log=0;}
 *gspGetSessionHandle()=0;
}

void loader_progress(const char*phase,unsigned done,unsigned total){
    uint64_t tick=svcGetSystemTick();
    if(!began)began=tick;
    if((!done||done%4==0||done==total)&&(strcmp(logged_phase,phase)||logged_done!=done)){
      if(!progress_log)progress_log=fopen("sdmc:/PictoPlus/startup-progress.txt","w");
      if(progress_log){fprintf(progress_log,"%s %u/%u at %u ms\n",phase,done,total,(unsigned)((tick-began)/268123));fflush(progress_log);}
      strncpy(logged_phase,phase,31);logged_done=done;
    }
    if(visible&&!strcmp(last_phase,phase)&&done<total&&tick-last_update<SYSCLOCK_ARM11/10)return;
    if(display_failed)return;
    if(!visible){if(!display_begin())return;visible=1;}
    uint8_t*top=display_buffer(0);uint8_t*bottom=display_buffer(1);
    int ready=top==prepared[0]||top==prepared[1];
    if(!ready){
    paper(top,400);paper(bottom,320);
    roundbox(top,400,29,25,344,194,12,219,201,158);roundbox(top,400,27,22,344,194,12,255,251,231);
    for(int y=0;y<42;y++)for(int x=0;x<LOADING_BRAND_WIDTH;x++){
        unsigned a=loading_brand[y*LOADING_BRAND_WIDTH+x];
        ink(top,400,(400-LOADING_BRAND_WIDTH)/2+x,30+y+1,a,225,206,157);
        ink(top,400,(400-LOADING_BRAND_WIDTH)/2+x,30+y,a,101,72,42);
    }
    logo(top);
    roundbox(bottom,320,28,54,268,137,10,219,201,158);roundbox(bottom,320,26,51,268,137,10,255,251,231);
    label(bottom,320,"Updating your books",66);label(bottom,320,"Please wait...",99);
    label(bottom,320,"The game will start",132);label(bottom,320,"automatically.",154);
    if(!prepared[0])prepared[0]=top;else prepared[1]=top;
    }
    // Draw only the changing area, entirely off screen, before presenting.
    fill(top,400,40,150,320,59,255,251,231);
    label(top,400,phase,151);
    char count[32];snprintf(count,sizeof(count),"%u / %u",done,total);label(top,400,count,174);
    roundbox(top,400,65,198,270,9,4,224,215,185);
    if(total&&done)roundbox(top,400,65,198,270*(done>total?total:done)/total,9,4,45,167,148);
    display_present();
    last_update=tick;strncpy(last_phase,phase,sizeof(last_phase)-1);
}
void loader_progress_end(void){
 if(progress_log){fclose(progress_log);progress_log=0;}
 display_end();visible=0;prepared[0]=prepared[1]=0;last_phase[0]=0;
}

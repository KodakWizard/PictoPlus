/* Native SD catalogue builder. Assets are streamed; no save files are opened. */
#include <algorithm>
#include <cerrno>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <strings.h>
#include <dirent.h>
#include <string>
#include <sys/stat.h>
#include <vector>

extern "C" uint64_t svcGetSystemTick(void);
using Bytes = std::vector<uint8_t>;
extern "C" void loader_progress(const char*,unsigned,unsigned);
#include "game_region.h"
static const std::string home=PP_STATE_SD;
static const std::string shared=PP_SD;
static FILE *report;
static std::string failure;
static uint32_t table[256];
static unsigned resident_bytes;
static uint32_t get32(const uint8_t *p) {return p[0]|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
static uint16_t get16(const uint8_t *p) {return p[0]|uint16_t(p[1])<<8;}
static void put32(uint8_t*p,uint32_t v){for(int i=0;i<4;i++)p[i]=v>>(i*8);}
static void put16(uint8_t*p,uint16_t v){p[0]=v;p[1]=v>>8;}
static uint32_t crc(const uint8_t*p,size_t n,uint32_t previous=0){
    uint32_t c=~previous;while(n--)c=table[(c^*p++)&255]^(c>>8);return ~c;
}
static bool fail(const char *message){failure=message;return false;}
static std::vector<std::string> ready_dirs;
static unsigned directory_calls,write_calls;
static uint64_t directory_ticks,write_ticks;
static bool directories(const std::string&path){
 for(size_t p=path.find('/',6);p!=std::string::npos;p=path.find('/',p+1)){
  std::string dir=path.substr(0,p);
  if(std::find(ready_dirs.begin(),ready_dirs.end(),dir)!=ready_dirs.end())continue;
  uint64_t t=svcGetSystemTick();int result=mkdir(dir.c_str(),0777);
  directory_ticks+=svcGetSystemTick()-t;directory_calls++;
  if(result==0||errno==EEXIST)ready_dirs.push_back(dir);
 }return true;
}
static Bytes read(const std::string&path,size_t max=2000000){
    FILE*f=fopen(path.c_str(),"rb");if(!f){fail("A required loader file is missing.");return {};}
    fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
    if(n<0||size_t(n)>max){fclose(f);fail("Loader data exceeds its limit.");return {};}
    Bytes data(n);bool ok=fread(data.data(),1,n,f)==size_t(n);fclose(f);
    if(!ok){fail("Could not read loader data.");return {};}
    return data;
}
/* Generated menus are staged on SD, never retained together in RAM. */
struct DirectMetadata {std::string name,path;uint32_t size,crc;};
static std::vector<DirectMetadata> direct_metadata;
static char metadata_write_buffer[32768];
static bool stream_bytes(FILE*f,const void*p,size_t n){return !n||fwrite(p,1,n,f)==n;}
static FILE*metadata_begin(const std::string&stage){
 std::string path=stage+".metadata-"+std::to_string(direct_metadata.size())+".tmp";directories(path);
 FILE*f=fopen(path.c_str(),"wb");if(!f)fail("Could not stage native menu data.");else setvbuf(f,metadata_write_buffer,_IOFBF,sizeof(metadata_write_buffer));return f;
}
static bool metadata_end(FILE*f,const std::string&stage,const std::string&name,bool ok){
 long size=ftell(f);if(fclose(f))ok=false;
 std::string path=stage+".metadata-"+std::to_string(direct_metadata.size())+".tmp";
 if(!ok||size<1||size>0x8000000)return fail("Could not finish native menu data.");
 f=fopen(path.c_str(),"rb");if(!f)return fail("Could not verify native menu data.");
 uint32_t check=0,left=size;static uint8_t buffer[32768];
 while(left){unsigned n=std::min<unsigned>(left,sizeof(buffer));if(fread(buffer,1,n,f)!=n){fclose(f);return fail("Incomplete staged menu.");}check=crc(buffer,n,check);left-=n;}
 fclose(f);direct_metadata.push_back({name,path,(uint32_t)size,check});return true;
}
static bool collect_direct_metadata(const std::string&path,const Bytes&data){
 std::string stage=path.substr(0,home.size()+8); // directA/ or directB/
 if(stage!=home+"directA/"&&stage!=home+"directB/")return fail("Invalid menu stage path.");
 FILE*f=metadata_begin(stage);return f&&metadata_end(f,stage,path.substr(stage.size()),stream_bytes(f,data.data(),data.size()));
}

static bool write(const std::string&path,const Bytes&data){
    if((path.compare(0,(home+"directA/").size(),home+"directA/")==0||path.compare(0,(home+"directB/").size(),home+"directB/")==0)&&path.substr(path.size()-13)!="catalogue.bin")return collect_direct_metadata(path,data);directories(path);uint64_t write_start=svcGetSystemTick();FILE*f=fopen(path.c_str(),"wb");if(!f)return fail("Could not create SD cache file.");
    static char cache_buffer[65536];setvbuf(f,cache_buffer,_IOFBF,sizeof(cache_buffer));bool ok=fwrite(data.data(),1,data.size(),f)==data.size();if(fclose(f))ok=false;
    write_ticks+=svcGetSystemTick()-write_start;write_calls++;return ok||fail("Could not finish SD cache file.");
}
static bool exists(const std::string&path){FILE*f=fopen(path.c_str(),"rb");if(!f)return false;fclose(f);return true;}
static void append(Bytes&out,const uint8_t*p,size_t n){out.insert(out.end(),p,p+n);}
static void u32(Bytes&out,uint32_t v){size_t p=out.size();out.resize(p+4);put32(out.data()+p,v);}
static void ascii(uint8_t*at,size_t size,const std::string&s,bool wide=false){
    memset(at,0,size);for(size_t i=0;i<s.size()&&i+1<size/(wide?2:1);i++)at[i*(wide?2:1)]=s[i];
}
static Bytes utf16(const std::string&s){Bytes out;for(char c:s){out.push_back(c);out.push_back(0);}out.push_back(0);out.push_back(0);return out;}
static Bytes text(const uint8_t*p,size_t n){size_t len=0;while(len<n&&get16(p+len))len+=2;Bytes out(p,p+len);out.push_back(0);out.push_back(0);return out;}
/* Minimal local preparation from the running USA game; no bundled base files. */
#include "game_layout_recipe.h"
extern "C" int picto_mount_game(void);
extern "C" void picto_unmount_game(void);
static const std::string local_base=home+"generated-base-" PP_REGION "-v1/";
struct BaseFile {const char*name;unsigned size,checksum;};
#ifdef PICTOPLUS_EUR
#include "game_base_manifest_eur.h"
#else
#include "game_base_manifest.h"
#endif
static bool local_matches(const std::string&path,unsigned size,unsigned checksum){
 FILE*f=fopen(path.c_str(),"rb");if(!f)return false;
 uint8_t buf[4096];unsigned n=0,c=0;size_t k;
 while((k=fread(buf,1,sizeof(buf),f))){n+=k;c=crc(buf,k,c);}
 bool ok=!ferror(f)&&n==size&&c==checksum;fclose(f);return ok;
}
static bool local_copy(FILE*out,FILE*in,unsigned offset,unsigned size,unsigned&checksum){
 if(fseek(in,offset,SEEK_SET))return false;uint8_t buf[4096];
 while(size){unsigned n=std::min<unsigned>(size,sizeof(buf));if(fread(buf,1,n,in)!=n||fwrite(buf,1,n,out)!=n)return false;checksum=crc(buf,n,checksum);size-=n;}return true;
}
static bool prepare_local_base(){
 bool ready=true;for(auto&item:base_files)ready=local_matches(local_base+item.name,item.size,item.checksum)&&ready;
 ready=local_matches(local_base+"layout/Body_PuzzleSelect.arc",layout_size,layout_crc)&&ready;
 if(ready){fprintf(report,"Installed-game base ready; no RomFS preparation needed.\n");return true;}
 if(!picto_mount_game())return fail("Could not read the installed " PP_REGION " game. Keep your existing books and progress; use the supported " PP_REGION " release.");
 bool ok=true;unsigned done=0;
 for(auto&item:base_files){
  loader_progress("Preparing game files",done++,sizeof(base_files)/sizeof(base_files[0])+1);
  std::string path=local_base+item.name;if(local_matches(path,item.size,item.checksum))continue;
  std::string source=std::string("pictogame:/")+item.name,temp=path+".tmp";directories(temp);
  FILE*in=fopen(source.c_str(),"rb"),*out=in?fopen(temp.c_str(),"wb"):nullptr;unsigned check=0;
  ok=in&&out&&local_copy(out,in,0,item.size,check)&&fgetc(in)==EOF&&check==item.checksum;
  if(in)fclose(in);if(out&&fclose(out))ok=false;
  if(!ok){remove(temp.c_str());break;}remove(path.c_str());if(rename(temp.c_str(),path.c_str())){ok=false;break;}
 }
 if(ok&&!local_matches(local_base+"layout/Body_PuzzleSelect.arc",layout_size,layout_crc)){
  loader_progress("Preparing page controls",done,sizeof(base_files)/sizeof(base_files[0])+1);
  const char*names[]={"pictogame:/layout/Body_PuzzleSelect.arc","pictogame:/layout/Parts_Common.arc"};
  FILE*inputs[]={nullptr,nullptr};
  for(unsigned i=0;i<2;i++)if(!local_matches(names[i],layout_source_sizes[i],layout_source_crcs[i]))ok=false;
  if(ok){inputs[0]=fopen(names[0],"rb");inputs[1]=fopen(names[1],"rb");ok=inputs[0]&&inputs[1];}
  std::string path=local_base+"layout/Body_PuzzleSelect.arc",temp=path+".tmp";directories(temp);
  FILE*out=ok?fopen(temp.c_str(),"wb"):nullptr;ok=ok&&out;unsigned check=0,written=0;
  for(auto&op:layout_ops){if(!ok)break;
   if(op.source<2)ok=local_copy(out,inputs[op.source],op.offset,op.size,check);
   else if(op.source==2&&op.offset<=sizeof(layout_literals)&&op.size<=sizeof(layout_literals)-op.offset){const uint8_t*p=layout_literals+op.offset;ok=fwrite(p,1,op.size,out)==op.size;check=crc(p,op.size,check);}
   else ok=false;written+=op.size;
  }
  for(auto*f:inputs)if(f)fclose(f);if(out&&fclose(out))ok=false;ok=ok&&written==layout_size&&check==layout_crc;
  if(ok){remove(path.c_str());ok=!rename(temp.c_str(),path.c_str());}if(!ok)remove(temp.c_str());
 }
 picto_unmount_game();
 if(!ok)return fail("Installed game preparation failed validation. Your books and progress were not changed.");
 // A changed local layout must invalidate the compact menu cache once.
 if(!write(home+"rebuild.request",Bytes{'b','a','s','e'}))return false;
 fprintf(report,"Prepared local game base and labelled page controls from installed RomFS.\n");return true;
}

/* Opt-in local authoring preparation. Never installed or shared as game content. */
#include "authoring_manifest.h"
static bool prepare_authoring_profile(){
 std::string target=shared+"PictoPlus-Setup.pictosetup",temp=target+".tmp",previous=target+".previous";
 if(exists(previous)&&!exists(target)&&rename(previous.c_str(),target.c_str())){
  fprintf(report,"First-time setup: previous profile could not be restored. Request retained.\n");return false;
 }
 if(!exists(shared+"authoring.request")&&(exists(target)||exists(shared+"authoring.skip")))return true;
 if(!picto_mount_game()){fprintf(report,"First-time setup: installed game unavailable. Request retained.\n");loader_progress("Setup failed",0,1);return false;}
 const unsigned count=sizeof(authoring_files)/sizeof(authoring_files[0]),head=32+count*176;
 Bytes index(count*176,0);unsigned total=head;
 for(unsigned i=0;i<count;i++){uint8_t*p=index.data()+i*176;strncpy((char*)p,authoring_files[i].name,159);put32(p+160,authoring_files[i].size);put32(p+164,authoring_files[i].checksum);put32(p+168,total);total+=authoring_files[i].size;}
 uint8_t header[32]={};memcpy(header,"PPAUTH01",8);put32(header+8,1);put32(header+12,count);put32(header+16,176);put32(header+20,total);put32(header+24,crc(index.data(),index.size()));put32(header+28,crc(header,32));
 FILE*out=fopen(temp.c_str(),"wb");static char authoring_buffer[65536];if(out)setvbuf(out,authoring_buffer,_IOFBF,sizeof(authoring_buffer));
 bool ok=out&&fwrite(header,1,32,out)==32&&fwrite(index.data(),1,index.size(),out)==index.size();Bytes().swap(index);
 for(unsigned i=0;ok&&i<count;i++){
  loader_progress("Preparing first-time setup",i,count);const auto&item=authoring_files[i];std::string name=std::string("pictogame:/")+item.name;
  FILE*in=fopen(name.c_str(),"rb");unsigned check=0;ok=in&&local_copy(out,in,0,item.size,check)&&fgetc(in)==EOF&&check==item.checksum;if(in)fclose(in);
 }
 if(out&&fclose(out))ok=false;picto_unmount_game();
 if(ok&&exists(target)){
  if(exists(previous)&&remove(previous.c_str()))ok=false;
  if(ok)ok=!rename(target.c_str(),previous.c_str());
 }
 if(ok){
  ok=!rename(temp.c_str(),target.c_str());
  if(!ok&&exists(previous))rename(previous.c_str(),target.c_str());
 }
 if(ok&&exists(previous))remove(previous.c_str());
 loader_progress(ok?"Setup file saved":"Setup failed",ok?1:0,1);
 if(ok){remove((shared+"authoring.request").c_str());fprintf(report,"First-time setup ready: PictoPlus/PictoPlus-Setup.pictosetup (%u files). Open it once in the desktop app.\n",count);}
 else {remove(temp.c_str());fprintf(report,"First-time setup failed; request retained. Existing books/progress unchanged.\n");}
 return ok;
}

struct Ref {uint32_t offset,size,crc;};
static Ref ref(const uint8_t*p){return {get32(p),get32(p+4),get32(p+8)};}
struct Book {std::string path;std::array<uint8_t,160> h;Bytes rows,resident;uint32_t size,digest;int bank;std::vector<int> slots;};
struct PuzzleID {uint8_t id[16];uint32_t geometry;uint32_t reserved;};
struct Bank {uint8_t id[16];uint32_t revision,digest;uint16_t used;uint16_t reserved;PuzzleID puzzles[210];};
struct Registry {char magic[8];uint32_t count;uint32_t crc;Bank banks[71];};
static Registry ledger;
static_assert(sizeof(PuzzleID)==24,"Registry layout");
static bool same(const uint8_t*a,const uint8_t*b){return !memcmp(a,b,16);}
static bool fullRead(FILE*f,uint8_t*p,size_t n){return fread(p,1,n,f)==n;}
static unsigned bank_save_slot(unsigned logical){return 3000+(logical/840)*3000+logical%840;}
static unsigned bank_game_id(unsigned logical){return logical<840?62000+logical:41000+logical-840;}
static bool load_registry(const std::string&path,Registry&result){
 FILE*f=fopen(path.c_str(),"rb");if(!f)return false;
 fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);
 if(size!=16+4*sizeof(Bank)&&size!=sizeof(Registry)){fclose(f);return false;}
 Bytes data(size);bool ok=fullRead(f,data.data(),data.size())&&fgetc(f)==EOF;fclose(f);if(!ok)return false;
 unsigned limit=size==16+4*sizeof(Bank)?4:71;
 if(memcmp(data.data(),limit==4?"VXREG001":"VXREG002",8)||get32(data.data()+8)>limit)return false;
 uint32_t saved=get32(data.data()+12);put32(data.data()+12,0);if(crc(data.data(),data.size())!=saved)return false;
 if(limit==4&&!exists(home+"registry.v1-backup.bin")){
  put32(data.data()+12,saved);if(!write(home+"registry.v1-backup.bin",data))return false;put32(data.data()+12,0);
 }
 memset(&result,0,sizeof(result));memcpy(&result,data.data(),data.size());memcpy(result.magic,"VXREG002",8);
 result.crc=crc((uint8_t*)&result,sizeof(result));return true;
}
extern "C" unsigned native_progress_span(void){
 unsigned end=45688+65528;
 for(unsigned bank=0;bank<ledger.count;bank++)if(ledger.banks[bank].used){
  unsigned last=12+2*0x3b78+0x220+bank_save_slot(bank*210+ledger.banks[bank].used-1)*16+16;
  if(last>end)end=last;
 }return end-45688;
}
extern "C" void native_initialize_records(void*raw){
 uint8_t*data=(uint8_t*)raw;
 for(unsigned bank=0;bank<ledger.count;bank++)for(unsigned slot=0;slot<ledger.banks[bank].used;slot++)
  for(unsigned profile=0;profile<3;profile++){
   uint32_t*p=(uint32_t*)(data+12+profile*0x3b78+0x220+bank_save_slot(bank*210+slot)*16);
   if(!(p[0]|p[1]|p[2]|p[3]))p[0]=9;
  }
}
extern "C" int native_progress_changed(const uint8_t*data,const uint8_t*snapshot){
 /* Do not scan the empty gaps between profile bands on every save poll. */
 for(unsigned bank=0;bank<ledger.count;bank++)if(ledger.banks[bank].used)
  for(unsigned profile=0;profile<3;profile++){
   unsigned at=12+profile*0x3b78+0x220+bank_save_slot(bank*210)*16;
   if(memcmp(data+at,snapshot+at-45688,ledger.banks[bank].used*16))return 1;
  }
 return 0;
}

static bool fingerprint(const std::vector<std::string>&files,Bytes&out){
    // The metadata includes CRCs of every native asset. Unchanged metadata
    // reuses previously validated extracted assets, never unvalidated payloads.
    out=Bytes{'V','X','F','A','S','T','0','8'};u32(out,files.size());
    for(auto&path:files){
        FILE*f=fopen(path.c_str(),"rb");if(!f)return false;
        uint8_t header[160];static uint8_t buffer[65536];
        if(!fullRead(f,header,160)||memcmp(header,"VXBOOK01",8)||get16(header+36)>210){fclose(f);return false;}
        uint32_t check=crc(header,160),left=get16(header+36)*640;
        while(left){unsigned n=std::min<uint32_t>(left,sizeof(buffer));if(!fullRead(f,buffer,n)){fclose(f);return false;}check=crc(buffer,n,check);left-=n;}
        fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);uint32_t whole=0,left_file=size;while(left_file){unsigned n=std::min<uint32_t>(left_file,sizeof(buffer));if(!fullRead(f,buffer,n)){fclose(f);return false;}whole=crc(buffer,n,whole);left_file-=n;}fclose(f);u32(out,whole);
        if(size<160||uint32_t(size)!=get32(header+132))return false;
        u32(out,path.size());append(out,(const uint8_t*)path.data(),path.size());u32(out,size);u32(out,check);
    }
    FILE*f=fopen((home+"registry.bin").c_str(),"rb");if(!f)return false;
    fclose(f);static Registry reg;bool ok=load_registry(home+"registry.bin",reg);
    if(!ok)return false;uint32_t saved=reg.crc;
    u32(out,saved);
    f=fopen((home+"direct-active-cache.txt").c_str(),"rb");if(!f)return false;
    uint8_t state[2];ok=fullRead(f,state,2);fclose(f);
    if(!ok||(state[0]!='A'&&state[0]!='B')||!state[1]||state[1]>71)return false;
    append(out,state,2);return true;
}
static int unchanged(const std::vector<std::string>&files){
    Bytes signature;if(!fingerprint(files,signature))return 0;
    FILE*f=fopen((home+"direct-books.signature").c_str(),"rb");if(!f)return 0;
    Bytes saved(signature.size());bool ok=fullRead(f,saved.data(),saved.size())&&fgetc(f)==EOF;fclose(f);
    if(!ok||saved!=signature)return 0;
    char generation=signature[signature.size()-2];
    for(const char*name:{"catalogue.bin"})
        if(!exists(home+"direct"+generation+"/"+name))return 0;
    return signature.back();
}
static bool validText(const uint8_t*p,size_t units,bool required){
    bool ended=false,any=false;
    for(size_t i=0;i<units;i++){uint16_t c=get16(p+i*2);if(!c){ended=true;continue;}if(ended)return false;any=true;
        if(c>=0xd800&&c<=0xdbff){if(++i>=units)return false;c=get16(p+i*2);if(c<0xdc00||c>0xdfff)return false;}
        else if(c>=0xdc00&&c<=0xdfff)return false;
    }return any||!required;
}
static bool checkBook(Book&b){
    FILE*f=fopen(b.path.c_str(),"rb");if(!f)return fail("Could not open book.");
    fseek(f,0,SEEK_END);long length=ftell(f);rewind(f);
    if(length<160||length>256*1024*1024||!fullRead(f,b.h.data(),160)){fclose(f);return fail("Incomplete book.");}
    b.size=length;auto*h=b.h.data();unsigned count=get16(h+36);uint32_t saved=get32(h+136);put32(h+136,0);
    bool ok=!memcmp(h,"VXBOOK01",8)&&get32(h+8)==1&&get32(h+12)==160&&count&&count<=210&&
        get16(h+38)<=1&&get32(h+40)==160&&get32(h+44)==640&&get32(h+132)==b.size&&get32(h+32)&&
        crc(h,160)==saved&&validText(h+48,24,true);
    put32(h+136,saved);
    if(!ok){fclose(f);return fail("Unsupported or damaged book header.");}
    b.rows.resize(count*640);if(!fullRead(f,b.rows.data(),b.rows.size())){fclose(f);return fail("Incomplete puzzle index.");}
    // Small books fit in a bounded startup buffer. Read once, then validate and
    // extract from memory instead of reopening SD for every individual asset.
    if(b.size<=2*1024*1024&&resident_bytes+b.size<=4*1024*1024){
        rewind(f);b.resident.resize(b.size);
        if(!fullRead(f,b.resident.data(),b.size)){fclose(f);return fail("Could not buffer book.");}
        if(memcmp(b.h.data(),b.resident.data(),160)||memcmp(b.rows.data(),b.resident.data()+160,b.rows.size())){fclose(f);return fail("Book changed while it was being loaded.");}
    }
    std::vector<Ref> refs={ref(h+96),ref(h+108)};if(get32(h+120)||get32(h+124)||get32(h+128))refs.push_back(ref(h+120));
    for(unsigned i=0;i<count;i++){
        uint8_t*p=b.rows.data()+i*640;uint32_t saved=get32(p+564);put32(p+564,0);ok=crc(p,640)==saved;put32(p+564,saved);
        ok=ok&&validText(p+32,28,true)&&validText(p+88,220,false);
        for(int j=16;j<19;j++)ok=ok&&p[j]>=1&&p[j]<=10;
        for(int j=20;j<32;j+=4)ok=ok&&get32(p+j)>=1&&get32(p+j)<=86400;
        for(unsigned j=0;j<i;j++)if(same(p,b.rows.data()+j*640))ok=false;
        if(!ok){fclose(f);return fail("Invalid or duplicate puzzle metadata.");}
        for(int at:{528,540,552})refs.push_back(ref(p+at));
    }
    std::sort(refs.begin(),refs.end(),[](const Ref&a,const Ref&b){return a.offset<b.offset;});
    uint32_t end=160+count*640;static uint8_t buffer[65536];
    for(auto r:refs){
        if(r.offset%16||r.offset<end||!r.size||r.offset>b.size||r.size>b.size-r.offset){fclose(f);return fail("Book assets overlap or exceed the file.");}
        uint32_t check=0,remaining=r.size;
        if(!b.resident.empty()){check=crc(b.resident.data()+r.offset,r.size);remaining=0;}
        else fseek(f,r.offset,SEEK_SET);
        while(remaining){unsigned n=std::min<uint32_t>(remaining,sizeof(buffer));if(!fullRead(f,buffer,n)){fclose(f);return fail("Truncated book asset.");}check=crc(buffer,n,check);remaining-=n;}
        if(check!=r.crc){fclose(f);return fail("Book asset checksum failed.");}end=r.offset+r.size;
    }
    b.digest=0;uint32_t remaining=b.size;
    if(!b.resident.empty()){b.digest=crc(b.resident.data(),b.size);remaining=0;}
    else rewind(f);
    while(remaining){unsigned n=std::min<uint32_t>(remaining,sizeof(buffer));if(!fullRead(f,buffer,n)){fclose(f);return fail("Book read failed.");}b.digest=crc(buffer,n,b.digest);remaining-=n;}
    fclose(f);resident_bytes+=b.resident.size();return true;
}
/* Resolve shareable changed-byte assets against installed RomFS once per book. */
static std::vector<std::string> verified_template_sources;
static uint8_t installed_input_buffer[65536],installed_output_buffer[65536];
static bool same_installed_payload(const Book&b,Ref a,Ref other){
 if(a.size!=other.size||a.crc!=other.crc)return false;
 FILE*f=fopen(b.path.c_str(),"rb");if(!f)return false;uint8_t first[8192],second[8192];bool ok=true;
 for(unsigned done=0;ok&&done<a.size;){unsigned n=std::min<unsigned>(sizeof(first),a.size-done);
  ok=!fseek(f,a.offset+done,SEEK_SET)&&fullRead(f,first,n)&&!fseek(f,other.offset+done,SEEK_SET)&&fullRead(f,second,n)&&!memcmp(first,second,n);done+=n;
 }fclose(f);return ok;
}
static std::string prepared_book_name(const uint8_t*h){
 char key[112];char id[33];for(unsigned i=0;i<16;i++)snprintf(id+i*2,3,"%02x",h[16+i]);
 snprintf(key,sizeof(key),"Books/.prepared/%s-%08x-%08x.pictobook",id,get32(h+32),get32(h+136));return home+key;
}
// Bounded sequential input: edit records often contain only a few bytes.
// Never turn every record into a libc/SD read or a source-position query.
class InstalledInput {
 FILE*f;unsigned left,at=0,used=0;
 public:
 InstalledInput(FILE*file,unsigned size):f(file),left(size){}
 unsigned remaining()const{return left;}
 bool read(uint8_t*dst,unsigned n){
  if(n>left)return false;
  while(n){
   if(at==used){used=std::min<unsigned>(left,sizeof(installed_input_buffer));at=0;
    if(!fullRead(f,installed_input_buffer,used))return false;}
   unsigned k=std::min<unsigned>(n,used-at);memcpy(dst,installed_input_buffer+at,k);
   dst+=k;at+=k;left-=k;n-=k;
  }return true;
 }
};
static bool installed_payload(FILE*input,Ref r,FILE*out,Ref&result){
 if(fseek(input,r.offset,SEEK_SET))return false;uint8_t h[32];InstalledInput edits(input,r.size);
 if(r.size<32||!edits.read(h,32)||memcmp(h,"PPEDIT01",8))return false;
 unsigned len=get32(h+8),size=get32(h+12),source_crc=get32(h+16),total=get32(h+20),expected=get32(h+24),count=get32(h+28);
 if(!len||len>160||!size||size>32*1024*1024||!total||total>32*1024*1024||count>r.size/9||len>r.size-32)return false;
 char name[161];if(!edits.read((uint8_t*)name,len))return false;name[len]=0;
 if(strlen(name)!=len||strstr(name,"..")||strchr(name,':')||strchr(name,'\\')||
    (strncmp(name,"puzzle/",7)&&strncmp(name,"completemodel/",14)&&strncmp(name,"texture/",8)))return false;
 std::string path=std::string("pictogame:/")+name;
 std::string identity=path+":"+std::to_string(size)+":"+std::to_string(source_crc);
 if(std::find(verified_template_sources.begin(),verified_template_sources.end(),identity)==verified_template_sources.end()){
  if(!local_matches(path,size,source_crc))return false;verified_template_sources.push_back(identity);
 }
 FILE*source=fopen(path.c_str(),"rb");if(!source)return false;
 unsigned next=0,pending=0,previous_end=0,checksum=0;bool ok=true;
 result.offset=ftell(out);result.size=total;result.crc=expected;
 // Read each source block once, overlay edits in RAM, then checksum/write once.
 // No unchanged game bytes are added to the exported book.
 for(unsigned pos=0;ok&&pos<total;){
  unsigned n=std::min<unsigned>(total-pos,sizeof(installed_output_buffer));
  unsigned from=pos<size?std::min<unsigned>(n,size-pos):0;
  if(from&&!fullRead(source,installed_output_buffer,from)){ok=false;break;}
  if(from<n)memset(installed_output_buffer+from,0,n-from);
  unsigned end=pos+n;
  while(ok&&(pending||count)){
   if(!pending){
    uint8_t item[8];if(!edits.read(item,8)){ok=false;break;}count--;
    next=get32(item);pending=get32(item+4);
    if(!pending||next<previous_end||next>total||pending>total-next||pending>edits.remaining()){ok=false;break;}
    previous_end=next+pending;
   }
   if(next>=end)break;
   unsigned k=std::min<unsigned>(pending,end-next);
   ok=edits.read(installed_output_buffer+next-pos,k);next+=k;pending-=k;
  }
  if(ok){ok=fwrite(installed_output_buffer,1,n,out)==n;checksum=crc(installed_output_buffer,n,checksum);}
  pos=end;
 }
 ok=ok&&!pending&&!count&&!edits.remaining()&&checksum==expected;
 fclose(source);return ok;
}
static bool prepare_installed_book(Book&b){
 if(!get16(b.h.data()+38))return true;
 uint64_t preparation_started=svcGetSystemTick();
 resident_bytes-=b.resident.size();Bytes().swap(b.resident);
 std::string target=prepared_book_name(b.h.data());
 if(exists(target)){
  Book cached;cached.path=target;if(checkBook(cached)){b=std::move(cached);return true;}
  failure.clear();
 }
 if(!picto_mount_game())return fail("Could not access installed-game book templates.");
 std::string temp=target+".tmp";directories(temp);FILE*input=fopen(b.path.c_str(),"rb"),*out=input?fopen(temp.c_str(),"wb+"):nullptr;
 bool ok=input&&out;unsigned count=get16(b.h.data()+36);Bytes header(b.h.begin(),b.h.end()),rows=b.rows;
 put16(header.data()+38,0);memset(header.data()+120,0,12);put32(header.data()+140,0);
 if(ok)ok=fwrite(header.data(),1,header.size(),out)==header.size()&&fwrite(rows.data(),1,rows.size(),out)==rows.size();
 std::vector<uint8_t*>refs={header.data()+96,header.data()+108};
 for(unsigned i=0;i<count;i++)for(unsigned at:{528,540,552})refs.push_back(rows.data()+i*640+at);
 unsigned done=0;
 struct PreparedAsset {Ref input,output;};std::vector<PreparedAsset> reused;
 for(auto*p:refs){if(!ok)break;loader_progress("Preparing book assets",done++,refs.size());
  uint8_t pad[16]={};unsigned n=(-ftell(out))&15;ok=fwrite(pad,1,n,out)==n;Ref resolved;
  bool found=false;Ref original=ref(p);
  for(auto&prior:reused){if(!ok)break;if(original.size==prior.input.size&&original.crc==prior.input.crc&&same_installed_payload(b,original,prior.input)){
    resolved=prior.output;resolved.offset=ftell(out);unsigned checksum=0;
    ok=!fflush(out);FILE*cached=ok?fopen(temp.c_str(),"rb"):nullptr;
    ok=cached&&local_copy(out,cached,prior.output.offset,prior.output.size,checksum)&&checksum==prior.output.crc;
    if(cached)fclose(cached);found=true;break;
  }}
  if(ok&&!found){ok=installed_payload(input,original,out,resolved);if(ok)reused.push_back({original,resolved});}
  if(ok){put32(p,resolved.offset);put32(p+4,resolved.size);put32(p+8,resolved.crc);}
 }
 for(unsigned i=0;ok&&i<count;i++){uint8_t*p=rows.data()+i*640;put32(p+564,0);put32(p+564,crc(p,640));}
 if(ok){long end=ftell(out);ok=end>0&&end<=256*1024*1024;if(ok){put32(header.data()+132,end);put32(header.data()+136,0);put32(header.data()+136,crc(header.data(),160));ok=!fseek(out,0,SEEK_SET)&&fwrite(header.data(),1,160,out)==160&&fwrite(rows.data(),1,rows.size(),out)==rows.size();}}
 if(input)fclose(input);if(out&&fclose(out))ok=false;picto_unmount_game();
 if(!ok){remove(temp.c_str());return fail("Book template edits failed validation. Existing progress is unchanged.");}
 Book checked;checked.path=temp;if(!checkBook(checked)){remove(temp.c_str());return false;}
 remove(target.c_str());if(rename(temp.c_str(),target.c_str()))return fail("Could not commit prepared book.");
 checked.path=target;b=std::move(checked);fprintf(report,"Prepared installed-game assets locally: %u ms, %u assets.\n",unsigned((svcGetSystemTick()-preparation_started)/268123),unsigned(refs.size()));return true;
}

static Bytes asset(const Book&b,Ref r,size_t max){
    if(r.size>max){fail("Native puzzle data exceeds its limit.");return {};}
    if(!b.resident.empty())return Bytes(b.resident.begin()+r.offset,b.resident.begin()+r.offset+r.size);
    FILE*f=fopen(b.path.c_str(),"rb");if(!f){fail("Could not reopen book.");return {};}
    fseek(f,r.offset,SEEK_SET);Bytes out(r.size);bool ok=fullRead(f,out.data(),r.size);fclose(f);
    if(!ok||crc(out.data(),out.size())!=r.crc){fail("Book changed during loading.");return {};}
    return out;
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

/* Compact index: no repeated 128-byte names or 256-byte book paths. */
static Bytes direct_records;
static std::vector<std::string> direct_sources;
static unsigned direct_source(const std::string&name){
 auto it=std::find(direct_sources.begin(),direct_sources.end(),name);
 if(it!=direct_sources.end())return it-direct_sources.begin();
 direct_sources.push_back(name);return direct_sources.size()-1;
}
static bool direct_record(const Book&b,Ref r,const std::string&path,unsigned patch_id=0){
 uint32_t key=direct_key(path.c_str());std::string book="vx:"+b.path.substr(5);
 if(!key||book.size()>=256||direct_records.size()/24>=45000)return fail("Invalid direct book resource.");
 size_t at=direct_records.size();direct_records.resize(at+24);uint8_t*p=direct_records.data()+at;
 put32(p,key);put32(p+4,direct_source(book));put32(p+8,r.offset);put32(p+12,r.size);put32(p+16,patch_id);put32(p+20,r.crc);return true;
}
static bool write_direct_index(const std::string&stage){
 unsigned count=direct_records.size()/24+direct_metadata.size();if(count>45000)return fail("Too many indexed resources.");
 unsigned bundle=direct_source("vx:"+stage.substr(5)+"catalogue.bin");
 unsigned head=32+direct_sources.size()*256+count*24,total=head;
 for(auto&m:direct_metadata){total=(total+15)&~15u;if(m.size>0x8000000-total)return fail("Menu bundle exceeds supported size.");total+=m.size;}
 Bytes out(head);memcpy(out.data(),"PPLUSID2",8);put32(out.data()+8,2);put32(out.data()+12,count);put32(out.data()+20,total);put32(out.data()+24,direct_sources.size());put32(out.data()+28,head);
 for(unsigned i=0;i<direct_sources.size();i++)memcpy(out.data()+32+i*256,direct_sources[i].c_str(),direct_sources[i].size()+1);
 unsigned table_at=32+direct_sources.size()*256,at=table_at+direct_records.size(),offset=head;
 memcpy(out.data()+table_at,direct_records.data(),direct_records.size());
 for(auto&m:direct_metadata){
  unsigned key=direct_key(m.name.c_str());if(!key)return fail("Unknown native menu resource.");offset=(offset+15)&~15u;
  uint8_t*p=out.data()+at;put32(p,key);put32(p+4,bundle);put32(p+8,offset);put32(p+12,m.size);put32(p+20,m.crc);offset+=m.size;at+=24;
 }
 struct Entry{uint32_t v[6];};Entry*entries=(Entry*)(out.data()+table_at);
 std::sort(entries,entries+count,[](const Entry&a,const Entry&b){return a.v[0]<b.v[0];});
 for(unsigned i=1;i<count;i++)if(entries[i-1].v[0]==entries[i].v[0])return fail("Duplicate native resource key.");
 put32(out.data()+16,crc(out.data()+32,head-32));
 std::string pending=stage+"catalogue.next";FILE*f=fopen(pending.c_str(),"wb");if(!f)return fail("Could not create catalogue bundle.");
 setvbuf(f,metadata_write_buffer,_IOFBF,sizeof(metadata_write_buffer));
 bool ok=stream_bytes(f,out.data(),out.size());offset=head;Bytes().swap(out);static uint8_t buffer[32768];uint8_t pad[16]={};
 unsigned finished=0;loader_progress("Finishing book import",0,direct_metadata.size());
 for(auto&m:direct_metadata){
  unsigned n=(-offset)&15;if(n)ok=ok&&stream_bytes(f,pad,n);offset+=n;
  FILE*input=fopen(m.path.c_str(),"rb");if(!input){ok=false;break;}
  uint32_t left=m.size,check=0;while(ok&&left){unsigned n=std::min<unsigned>(left,sizeof(buffer));
   if(fread(buffer,1,n,input)!=n){ok=false;break;}check=crc(buffer,n,check);ok=stream_bytes(f,buffer,n);left-=n;offset+=n;
  }fclose(input);if(left||check!=m.crc)ok=false;
  loader_progress("Finishing book import",++finished,direct_metadata.size());
 }
 if(fclose(f))ok=false;
 if(!ok||offset!=total)return fail("Could not finish catalogue bundle.");
 remove((stage+"catalogue.bin").c_str());if(rename(pending.c_str(),(stage+"catalogue.bin").c_str()))return fail("Could not commit catalogue bundle.");
 for(auto&m:direct_metadata)remove(m.path.c_str());return true;
}

static bool copyAsset(const Book&b,Ref r,const std::string&path){
  // Cache generation names have equal lengths.
  std::string prefix=home+"directA/";return direct_record(b,r,path.substr(prefix.size()));
 }
 static std::string sharedAsset(const Book&b,Ref r,const std::string&stage,const std::string&path){return direct_record(b,r,path)?path:std::string();}
static const Book*row_book;
static Bytes row_cache;
static uint8_t*book_row(const Book&b,unsigned index){
 if(row_book!=&b){
  row_book=nullptr;unsigned count=get16(b.h.data()+36);row_cache.resize(count*640);
  FILE*f=fopen(b.path.c_str(),"rb");bool ok=f&&fseek(f,160,SEEK_SET)==0&&fullRead(f,row_cache.data(),row_cache.size());if(f)fclose(f);
  for(unsigned i=0;ok&&i<count;i++){
   uint8_t*p=row_cache.data()+i*640;uint32_t saved=get32(p+564);put32(p+564,0);ok=crc(p,640)==saved;put32(p+564,saved);
  }
  if(!ok){fail("Could not read book rows.");row_cache.assign(count*640,0);}else row_book=&b;
 }
 if(index>=row_cache.size()/640){fail("Invalid puzzle row.");static uint8_t empty[640];return empty;}
 return row_cache.data()+index*640;
}

static bool assign(std::vector<Book>&books){
    memset(&ledger,0,sizeof(ledger));memcpy(ledger.magic,"VXREG002",8);
    std::string registry=home+"registry.bin";
    if(!exists(registry)){
        if(exists(home+"registry.next"))registry=home+"registry.next";
        else if(exists(home+"registry.previous"))registry=home+"registry.previous";
    }
    // A cache implies identities have previously been assigned. If every
    // registry copy is missing, do not silently reuse those save slots.
    if(!exists(registry)&&exists(home+"direct-active-cache.txt"))return fail("The progress registry is missing. Restore it before adding books.");
    if(exists(registry)&&!load_registry(registry,ledger))return fail("The progress registry is damaged. It was preserved.");
    for(unsigned i=0;i<ledger.count;i++)if(ledger.banks[i].used>210)return fail("Invalid progress bank.");
    for(auto&b:books){
        unsigned bank=0;for(;bank<ledger.count;bank++)if(same(b.h.data()+16,ledger.banks[bank].id))break;
        if(bank==ledger.count){if(bank==71)return fail("The game has no remaining custom book records (71). Keep this registry to preserve removed books' progress.");memcpy(ledger.banks[bank].id,b.h.data()+16,16);ledger.count++;}
        Bank&saved=ledger.banks[bank];uint32_t rev=get32(b.h.data()+32);
        if(saved.revision>rev||(saved.revision==rev&&saved.digest!=b.digest))return fail("Book update conflicts with an installed revision.");
        b.bank=bank;
        for(unsigned i=0;i<get16(b.h.data()+36);i++){
            uint8_t*p=book_row(b,i);Bytes q=asset(b,ref(p+528),10000);if(q.size()<592||q[0]!=5||memcmp(q.data()+1,p+16,3))return fail("Invalid native puzzle dimensions.");
            unsigned cells=get32(q.data()+8);if(cells>1000||592+cells*4>q.size())return fail("Invalid puzzle geometry.");
            std::vector<uint32_t> voxels;bool occupied[1000]={};
            for(unsigned j=0;j<cells;j++){uint8_t*v=q.data()+592+j*4;unsigned x=v[1]&15,y=v[1]>>4,z=v[2]&15;
                if(v[0]>=218||x>=p[16]||y>=p[17]||z>=p[18]||occupied[x+y*10+z*100])return fail("Invalid or repeated puzzle block.");
                occupied[x+y*10+z*100]=true;voxels.push_back(get32(v));}
            std::sort(voxels.begin(),voxels.end());uint32_t geometry=crc(p+16,3);geometry=crc((uint8_t*)voxels.data(),voxels.size()*4,geometry);
            unsigned slot=0;for(;slot<saved.used;slot++)if(same(p,saved.puzzles[slot].id))break;
            if(slot==saved.used){if(slot==210)return fail("A permanent puzzle bank is full; existing progress slots are never reused.");memcpy(saved.puzzles[slot].id,p,16);saved.puzzles[slot].geometry=geometry;saved.used++;}
            else if(saved.puzzles[slot].geometry!=geometry)return fail("Changed puzzle geometry needs a new permanent ID.");
            b.slots.push_back(bank*210+slot);
        }
        saved.revision=rev;saved.digest=b.digest;
    }
    std::sort(books.begin(),books.end(),[](const Book&a,const Book&b){return a.bank<b.bank;});row_book=nullptr;return true;
}
struct Message {std::string key;Bytes value;};
static bool msbt(const std::string&source,const std::string&dest,const std::vector<Message>&add){
    Bytes raw=read(source);if(raw.size()<32||memcmp(raw.data(),"MsgStdBn",8)||raw[12]!=1)return fail("Unexpected base text resource.");
    Bytes output(raw.begin(),raw.begin()+32);size_t pos=32;
    for(unsigned section=0;section<get16(raw.data()+14);section++){
        if(pos+16>raw.size())return fail("Incomplete base text section.");
        uint32_t n=get32(raw.data()+pos+4);if(n>raw.size()-pos-16)return fail("Invalid base text size.");
        uint8_t*p=raw.data()+pos+16;Bytes body;
        if(!memcmp(raw.data()+pos,"TXT2",4)){
            unsigned count=get32(p),head=4+count*4;if(head>n)return fail("Invalid text offsets.");
            u32(body,count+add.size());for(unsigned i=0;i<count;i++)u32(body,get32(p+4+i*4)+add.size()*4);
            unsigned offset=n+add.size()*4;for(auto&m:add){u32(body,offset);offset+=m.value.size();}
            append(body,p+head,n-head);for(auto&m:add)append(body,m.value.data(),m.value.size());
        }else if(!memcmp(raw.data()+pos,"LBL1",4)){
            unsigned buckets=get32(p),messages=0;if(4+buckets*8>n)return fail("Invalid text label table.");
            // TXT2 can follow LBL1; locate its original message count first.
            size_t scan=32;for(unsigned k=0;k<get16(raw.data()+14);k++){
                if(scan+20>raw.size())return fail("Invalid base message table.");
                if(!memcmp(raw.data()+scan,"TXT2",4)){messages=get32(raw.data()+scan+16);break;}
                scan=(scan+16+get32(raw.data()+scan+4)+15)&~15u;
            }
            std::vector<Bytes> groups(buckets);std::vector<unsigned> counts(buckets);
            for(unsigned b=0;b<buckets;b++){
                unsigned count=get32(p+4+b*8),start=get32(p+8+b*8),end=start;
                for(unsigned i=0;i<count;i++){if(end>=n||p[end]+5u>n-end)return fail("Invalid base text label.");end+=p[end]+5;}
                if(start>n||end>n)return fail("Invalid base label offset.");groups[b]=Bytes(p+start,p+end);counts[b]=count;
            }
            for(unsigned i=0;i<add.size();i++){auto&m=add[i];uint32_t hash=0;for(unsigned char c:m.key)hash=hash*0x492+c;unsigned b=hash%buckets;
                groups[b].push_back(m.key.size());append(groups[b],(uint8_t*)m.key.data(),m.key.size());u32(groups[b],messages+i);counts[b]++;}
            u32(body,buckets);unsigned offset=4+buckets*8;for(unsigned b=0;b<buckets;b++){u32(body,counts[b]);u32(body,offset);offset+=groups[b].size();}
            for(auto&g:groups)append(body,g.data(),g.size());
        }else if(!memcmp(raw.data()+pos,"ATR1",4)){
            if(n<8||get32(p+4)!=0)return fail("Unsupported base message attributes.");body=Bytes(p,p+n);put32(body.data(),get32(p)+add.size());
        }else body=Bytes(p,p+n);
        size_t at=output.size();append(output,raw.data()+pos,16);put32(output.data()+at+4,body.size());append(output,body.data(),body.size());
        while(output.size()%16)output.push_back(0xab);pos=(pos+16+n+15)&~15u;
    }
    put32(output.data()+18,output.size());return write(dest,output);
}

static unsigned stream_message_count(const std::vector<Book>&books,unsigned resource){
 if(resource<2)return books.size()+(resource==0?2:0);unsigned n=0;for(auto&b:books)n+=get16(b.h.data()+36);return n;
}
#include "trivia_wrap.h"
static Message stream_message(const std::vector<Book>&books,unsigned resource,unsigned index){
 if(resource<2){
  if(index>=books.size())return index==books.size()?Message{"BOOKNO_STUDIO_PREVIOUS",utf16("Left: Previous")}:Message{"BOOKNO_STUDIO_NEXT",utf16("Right: Next")};
  std::string id=std::to_string(57+index);return {std::string(resource?"PACK_BOOKNAME_":"PACK_BOOKNO_")+id,resource?text(books[index].h.data()+48,48):utf16(id)};
 }
 unsigned bi=0;while(bi<books.size()&&index>=get16(books[bi].h.data()+36)){index-=get16(books[bi].h.data()+36);bi++;}
 if(bi==books.size()){fail("Invalid text puzzle index.");return {"",{}};}
 auto&b=books[bi];std::string id=std::to_string(bank_game_id(b.slots[index]));
 if(resource==2){char no[16];snprintf(no,sizeof(no),"C%03u",index+1);return {"PUZZLE_NO_"+id,utf16(no)};}
 uint8_t*p=book_row(b,index);return {"PUZZLE_NAME_"+id,resource==3?text(p+32,56):wrap_trivia(text(p+88,440))};
}
static bool stream_msbt(const std::vector<Book>&books,unsigned resource,const std::string&source,const std::string&stage,const std::string&name){
 Bytes raw=read(source);if(raw.size()<32||memcmp(raw.data(),"MsgStdBn",8)||raw[12]!=1)return fail("Unexpected base text resource.");
 unsigned add=stream_message_count(books,resource),messages=0;size_t scan=32;
 for(unsigned i=0;i<get16(raw.data()+14);i++){
  if(scan+20>raw.size())return fail("Invalid text section.");unsigned n=get32(raw.data()+scan+4);if(n>raw.size()-scan-16)return fail("Incomplete text section.");
  if(!memcmp(raw.data()+scan,"TXT2",4))messages=get32(raw.data()+scan+16);scan=(scan+16+n+15)&~15u;
 }
 FILE*f=metadata_begin(stage);if(!f)return false;bool ok=stream_bytes(f,raw.data(),32);size_t pos=32;
 for(unsigned section=0;ok&&section<get16(raw.data()+14);section++){
  unsigned n=get32(raw.data()+pos+4);uint8_t*p=raw.data()+pos+16;Bytes body;
  uint8_t header[16];memcpy(header,raw.data()+pos,16);
  if(!memcmp(header,"TXT2",4)){
   unsigned count=get32(p),head=4+count*4;if(head>n){ok=false;break;}
   unsigned total=n+add*4;for(unsigned i=0;i<add;i++)total+=stream_message(books,resource,i).value.size();
   put32(header+4,total);ok=stream_bytes(f,header,16);uint8_t word[4];put32(word,count+add);ok=ok&&stream_bytes(f,word,4);
   for(unsigned i=0;ok&&i<count;i++){put32(word,get32(p+4+i*4)+add*4);ok=stream_bytes(f,word,4);}
   unsigned offset=n+add*4;
   for(unsigned i=0;ok&&i<add;i++){put32(word,offset);ok=stream_bytes(f,word,4);offset+=stream_message(books,resource,i).value.size();}
   ok=ok&&stream_bytes(f,p+head,n-head);
   for(unsigned i=0;ok&&i<add;i++){Message m=stream_message(books,resource,i);ok=stream_bytes(f,m.value.data(),m.value.size());}
  }else{
   if(!memcmp(header,"LBL1",4)){
    unsigned buckets=get32(p);if(4+buckets*8>n){ok=false;break;}
    std::vector<Bytes>groups(buckets);std::vector<unsigned>counts(buckets);
    for(unsigned b=0;b<buckets;b++){
     unsigned count=get32(p+4+b*8),start=get32(p+8+b*8),end=start;
     for(unsigned i=0;i<count;i++){if(end>=n||p[end]+5u>n-end){ok=false;break;}end+=p[end]+5;}
     if(!ok||start>n||end>n){ok=false;break;}groups[b]=Bytes(p+start,p+end);counts[b]=count;
    }
    for(unsigned i=0;ok&&i<add;i++){
     Message m=stream_message(books,resource,i);uint32_t hash=0;for(unsigned char c:m.key)hash=hash*0x492+c;unsigned b=hash%buckets;
     groups[b].push_back(m.key.size());append(groups[b],(uint8_t*)m.key.data(),m.key.size());u32(groups[b],messages+i);counts[b]++;
    }
    u32(body,buckets);unsigned offset=4+buckets*8;for(unsigned b=0;b<buckets;b++){u32(body,counts[b]);u32(body,offset);offset+=groups[b].size();}
    for(auto&g:groups)append(body,g.data(),g.size());
   }else{
    body=Bytes(p,p+n);if(!memcmp(header,"ATR1",4)){if(n<8||get32(p+4)){ok=false;break;}put32(body.data(),get32(p)+add);}
   }
   put32(header+4,body.size());ok=ok&&stream_bytes(f,header,16)&&stream_bytes(f,body.data(),body.size());
  }
  uint8_t pad[16];memset(pad,0xab,16);unsigned padding=(-ftell(f))&15;ok=ok&&stream_bytes(f,pad,padding);pos=(pos+16+n+15)&~15u;
 }
 long length=ftell(f);uint8_t word[4];put32(word,length);ok=ok&&fseek(f,18,SEEK_SET)==0&&stream_bytes(f,word,4)&&fseek(f,length,SEEK_SET)==0;
 return metadata_end(f,stage,name,ok)&&failure.empty();
}

static bool catalogues(std::vector<Book>&books,const std::string&stage){
 Bytes bms=read(local_base+"master/default.bms"),pms=read(local_base+"master/default.pms");
 if(bms.size()<28+57*404||pms.size()<28+609*404||get16(bms.data()+8)!=57)return fail("Unexpected original catalogues.");
 unsigned bs=get32(bms.data()+20),ps=get32(pms.data()+20),layout=get32(bms.data()+28+39*404+396),total=0;
 if(bs>bms.size()||ps>pms.size()||layout+15*244>bms.size())return fail("Invalid original catalogue offsets.");
 Bytes header(bms.begin(),bms.begin()+bs);header.resize(bs+books.size()*404);
 for(unsigned i=0;i<57;i++){uint8_t*r=header.data()+28+i*404;unsigned offset=get32(r+396);if(offset)put32(r+396,offset+books.size()*404);}
 struct PuzzleRef{unsigned book,index,id;};std::vector<PuzzleRef> refs;
 unsigned next=header.size()+bms.size()-bs;
 for(unsigned bi=0;bi<books.size();bi++){
  auto&b=books[bi];unsigned id=57+bi,count=get16(b.h.data()+36);std::string key=std::to_string(id);
  uint8_t*r=header.data()+28+id*404;memcpy(r,bms.data()+28+3*404,404);put16(r,id);put16(r+2,id);r[4]=count;r[5]=r[6]=0;memset(r+28,0,16);
  ascii(r+44,32,"PACK_BOOKNO_"+key);ascii(r+76,32,"PACK_BOOKNAME_"+key);put32(r+396,next);next+=count*244;
  ascii(r+140,128,"r:/texture/book/cover/Pack"+key+".bch",true);ascii(r+268,128,"r:/texture/book/icon/Pack"+key+".ctpk",true);
  if(!copyAsset(b,ref(b.h.data()+96),stage+"texture/book/cover/Pack"+key+".bch")||!copyAsset(b,ref(b.h.data()+108),stage+"texture/book/icon/Pack"+key+".ctpk"))return false;
  for(unsigned i=0;i<count;i++)refs.push_back({bi,i,bank_game_id(b.slots[i])});
 }
 put16(header.data()+8,57+books.size());put32(header.data()+20,header.size());
 FILE*f=metadata_begin(stage);if(!f)return false;bool ok=stream_bytes(f,header.data(),header.size())&&stream_bytes(f,bms.data()+bs,bms.size()-bs);Bytes().swap(header);
 loader_progress("Preparing puzzles",0,refs.size());
 for(auto&r:refs){
  auto&b=books[r.book];uint8_t*p=book_row(b,r.index);std::string sid=std::to_string(r.id),base="pack_"+sid;
  uint8_t e[244];memcpy(e,bms.data()+layout+(r.index%15)*244,244);put16(e,r.index);put16(e+2,57+r.book);put32(e+4,r.id);memset(e+212,0,32);e[213]=4;put16(e+214,bank_save_slot(b.slots[r.index]));
  ascii(e+20,32,"PUZZLE_NO_"+sid);ascii(e+52,32,"PUZZLE_NAME_"+sid);ascii(e+84,128,"r:/texture/thumbnail/"+base+".ctpk",true);
  ok=ok&&stream_bytes(f,e,244)&&direct_record(b,ref(p+528),"puzzle/"+base+".qpp",r.id)&&direct_record(b,ref(p+540),"completemodel/cm_"+base+".bch")&&direct_record(b,ref(p+552),"texture/thumbnail/"+base+".ctpk");
  loader_progress("Preparing puzzles",++total,refs.size());if(!ok)break;
 }
 if(!metadata_end(f,stage,"master/default.bms",ok))return false;Bytes().swap(bms);
 std::sort(refs.begin(),refs.end(),[](const PuzzleRef&a,const PuzzleRef&b){return a.id<b.id;});
 for(unsigned i=0;i<get16(pms.data()+8);i++)if(get32(pms.data()+28+i*404)>=10000)for(auto&r:refs)if(get32(pms.data()+28+i*404)==r.id)return fail("Custom puzzle ID conflicts with original game.");
 header=Bytes(pms.begin(),pms.begin()+28);put16(header.data()+8,get16(pms.data()+8)+total);put32(header.data()+20,ps+total*404);
 f=metadata_begin(stage);if(!f)return false;ok=stream_bytes(f,header.data(),28)&&stream_bytes(f,pms.data()+28,ps-28);
 for(auto&r:refs){
  auto&b=books[r.book];uint8_t*p=book_row(b,r.index);std::string sid=std::to_string(r.id),base="pack_"+sid;uint8_t q[404];memcpy(q,pms.data()+28+608*404,404);
  put32(q,r.id);ascii(q+4,32,"PUZZLE_NO_"+sid);ascii(q+36,32,"PUZZLE_NAME_"+sid);ascii(q+68,128,"r:/puzzle/"+base+".qpp",true);ascii(q+196,128,"r:/completemodel/cm_"+base+".bch",true);memcpy(q+328,p+16,3);
  for(unsigned j=0;j<3;j++)put32(q+(j==0?368:j==1?376:400),get32(p+20+j*4));ok=ok&&stream_bytes(f,q,404);
 }
 ok=ok&&stream_bytes(f,pms.data()+ps,pms.size()-ps);if(!metadata_end(f,stage,"master/default.pms",ok))return false;Bytes().swap(pms);decltype(refs)().swap(refs);Bytes().swap(header);
 const char*resources[]={"BookNo","BookName","PuzzleNo","PuzzleName","Trivia"};
 for(unsigned resource=0;resource<5;resource++){
  loader_progress("Writing book menus",resource,5);
#ifdef PICTOPLUS_EUR
  for(const char*lang:{"en","fr","de","es","it"})
#else
  for(const char*lang:{"en","fr","es"})
#endif
  {std::string name=std::string("text/")+lang+"/"+resources[resource]+".msbt";
   if(!stream_msbt(books,resource,local_base+""+name,stage,name))return false;
  }
 }
 row_book=nullptr;Bytes().swap(row_cache);
 Bytes art=read(local_base+"layout/Body_PuzzleSelect.arc");if(art.empty()||!write(stage+"layout/Body_PuzzleSelect.arc",art))return false;Bytes().swap(art);
 fprintf(report,"Streaming menus complete; committing compact bundle.\n");
 if(!write_direct_index(stage))return false;fprintf(report,"Catalogue compiled: %u books, %u puzzles.\n",unsigned(books.size()),total);return failure.empty();
}

extern "C" int compile_native_books(FILE*log){
    report=log;verified_template_sources.clear();row_book=nullptr;Bytes().swap(row_cache);direct_records.clear();direct_sources.clear();direct_metadata.clear();ready_dirs.clear();resident_bytes=0;failure.clear();for(unsigned i=0;i<256;i++){uint32_t c=i;for(int b=0;b<8;b++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));table[i]=c;}
    if(!prepare_local_base()){fprintf(log,"NOT INSTALLED: %s\n",failure.c_str());return -1;}
    prepare_authoring_profile();
    std::vector<std::string> files;DIR*d=opendir((shared+"Books").c_str());if(!d){fprintf(log,"Books folder not found.\n");return 0;}
    struct dirent*e;while((e=readdir(d))){std::string n=e->d_name;if((n.size()>=8&&!strcasecmp(n.c_str()+n.size()-8,".voxbook"))||(n.size()>=10&&!strcasecmp(n.c_str()+n.size()-10,".pictobook")))files.push_back(shared+"Books/"+n);}closedir(d);std::sort(files.begin(),files.end());
    bool missing_prepared=false;
    for(auto&path:files){FILE*f=fopen(path.c_str(),"rb");uint8_t h[160];if(f){if(fullRead(f,h,160)&&get16(h+38)==1&&!exists(prepared_book_name(h)))missing_prepared=true;fclose(f);}}
    int cached=(missing_prepared||exists(home+"rebuild.request"))?0:unchanged(files);if(cached){fprintf(log,"FAST START: %u unchanged books; reusing validated SD catalogue.\n",unsigned(cached));return cached;}
    std::vector<Book> books;
    unsigned checked=0;
    for(auto&path:files){loader_progress("Checking books",checked++,files.size());Book b;b.path=path;if(!checkBook(b)||!prepare_installed_book(b))goto bad;Bytes().swap(b.resident);Bytes().swap(b.rows);resident_bytes=0;
        bool duplicate=false;for(auto&old:books)if(same(old.h.data()+16,b.h.data()+16)){
            unsigned a=get32(old.h.data()+32),v=get32(b.h.data()+32);if(a==v&&old.digest!=b.digest){fail("Two books claim the same ID and revision with different content.");goto bad;}
            if(v>a)old=std::move(b);duplicate=true;break;}
        if(!duplicate)books.push_back(std::move(b));
    }
    if(books.empty()){fprintf(log,"No books installed. Original game unchanged.\n");return 0;}
    if(books.size()>71){fail("The game supports 71 additional book records.");goto bad;}
    {unsigned buffered=0;for(auto&book:books)if(!book.resident.empty())buffered++;
        fprintf(log,"Input reads: %u books buffered once; %u streamed in 64 KiB blocks.\n",buffered,unsigned(books.size())-buffered);}
    fprintf(log,"DIAG3: assigning puzzle identities.\n");if(!assign(books))goto bad;fprintf(log,"DIAG3: identities complete.\n");
    {
        // Alternate complete cache generations; never expose a half-built one.
        Bytes old;FILE*f=fopen((home+"direct-active-cache.txt").c_str(),"rb");char current='B';if(f){current=fgetc(f);fclose(f);}
        char next=current=='A'?'B':'A';std::string stage=home+"direct"+next+"/";
        if(!catalogues(books,stage))goto bad;
        ledger.crc=0;ledger.crc=crc((uint8_t*)&ledger,sizeof(ledger));Bytes bytes((uint8_t*)&ledger,(uint8_t*)&ledger+sizeof(ledger));
        if(!write(home+"registry.next",bytes))goto bad;
        // Registry is append-only. Commit it first so interrupted cache promotion
        // can never cause progress slots to be assigned to different puzzles.
        remove((home+"registry.previous").c_str());
        if(exists(home+"registry.bin")&&rename((home+"registry.bin").c_str(),(home+"registry.previous").c_str())){fail("Could not preserve registry.");goto bad;}
        if(rename((home+"registry.next").c_str(),(home+"registry.bin").c_str())){rename((home+"registry.previous").c_str(),(home+"registry.bin").c_str());fail("Could not commit registry.");goto bad;}
        if(!write(home+"direct-active-cache.next",Bytes{uint8_t(next),uint8_t(books.size())}))goto bad;
        remove((home+"direct-active-cache.txt").c_str());if(rename((home+"direct-active-cache.next").c_str(),(home+"direct-active-cache.txt").c_str())){fail("Could not select completed cache.");goto bad;}
        Bytes signature;if(fingerprint(files,signature))write(home+"direct-books.signature",signature);
        remove((home+"rebuild.request").c_str());fprintf(log,"READY cache%c; %u books. Registry preserved on SD.\n",next,unsigned(books.size()));return books.size();
    }
bad:
    fprintf(log,"NOT INSTALLED: %s\n",failure.c_str());return -1;
}

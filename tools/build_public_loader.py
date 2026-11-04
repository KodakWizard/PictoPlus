"""Build the audited USA source snapshot with devkitARM; no game files required."""
import hashlib,json,os,pathlib,struct,subprocess,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]

def build(sdk=None):
 sdk=pathlib.Path(sdk or os.environ.get('DEVKITPRO',ROOT/'tools/native-loader/toolchain/opt/devkitpro'))
 suffix='.exe' if os.name=='nt' else '';binary=sdk/'devkitARM/bin'
 gcc=binary/('arm-none-eabi-gcc'+suffix);gpp=binary/('arm-none-eabi-g++'+suffix)
 if not gcc.is_file():raise SystemExit('Install devkitARM/libctru and set DEVKITPRO to the devkitPro directory. See docs/BUILDING.md.')
 source=ROOT/'native/usa';out=ROOT/'build/standalone-usa';out.mkdir(parents=True,exist_ok=True)
 vendor=ROOT/'native/vendor'
 flags=['-march=armv6k','-mtune=mpcore','-mfloat-abi=hard','-mtp=soft','-Os','-ffunction-sections','-fdata-sections','-D__3DS__','-I'+str(sdk/'libctru/include'),'-I'+str(source),'-I'+str(vendor),'-DNATIVE_CATALOGUE']
 def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 objects=[]
 for name in ('startup.s','discovery.c','catalogue.cpp','game_hooks.c','game_hooks.s','loading_screen.c','page_timing.c','game_romfs.c','csvc.s'):
  path=(vendor if name=='csvc.s' else source)/name;obj=out/(name+'.o')
  extra=['-std=c++17','-fno-exceptions','-fno-rtti'] if path.suffix=='.cpp' else []
  run(gpp if extra else gcc,*flags,*extra,'-c',path,'-o',obj);objects.append(obj)
 elf=out/'PictoPlus.elf';run(gpp,*flags,'-T',vendor/'3gx.ld','-Wl,--gc-sections','-nostartfiles',*objects,'-L'+str(sdk/'libctru/lib'),'-lctru','-lm','-o',elf)
 # The small ABI-checked boot decoder is assembled by the same toolchain.
 run(gcc,*flags,'-c',source/'decoder.s','-o',out/'decoder.o')
 run(binary/('arm-none-eabi-objcopy'+suffix),'-O','binary','-j','.text',out/'decoder.o',out/'decoder.bin')
 decoder=(out/'decoder.bin').read_bytes();assert len(decoder)<=128 and len(decoder)%4==0
 decoder+=struct.pack('<I',0xe320f000)*((128-len(decoder))//4)
 raw=elf.read_bytes();assert raw[:7]==b'\x7fELF\x01\x01\x01'
 phoff=struct.unpack_from('<I',raw,28)[0];phsize,phcount=struct.unpack_from('<HH',raw,42);segments=[]
 for i in range(phcount):
  typ,off,va,pa,n,mem,flags_,align=struct.unpack_from('<8I',raw,phoff+i*phsize)
  if typ==1:segments.append((va,raw[off:off+n],mem))
 segments.sort();assert len(segments)==3 and segments[0][0]==0x07000100
 sizes=[segments[1][0]-segments[0][0],segments[2][0]-segments[1][0],len(segments[2][1])]
 payload=b''.join(s[1].ljust(n,b'\0') for s,n in zip(segments,sizes));bss=segments[2][2]-sizes[2]
 data=bytearray(148);data[:8]=b'3GX$0002';struct.pack_into('<I',data,8,1)
 def add(blob):offset=len(data);data.extend(blob);return offset
 for at,text in ((16,'PictoPlus'),(24,'PictoPlus - SD books'),(32,''),(40,'')):
  blob=text.encode()+b'\0';offset=add(blob);struct.pack_into('<II',data,at,len(blob),offset)
 struct.pack_into('<I',data,48,1|(2<<2)|(2<<4)|(1<<7));offset=add(struct.pack('<I',0x00187d00));struct.pack_into('<II',data,128,1,offset)
 data.extend(b'\0'*(-len(data)%16));dec=add(decoder);off=add(payload)
 struct.pack_into('<10I',data,88,off,off+sizes[0],off+sizes[0]+sizes[1],*sizes,bss,dec,0,0)
 plugin=out/'PictoPlus.3gx';plugin.write_bytes(data)
 release=ROOT/'app/distribution/USA';release.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(release/'PictoPlus-USA-SD-Setup.zip','w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('luma/plugins/0004000000187D00/PictoPlus.3gx',data);z.writestr('PictoPlus/Books/',b'')
  z.writestr('PictoPlus/Setup files/Create setup file/authoring.request',b'PPAUTH01\n')
  z.writestr('PictoPlus/Setup files/Skip Setup/authoring.skip',b'PPAUTH01\n')
  z.writestr('PictoPlus-First-Time-Setup.txt',b'PictoPlus USA SD Loader\n\nCopy the luma and PictoPlus folders to your SD card root. Enable Luma plugins. Keep existing books, registry and progress.\n\nThe installed USA game creates a desktop setup profile if one is missing. To skip generation, copy authoring.skip from PictoPlus/Setup files/Skip Setup into SD:/PictoPlus/ before launching. To explicitly create or replace a profile later, copy authoring.request from PictoPlus/Setup files/Create setup file into SD:/PictoPlus/ and launch the game.\n\nAfter startup, look for SD:/PictoPlus/PictoPlus-Setup.pictosetup. A successful request disappears. If no profile appeared or the request is still there, read SD:/PictoPlus/native-loader-status.txt for the result and retry after correcting the issue. To cancel a pending request, remove authoring.request and copy authoring.skip into SD:/PictoPlus/. Keep the profile private. EUR is separate.\n')
 report=dict(sha256=hashlib.sha256(data).hexdigest(),hardware_verified=False,purpose='USA source build; local installed-game preparation')
 (release/'build-info.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));return plugin
if __name__=='__main__':build()

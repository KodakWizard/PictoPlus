"""Export the exact executable-icon PNG frames for documentation and reuse."""
import pathlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[2]
def export():
 raw=(ROOT/'app/assets/pictoplus.ico').read_bytes();reserved,kind,count=struct.unpack_from('<3H',raw)
 assert (reserved,kind)==(0,1)
 out=ROOT/'docs/images';out.mkdir(parents=True,exist_ok=True)
 sizes=[]
 for i in range(count):
  w,h,_,_,planes,bits,n,at=struct.unpack_from('<BBBBHHII',raw,6+i*16);w=w or 256;h=h or 256
  image=raw[at:at+n];assert image[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack_from('>II',image,16)==(w,h)
  (out/f'icon-{w}.png').write_bytes(image);sizes.append(w)
 assert sizes==[16,24,32,48,64,128,256];return sizes
if __name__=='__main__':print(export())

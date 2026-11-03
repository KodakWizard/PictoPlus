"""Distribute changed bytes only; the installed game supplies template data."""
import functools,hashlib,pathlib,struct,zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/"tools"))
import game_resources
MAGIC=b'PPEDIT01'
LIMIT=32*1024*1024

@functools.lru_cache(maxsize=1)
def _models():
    result={}
    for p in sorted((game_resources.romfs()/'completemodel').glob('*.bch')):
        with p.open('rb') as f:head=f.read(64)
        result.setdefault((p.stat().st_size,head),[]).append(p)
    return result

def template(raw,kind):
    base=game_resources.romfs()
    fixed={'puzzle':'puzzle/609_FruitsGrape.qpp','thumbnail':'texture/thumbnail/044_00609.ctpk',
           'cover':'texture/book/cover/Book44.bch','icon':'texture/book/icon/BookIcon44.ctpk'}
    if kind in fixed:return base/fixed[kind]
    candidates=_models().get((len(raw),raw[:64]),[])
    if not candidates:raise ValueError('This reveal has no verified installed-game template. Attach or rebuild its model before exporting.')
    # The established model writer preserves the native header and file size.
    return min(candidates,key=lambda p:sum(a!=b for a,b in zip(p.read_bytes(),raw)))

def encode(raw,kind):
    p=template(raw,kind);original=p.read_bytes();name=p.relative_to(game_resources.romfs()).as_posix().encode('ascii')
    baseline=original[:len(raw)].ljust(len(raw),b'\0')
    edits=[];i=0
    while i<len(raw):
        if raw[i]==baseline[i]:i+=1;continue
        start=i
        while i<len(raw) and raw[i]!=baseline[i]:i+=1
        edits.append((start,raw[start:i]))
    data=bytearray(MAGIC+struct.pack('<6I',len(name),len(original),zlib.crc32(original),len(raw),zlib.crc32(raw),len(edits))+name)
    for at,blob in edits:data+=struct.pack('<II',at,len(blob))+blob
    assert decode(bytes(data))==raw
    return bytes(data)

def decode(data,base=None):
    if not data.startswith(MAGIC):raise ValueError('Missing installed-game asset edits.')
    if len(data)<32:raise ValueError('Truncated asset edits.')
    length,size,checksum,out_size,out_crc,count=struct.unpack_from('<6I',data,8)
    if not 1<=length<=160 or not 1<=size<=LIMIT or not 1<=out_size<=LIMIT or count>LIMIT or 32+length+count*9>len(data):raise ValueError('Invalid asset edits header.')
    try:name=data[32:32+length].decode('ascii')
    except UnicodeError:raise ValueError('Invalid template name.')
    path=pathlib.PurePosixPath(name)
    if '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts or name not in (path.as_posix(),) or not name.startswith(('puzzle/','completemodel/','texture/')):raise ValueError('Unsafe template path.')
    try:raw=bytearray((pathlib.Path(base or game_resources.romfs())/name).read_bytes())
    except OSError as error:raise ValueError('Required local game template is unavailable.') from error
    if len(raw)!=size or zlib.crc32(raw)!=checksum:raise ValueError('Installed-game template does not match this book.')
    raw=raw[:out_size];raw.extend(bytes(out_size-len(raw)))
    pos=32+length;end=0
    for _ in range(count):
        if pos+8>len(data):raise ValueError('Truncated asset edit.')
        at,n=struct.unpack_from('<II',data,pos);pos+=8
        if not n or at<end or at>out_size or n>out_size-at or n>len(data)-pos:raise ValueError('Invalid asset edit range.')
        raw[at:at+n]=data[pos:pos+n];pos+=n;end=at+n
    if pos!=len(data) or zlib.crc32(raw)!=out_crc:raise ValueError('Asset edit checksum failed.')
    return bytes(raw)

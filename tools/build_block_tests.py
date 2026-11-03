"""Additional colour/shape probes alongside the verified torpedo; no originals replaced."""
import collections,json,pathlib,shutil,struct
from puzzle_format import Puzzle
from msbt import MessageFile
from colour_logic import solve
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'build/block-tests'
SOURCE=ROOT/'build/new-book-experimental'
def string(b,off,size,text,wide=False):
    raw=text.encode('utf-16le' if wide else 'ascii');assert len(raw)+(2 if wide else 1)<=size
    b[off:off+size]=raw+bytes(size-len(raw))
def write(name,data):
    p=OUT/'romfs'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
def build():
    shutil.copytree(SOURCE/'romfs',OUT/'romfs',dirs_exist_ok=True)
    b=bytearray((OUT/'romfs/master/default.bms').read_bytes())
    book=28+57*404;pointer=struct.unpack_from('<I',b,book+396)[0]
    assert b[book+4]==1
    template=bytes(b[pointer:pointer+244]);entries=[]
    for slot in range(1,3):
        e=bytearray(template);struct.pack_into('<H',e,0,slot);struct.pack_into('<I',e,4,60000+slot)
        struct.pack_into('<HH',e,8,20+slot*98,21);struct.pack_into('<H',e,214,395+slot)
        string(e,20,32,f'PUZZLE_NO_{60000+slot}');string(e,52,32,f'PUZZLE_NAME_{60000+slot}')
        entries.append(e)
    b[book+4]=3;b[pointer+8:pointer+12]=struct.pack('<HH',20,21)
    # This is the last book's last entry, so appending changes no existing pointers.
    assert pointer+244==len(b)
    b+=b''.join(entries);write('master/default.bms',b)
    p=bytearray((OUT/'romfs/master/default.pms').read_bytes())
    count=struct.unpack_from('<H',p,8)[0];secondary=struct.unpack_from('<I',p,20)[0]
    record=bytes(p[28+(count-1)*404:28+count*404]);assert struct.unpack_from('<I',record)[0]==60000
    new=[]
    shapes=(1,2,12,85,102,104,212,217)
    reports=[]
    for slot in (1,2):
        id=60000+slot;filename=f'{id}_BlockTest.qpp'
        r=bytearray(record);struct.pack_into('<I',r,0,id)
        string(r,4,32,f'PUZZLE_NO_{id}');string(r,36,32,f'PUZZLE_NAME_{id}')
        string(r,68,128,'r:/puzzle/'+filename,True);new.append(r)
        q=Puzzle.read((OUT/'romfs/puzzle/60000_Torpedo.qpp').read_bytes())
        h=bytearray(q.header);struct.pack_into('<I',h,4,id);q.header=bytes(h)
        voxels=[];solution={};orange_index=0
        for _,xy,zc,flags in q.voxels:
            x,y,z=xy&15,xy>>4,zc&15;orange=x<=1 or x>=8
            shape=73 if orange else 0
            if slot==2 and orange:
                shape=shapes[orange_index%len(shapes)];orange_index+=1
            voxels.append((shape,xy,zc,flags));solution[x,y,z]=2 if orange else 1
        q.voxels=voxels
        x,y,z=q.dimensions;q.masks=[bytes([1])*(x*y),bytes([1])*(x*z),bytes([1])*(z*y)]*5
        data=q.write();check=Puzzle.read(data);assert check.voxels==q.voxels
        proof=solve(q.dimensions,solution)
        report={'id':id,'name':'Two-colour Torpedo' if slot==1 else 'Shaped Block Probe',
          'shape_counts':dict(collections.Counter(v[0] for v in q.voxels)),
          'blue':sum(c==1 for c in solution.values()),'orange':sum(c==2 for c in solution.values()),
          'proof':proof,'status':'UNVERIFIED native colour and shape probe'}
        reports.append(report);write('puzzle/'+filename,data)
    p[secondary:secondary]=b''.join(new)
    struct.pack_into('<H',p,8,count+2);struct.pack_into('<I',p,20,secondary+808)
    write('master/default.pms',p)
    for language in ('en','fr','de','es','it'):
        for resource in ('PuzzleName','PuzzleNo','Trivia'):
            path=f'text/{language}/{resource}.msbt';m=MessageFile((OUT/'romfs'/path).read_bytes())
            for slot in (1,2):
                id=60000+slot
                label=f'PUZZLE_NO_{id}' if resource=='PuzzleNo' else f'PUZZLE_NAME_{id}'
                text=(f'C00{slot+1}' if resource=='PuzzleNo' else
                  ('Two-colour Torpedo' if slot==1 else 'Shaped Block Probe') if resource=='PuzzleName' else
                  ('Blue and orange cube test.\nThe body and tips use\ndifferent marking colours.' if slot==1 else
                   'A diagnostic shape test.\nOrange blocks use different\nsurfaces. The final model is\nthe shared torpedo preview.'))
                m.set(label,text)
            data=m.write();MessageFile(data);write(path,data)
    (OUT/'proofs.json').write_text(json.dumps(reports,indent=2))
    manifest={'revision':4,'status':'Colour and shape experiments, not yet emulator verified',
      'save_indices':[395,396,397],
      'files':sorted(f.relative_to(OUT/'romfs').as_posix() for f in (OUT/'romfs').rglob('*') if f.is_file() and f.suffix!='.png')}
    (OUT/'package.json').write_text(json.dumps(manifest,indent=2))
    print('PASS: two additive probe entries, distinct IDs, full clues; ternary solver settles all 250 cells each')
    print([(r['id'],r['blue'],r['orange'],len(r['proof'])) for r in reports])
if __name__=='__main__':build()

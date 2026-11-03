"""Independent certificate replay by exhaustive short-row enumeration."""
import functools,itertools
from clue_difficulty import PLANES
@functools.lru_cache(None)
def possibilities(length,blue,orange,groups):
    result=[]
    for row in itertools.product((0,1,2),repeat=length):
        if row.count(1)!=blue or row.count(2)!=orange:continue
        signature=[]
        for colour in (1,2):
            previous=False;n=0
            for value in row:
                current=value==colour
                n+=int(current and not previous);previous=current
            signature.append(min(3,n))
        if tuple(signature)==groups:result.append(row)
    return tuple(result)
def verify(puzzle,proof,mode):
    solution={(xy&15,xy>>4,zc&15):1 if shape==0 else 2 for shape,xy,zc,_ in puzzle.voxels}
    table={}
    for plane,(a,b,axis) in enumerate(PLANES):
        for v in range(puzzle.dimensions[b]):
            for u in range(puzzle.dimensions[a]):
                index=u+v*puzzle.dimensions[a]
                if not puzzle.masks[mode*3+plane][index]:continue
                cells=[tuple(n if k==axis else u if k==a else v for k in range(3)) for n in range(puzzle.dimensions[axis])]
                values=[solution.get(p,0) for p in cells]
                groups=tuple(min(3,sum(value==c and (i==0 or values[i-1]!=c) for i,value in enumerate(values))) for c in (1,2))
                table[plane,index]=(cells,possibilities(len(cells),values.count(1),values.count(2),groups))
    known={}
    for step in proof:
        cells,candidates=table[step['plane'],step['index']]
        remaining=[r for r in candidates if all(p not in known or known[p]==value for p,value in zip(cells,r))]
        assert remaining and len(remaining)==step['candidate_count']
        for raw,value in step['moves']:
            p=tuple(raw);assert p in cells and p not in known
            i=cells.index(p);assert {r[i] for r in remaining}=={value},'Unjustified move'
            known[p]=value
    assert len(known)==puzzle.dimensions[0]*puzzle.dimensions[1]*puzzle.dimensions[2]
    assert all(value==solution.get(p,0) for p,value in known.items())
    return len(known)

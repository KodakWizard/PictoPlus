"""Count-only two-colour line solver, with no solution lookahead."""
import itertools
from functools import lru_cache
from clue_difficulty import PLANES

def group_signature(row):
    return tuple(min(3,sum(value==colour and (i==0 or row[i-1]!=colour) for i,value in enumerate(row))) for colour in (1,2))

@lru_cache(maxsize=4096)
def line_candidates(length,blue,orange,signature):
    candidates=[]
    for first in itertools.combinations(range(length),blue):
        rest=[i for i in range(length) if i not in first]
        for second in itertools.combinations(rest,orange):
            row=[0]*length
            for i in first:row[i]=1
            for i in second:row[i]=2
            if signature is None or group_signature(row)==signature:candidates.append(tuple(row))
    return tuple(candidates)

@lru_cache(maxsize=32768)
def line_deductions(length,blue,orange,signature,known):
    fixed=[(i,v) for i,v in enumerate(known) if v>=0]
    candidates=[row for row in line_candidates(length,blue,orange,signature) if all(row[i]==value for i,value in fixed)]
    assert candidates
    moves=[]
    for i,value in enumerate(known):
        if value>=0:continue
        options={row[i] for row in candidates}
        if len(options)==1:moves.append((i,options.pop()))
    return len(candidates),tuple(moves)

def solve(dimensions,solution,masks=None,use_groups=False):
    lines=[]
    for plane,(a,b,axis) in enumerate(PLANES):
        for v in range(dimensions[b]):
            for u in range(dimensions[a]):
                if masks is not None and not masks[plane][u+v*dimensions[a]]:continue
                cells=[]
                for n in range(dimensions[axis]):
                    p=[0,0,0];p[a]=u;p[b]=v;p[axis]=n;cells.append(tuple(p))
                blue=sum(solution.get(p,0)==1 for p in cells)
                orange=sum(solution.get(p,0)==2 for p in cells)
                signature=group_signature([solution.get(p,0) for p in cells])
                lines.append((plane,u+v*dimensions[a],cells,blue,orange,signature if use_groups else None))
    known={};proof=[]
    while True:
        before=len(known)
        for plane,index,cells,blue,orange,signature in lines:
            count,forced=line_deductions(len(cells),blue,orange,signature,tuple(known.get(p,-1) for p in cells))
            moves=[(cells[i],value) for i,value in forced]
            if moves:
                proof.append({'plane':plane,'index':index,'candidate_count':count,'moves':moves})
                known.update(moves)
        if len(known)==before:break
    assert len(known)==dimensions[0]*dimensions[1]*dimensions[2],('Stalled',len(known))
    assert all(known[p]==solution.get(p,0) for p in known)
    return proof

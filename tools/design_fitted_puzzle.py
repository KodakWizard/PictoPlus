"""Select clue layouts for fitted colours, retaining no-guessing group proofs."""
import collections,itertools,json,pathlib,random
from clue_difficulty import PLANES
from colour_logic import solve,group_signature
ROOT=pathlib.Path(__file__).resolve().parents[1]
def catalogue(dims,solution):
    rows=[]
    for plane,(a,b,axis) in enumerate(PLANES):
        for v in range(dims[b]):
            for u in range(dims[a]):
                cells=[tuple(n if k==axis else u if k==a else v for k in range(3)) for n in range(dims[axis])]
                values=[solution.get(p,0) for p in cells]
                rows.append({'plane':plane,'index':u+v*dims[a],'cells':cells,
                    'counts':tuple(values.count(c) for c in (1,2)),'groups':group_signature(values)})
    return rows
def zero_envelope(rows,masks,total):
    removed={p for row in rows if masks[row['plane']][row['index']] and not sum(row['counts']) for p in row['cells']}
    return total-len(removed)
def build():
    fit=json.loads((ROOT/'build/fitted-torpedo.json').read_text());dims=tuple(fit['dimensions'])
    solution={tuple(c['xyz']):1 if c['shape']==0 else 2 for c in fit['cells']}
    rows=catalogue(dims,solution);frequencies=collections.Counter(r['counts'] for r in rows)
    masks=[bytearray([1])*(dims[a]*dims[b]) for a,b,_ in PLANES]
    # Interleave zero clues and repeated nonzero clues. Keep useful grouping
    # clues available; solver certification, not this heuristic, decides validity.
    zeros=[r for r in rows if sum(r['counts'])==0]
    ordinary=[r for r in rows if sum(r['counts']) and max(r['groups'])<2]
    groups=[r for r in rows if max(r['groups'])>=2]
    rng=random.Random(60007)
    for part in (zeros,ordinary,groups):rng.shuffle(part)
    ordinary.sort(key=lambda r:-frequencies[r['counts']])
    order=[]
    while zeros or ordinary or groups:
        for part in (zeros,ordinary,ordinary,groups):
            if part:order.append(part.pop(0))
    modes=[];removed=0
    for target in (5,20,35,50,65):
        for row in order:
            if removed==target:break
            plane,index=row['plane'],row['index']
            if not masks[plane][index]:continue
            masks[plane][index]=0
            try:solve(dims,solution,masks,True)
            except AssertionError:masks[plane][index]=1
            else:removed+=1
        assert removed==target,('Insufficient certified removals',target,removed)
        proof=solve(dims,solution,masks,True)
        count_only=True
        try:solve(dims,solution,masks,False)
        except AssertionError:count_only=False
        shown=[r for r in rows if masks[r['plane']][r['index']]]
        modes.append({'mode':len(modes),'masks':[list(m) for m in masks],
            'visible_clues':sum(map(sum,masks)),'after_zero_sweep':zero_envelope(rows,masks,250),
            'visible_circle_clues':sum(g==2 for r in shown for g in r['groups']),
            'visible_square_clues':sum(g==3 for r in shown for g in r['groups']),
            'count_only_solved':count_only,'proof':proof})
    assert modes[0]['after_zero_sweep']<modes[1]['after_zero_sweep']<modes[4]['after_zero_sweep']
    assert all(m['visible_circle_clues'] for m in modes)
    (ROOT/'build/fitted-torpedo-design.json').write_text(json.dumps({'status':'offline-certified; native playtest pending','modes':modes},indent=2))
    print([(m['mode'],m['visible_clues'],m['after_zero_sweep'],m['visible_circle_clues'],m['count_only_solved']) for m in modes])
if __name__=='__main__':build()

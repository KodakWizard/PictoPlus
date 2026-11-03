import random

# Native indexing traced at ARM 0x2031a8..0x20333c: X+Y*Xdim,
# X+Z*Xdim, Z+Y*Zdim. Do not infer this from plane names.
PLANES=((0,1,2),(0,2,1),(2,1,0))

def visible_lines(dimensions, occupied, masks):
    result=[]
    for plane,(a,b,axis) in enumerate(PLANES):
        assert len(masks[plane])==dimensions[a]*dimensions[b]
        for v in range(dimensions[b]):
            for u in range(dimensions[a]):
                index=u+v*dimensions[a]
                if not masks[plane][index]:continue
                coords=[]
                for n in range(dimensions[axis]):
                    p=[0,0,0];p[a]=u;p[b]=v;p[axis]=n;coords.append(tuple(p))
                result.append({'plane':plane,'index':index,'axis':axis,
                    'coords':coords,'count':sum(p in occupied for p in coords)})
    return result

def deduce(visible):
    """No access to geometry, groups, hidden clues, or future moves."""
    known={};steps=[]
    while True:
        before=len(known)
        for line in visible:
            unknown=[p for p in line['coords'] if p not in known]
            remaining=line['count']-sum(known.get(p,0) for p in line['coords'])
            if not 0<=remaining<=len(unknown):raise ValueError('Contradictory line')
            if not unknown or remaining not in (0,len(unknown)):continue
            value=int(remaining!=0)
            steps.append({'plane':line['plane'],'index':line['index'],
                'value':value,'cells':unknown,'remaining':remaining,
                'reason':'all remaining cells occupied' if value else 'all remaining cells empty'})
            known.update((p,value) for p in unknown)
        if len(known)==before:return known,steps

def replay(dimensions, occupied, masks, steps):
    table={(l['plane'],l['index']):l for l in visible_lines(dimensions,occupied,masks)}
    known={}
    for step in steps:
        line=table[step['plane'],step['index']]
        unknown=[p for p in line['coords'] if p not in known]
        assert unknown and list(map(tuple,step['cells']))==unknown
        remaining=line['count']-sum(known.get(p,0) for p in line['coords'])
        assert remaining in (0,len(unknown))
        assert step['value']==int(remaining!=0) and step['remaining']==remaining
        known.update((p,step['value']) for p in unknown)
    assert len(known)==dimensions[0]*dimensions[1]*dimensions[2]
    assert {p for p,value in known.items() if value}==occupied
    return len(known)

def generate(dimensions, occupied):
    """Thin all clue types, accepting only layouts with count-only solutions."""
    masks=[bytearray([1])*(dimensions[a]*dimensions[b]) for a,b,_ in PLANES]
    modes=[[bytes(m) for m in masks]]
    order=[(l['plane'],l['index']) for l in visible_lines(dimensions,occupied,masks)]
    random.Random(60000).shuffle(order);removed=0
    for target in (15,30,45,55):
        for plane,index in order:
            if removed>=target:break
            if not masks[plane][index]:continue
            masks[plane][index]=0
            known,_=deduce(visible_lines(dimensions,occupied,masks))
            if len(known)==dimensions[0]*dimensions[1]*dimensions[2]:removed+=1
            else:masks[plane][index]=1
        assert removed==target,('No certified thinning available',removed,target)
        modes.append([bytes(m) for m in masks])
    for mode in modes:
        _,steps=deduce(visible_lines(dimensions,occupied,mode));replay(dimensions,occupied,mode,steps)
    return [mask for mode in modes for mask in mode],[sum(map(sum,mode)) for mode in modes]


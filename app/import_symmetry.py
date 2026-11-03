"""Detect actual source symmetry and fit mirrored native orientations jointly."""
import functools,itertools

def source_axes(triangles,dimensions):
    points={tuple(round(v,4) for v in p) for t in triangles for p in t}
    axes=[]
    for axis in range(3):
        reflected={tuple(round(dimensions[a]-p[a],4) if a==axis else p[a] for a in range(3)) for p in points}
        if points and len(points&reflected)/len(points)>=.995:axes.append(axis)
    return axes

def reflect_position(xyz,dimensions,axis):
    return tuple(dimensions[a]-1-v if a==axis else v for a,v in enumerate(xyz))

def reflect_mask(mask,axis):
    result=0
    for i in range(64):
        if mask>>i&1:
            p=[i//16,i//4%4,i%4];p[axis]=3-p[axis]
            result|=1<<(p[0]*16+p[1]*4+p[2])
    return result

@functools.lru_cache(maxsize=1)
def reflection_tables():
    from fit_native_shapes import variants
    meshes=variants()
    def key(points):return tuple(sorted({tuple(round(v,5) for v in p) for p in points}))
    lookup={key(p for t in v['triangles'] for p in t):v['id'] for v in reversed(meshes)}
    return [{v['id']:lookup.get(key(tuple(-n if a==axis else n for a,n in enumerate(p)) for t in v['triangles'] for p in t)) for v in meshes} for axis in range(3)]

def orbits(positions,dimensions,axes):
    unseen=set(positions);groups=[]
    while unseen:
        first=min(unseen);group={first}
        for axis in axes:group|={reflect_position(p,dimensions,axis) for p in list(group)}
        group&=unseen;unseen-=group;groups.append(sorted(group))
    return groups

def fit_mirrors(cells,dimensions,axes,targets,variants,blue,yellow):
    if not axes:return []
    groups=orbits((tuple(c['xyz']) for c in cells),dimensions,axes)
    table=reflection_tables();masks=dict(variants);masks[0]=(1<<64)-1;by_position={tuple(c['xyz']):c for c in cells}
    for group in groups:
        origin=group[0];old_yellow=sum(bool(by_position[p]['shape']) for p in group)
        colour=None if old_yellow*2==len(group) else old_yellow*2>len(group)
        best=None
        for shape,mask in masks.items():
            if (not blue and not shape) or (not yellow and shape):continue
            if colour is not None and bool(shape)!=colour:continue
            orientations={origin:shape};valid=True
            for axis in axes:
                for p,current in list(orientations.items()):
                    q=reflect_position(p,dimensions,axis);mirror=table[axis].get(current)
                    if mirror is None or (q in orientations and orientations[q]!=mirror and masks[orientations[q]]!=masks[mirror]):valid=False;break
                    orientations[q]=mirror
                if not valid:break
            if not valid or any(p not in orientations for p in group):continue
            cost=sum((targets[p]&~masks[orientations[p]]).bit_count()*3+(masks[orientations[p]]&~targets[p]).bit_count()+(3 if shape else 0) for p in group)
            candidate=(cost,shape,orientations)
            if best is None or candidate[:2]<best[:2]:best=candidate
        if best is not None:
            for p in group:by_position[p]['shape']=best[2][p]
        elif blue:
            for p in group:by_position[p]['shape']=0
    return groups

def fit_matching_surfaces(cells,targets,variants,blue,yellow,depth,planar=None,dimensions=None,source_symmetry=(),boxlike=None):
    """Match reflected local volumes without mirroring asymmetric scene parts."""
    from import_surfaces import CURVED_IDS,BOX_IDS
    planar=planar or set()
    boxlike=boxlike or set()
    tables=reflection_tables();masks=dict(variants);masks[0]=(1<<64)-1
    flips=list(itertools.product((False,True),repeat=3));groups={}
    def flip_mask(mask,flags):
        for axis,flag in enumerate(flags):
            if flag:mask=reflect_mask(mask,axis)
        return mask
    for c in cells:
        xyz=tuple(c['xyz']);target=targets[xyz]
        canonical=min(flip_mask(target,f) for f in flips)
        wanted=tuple(dimensions is not None and xyz[a]+.5>dimensions[a]/2 for a in range(3))
        flags=min((f for f in flips if flip_mask(target,f)==canonical),key=lambda f:sum(a!=b for a,b in zip(f,wanted)))
        groups.setdefault((canonical,bool(depth.get(xyz,0)),xyz in planar,xyz in boxlike),[]).append((c,flags))
    linked=[]
    for (target,interior,is_planar,is_box),members in groups.items():
        best=None
        required_self_axes={axis for axis in source_symmetry if any(abs(c['xyz'][axis]+.5-dimensions[axis]/2)<1e-8 for c,_ in members)}
        for shape,mask in masks.items():
            if (not blue and not shape) or (not yellow and shape) or (interior and blue and shape and target.bit_count()>=48):continue
            # Only an actual source symmetry plane through a cell requires a
            # self-mirrored solid. Coarse symmetric samples alone must not force
            # a sphere onto a small rectangular deck or cabin.
            if any(tables[axis].get(shape) is None or masks[tables[axis][shape]]!=mask for axis in required_self_axes):continue
            orientations=[];valid=True
            for c,flags in members:
                current=shape
                for axis,flag in enumerate(flags):
                    if flag:current=tables[axis].get(current)
                    if current is None:valid=False;break
                if not valid:break
                orientations.append(current)
            if not valid:continue
            cost=(target&~mask).bit_count()*3+(mask&~target).bit_count()+(3 if shape else 0)+(24 if is_planar and shape in CURVED_IDS else 0)+(48 if is_box and shape not in BOX_IDS else 0)
            if best is None or (cost,shape)<best[:2]:best=(cost,shape,orientations)
        if best:
            for (c,_),shape in zip(members,best[2]):c['shape']=shape
            if len(members)>1:linked.append([tuple(c['xyz']) for c,_ in members])
    return linked

"""Retain native face contacts where the original surface crosses a cell edge."""
import functools,itertools,math

@functools.lru_cache(maxsize=1)
def bounds():
    from fit_native_shapes import variants
    return {v['id']:tuple((min(p[a] for t in v['triangles'] for p in t),max(p[a] for t in v['triangles'] for p in t)) for a in range(3)) for v in variants()}

def source_contacts(triangles,positions):
    from voxelise import overlap
    contacts={p:set() for p in positions}
    for triangle in triangles:
        lo=[min(p[a] for p in triangle) for a in range(3)];hi=[max(p[a] for p in triangle) for a in range(3)]
        ranges=[range(math.floor(lo[a]),math.floor(hi[a])+1) for a in range(3)]
        hit={p for p in itertools.product(*ranges) if p in positions and overlap(triangle,p)}
        for p in hit:
            for axis in range(3):
                for sign in (-1,1):
                    face=p[axis]+(sign>0);q=list(p);q[axis]+=sign;q=tuple(q)
                    if q in hit and lo[axis]<face-1e-6 and hi[axis]>face+1e-6:contacts[p].add((axis,sign))
    return contacts

def contact_points(triangles,positions):
    """Midpoints of clipped source segments crossing each shared voxel face."""
    from voxelise import overlap
    result={p:{} for p in positions}
    for t in triangles:
        lo=[min(p[a] for p in t) for a in range(3)];hi=[max(p[a] for p in t) for a in range(3)]
        hit={p for p in itertools.product(*(range(math.floor(lo[a]),math.floor(hi[a])+1) for a in range(3))) if p in positions and overlap(t,p)}
        for p in hit:
            for axis in range(3):
                other=[a for a in range(3) if a!=axis]
                for sign in (-1,1):
                    q=list(p);q[axis]+=sign;q=tuple(q);plane=p[axis]+(sign>0)
                    if q not in hit or not lo[axis]<plane-1e-6 or not hi[axis]>plane+1e-6:continue
                    points=[]
                    for a,b in zip(t,t[1:]+t[:1]):
                        if abs(b[axis]-a[axis])<1e-10:continue
                        u=(plane-a[axis])/(b[axis]-a[axis])
                        if 0<=u<=1:points.append([a[k]+u*(b[k]-a[k]) for k in other])
                    if len(points)<2:continue
                    a,b=points[:2];start,end=0.,1.
                    for i,k in enumerate(other):
                        delta=b[i]-a[i]
                        if abs(delta)<1e-10:
                            if not p[k]-1e-7<=a[i]<=p[k]+1+1e-7:start,end=1,0
                        else:
                            u,v=sorted(((p[k]-a[i])/delta,(p[k]+1-a[i])/delta));start=max(start,u);end=min(end,v)
                    if start>end:continue
                    u=(start+end)/2;point=tuple(round(a[i]+u*(b[i]-a[i])-p[k]-.5,2) for i,k in enumerate(other))
                    result[p].setdefault((axis,sign),set()).add(point)
    return result

@functools.lru_cache(maxsize=1)
def face_hulls():
    from fit_native_shapes import variants
    result={}
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    for v in variants():
        for axis in range(3):
            other=[a for a in range(3) if a!=axis]
            for sign in (-1,1):
                points=sorted({tuple(round(p[k],5) for k in other) for t in v['triangles'] for p in t if p[axis]*sign>=.485})
                lower=[];upper=[]
                for p in points:
                    while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
                    lower.append(p)
                for p in reversed(points):
                    while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
                    upper.append(p)
                result[v['id'],axis,sign]=lower[:-1]+upper[:-1] if len(points)>1 else points
    return result

def covers(hull,point):
    if not hull:return False
    if len(hull)==1:return math.dist(hull[0],point)<.08
    signs=[]
    for a,b in zip(hull,hull[1:]+hull[:1]):
        edge=(b[0]-a[0],b[1]-a[1]);cross=edge[0]*(point[1]-a[1])-edge[1]*(point[0]-a[0])
        if abs(cross)>.045:signs.append(cross>0)
    return len(hull)>2 and (not signs or all(v==signs[0] for v in signs))

def repair(cells,triangles,targets,variants,blue,yellow,planar,boxlike,preserve_colour=False):
    from import_surfaces import CURVED_IDS,BOX_IDS
    extents=bounds();contacts=contact_points(triangles,{tuple(c['xyz']) for c in cells});hulls=face_hulls();masks=dict(variants);masks[0]=(1<<64)-1
    changed=0
    for cell in cells:
        p=tuple(cell['xyz']);needed=contacts[p];target=targets[p]
        def gaps(shape):return sum(not all(covers(hulls[shape,a,sign],point) for point in points) for (a,sign),points in needed.items())
        if not needed or not gaps(cell['shape']):continue
        choices=[(shape,mask) for shape,mask in masks.items() if (blue or shape!=0) and (yellow or shape==0) and (not preserve_colour or bool(shape)==bool(cell['shape']))]
        def cost(pair):
            shape,mask=pair
            return (gaps(shape)*160+(target&~mask).bit_count()*3+(mask&~target).bit_count()+(3 if shape else 0)+(24 if p in planar and shape in CURVED_IDS else 0)+(48 if p in boxlike and shape not in BOX_IDS else 0),shape)
        cell['shape']=min(choices,key=cost)[0];changed+=1
    return changed

def balance(cells,targets,variants,blue,yellow):
    """Keep a small colour minority only for automatic, mixed-colour fitting."""
    if not (blue and yellow) or len(cells)<4:return
    masks=dict(variants);masks[0]=(1<<64)-1
    minimum=max(1,min(4,round(len(cells)*.05)))
    blue_count=sum(c['shape']==0 for c in cells)
    if blue_count<minimum:
        candidates=sorted((c for c in cells if c['shape']),key=lambda c:((masks[0]^targets[tuple(c['xyz'])]).bit_count(),c['xyz']))
        for cell in candidates[:minimum-blue_count]:cell['shape']=0
    yellow_count=sum(c['shape']!=0 for c in cells)
    if yellow_count<minimum:
        choices=[]
        for cell in cells:
            if cell['shape']:continue
            target=targets[tuple(cell['xyz'])]
            shape,mask=min(((s,m) for s,m in variants if s),key=lambda pair:((target&~pair[1]).bit_count()*3+(pair[1]&~target).bit_count(),pair[0]))
            choices.append(((target&~mask).bit_count()*3+(mask&~target).bit_count(),cell['xyz'],cell,shape))
        for _,_,cell,shape in sorted(choices,key=lambda item:item[:2])[:minimum-yellow_count]:cell['shape']=shape

def prune_small_orphans(cells):
    """Drop tiny fitted fragments left unsupported at the grid resolution.

    Voxel adjacency alone is insufficient: two small corner cubes can occupy
    neighbouring cells while having a visible gap between their actual meshes.
    Keep large/disconnected model parts and all small complete puzzles.
    """
    if len(cells)<12:return cells
    extent=bounds();by_position={tuple(c['xyz']):c for c in cells};unseen=set(by_position);groups=[]
    def touches(p,q):
        a=extent[by_position[p]['shape']];b=extent[by_position[q]['shape']]
        return all(min(p[i]+a[i][1],q[i]+b[i][1])-max(p[i]+a[i][0],q[i]+b[i][0])>=-1e-5 for i in range(3))
    while unseen:
        group={unseen.pop()};queue=list(group)
        while queue:
            p=queue.pop()
            for delta in itertools.product((-1,0,1),repeat=3):
                q=tuple(p[a]+delta[a] for a in range(3))
                if q in unseen and touches(p,q):unseen.remove(q);group.add(q);queue.append(q)
        groups.append(group)
    largest=max(map(len,groups));remove=set()
    for group in groups:
        volume=sum(math.prod(hi-lo for lo,hi in extent[by_position[p]['shape']]) for p in group)
        if len(group)<=2 and len(group)<largest and volume<.8:remove.update(group)
    return [c for c in cells if tuple(c['xyz']) not in remove]

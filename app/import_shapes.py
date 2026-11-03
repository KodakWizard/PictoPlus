"""Fit native blue/yellow solids to sampled source volume, never random shapes."""
import bisect,collections,functools,json,math,pathlib
import game_resources

@functools.lru_cache(maxsize=1)
def catalogue():
    data=json.loads((game_resources.generated()/'native-shape-samples.json').read_text())
    return data['offsets'],[(r['shape'],int(r['mask'],16)) for r in data['variants']]

def fit(triangles,dimensions,cells,blue=True,yellow=True,yellow_ratio=None,metrics=None,blue_inside=False,automatic_balance=False):
    assert blue or yellow,'Select blue blocks, yellow shapes, or both.'
    assert yellow_ratio is None or type(yellow_ratio) in (int,float) and 0<=yellow_ratio<=100,'Choose a yellow ratio from 0 to 100.'
    from import_symmetry import source_axes,reflect_position,reflect_mask,fit_mirrors,fit_matching_surfaces
    symmetry_axes=source_axes(triangles,dimensions)
    positions={tuple(c['xyz']) for c in cells}
    for axis in symmetry_axes:positions|={reflect_position(p,dimensions,axis) for p in list(positions)}
    cells=[{'xyz':list(p),'shape':0} for p in sorted(positions)]
    from import_surfaces import flat_cells,CURVED_IDS,BOX_IDS
    boxlike=set();planar=flat_cells(triangles,cells,boxlike)
    # Shared positions connect triangles across normal/UV seams. Disconnected
    # closed parts are unioned, so overlapping foliage does not cancel out.
    parent=list(range(len(triangles)));vertices={}
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,t in enumerate(triangles):
        for p in t:
            key=tuple(round(v,6) for v in p)
            if key in vertices:parent[root(i)]=root(vertices[key])
            else:vertices[key]=i
    edges=collections.defaultdict(collections.Counter)
    for i,t in enumerate(triangles):
        points=[tuple(round(v,6) for v in p) for p in t]
        for a,b in zip(points,points[1:]+points[:1]):
            if a!=b:edges[root(i)][tuple(sorted((a,b)))]+=1
    open_parts={part for part,counts in edges.items() if any(n%2 for n in counts.values())}
    # Preserve genuinely open sheets, but do not inflate every grazing contact
    # on a closed solid into a full cube.
    open_cells=set()
    if open_parts:
        import itertools
        from voxelise import overlap
        occupied={tuple(c['xyz']) for c in cells}
        for i,t in enumerate(triangles):
            if root(i) not in open_parts:continue
            ranges=[range(max(0,math.floor(min(p[a] for p in t))),min(dimensions[a]-1,math.floor(max(p[a] for p in t)))+1) for a in range(3)]
            for xyz in itertools.product(*ranges):
                if xyz in occupied and xyz not in open_cells and overlap(t,xyz):open_cells.add(xyz)
    rays=collections.defaultdict(lambda:collections.defaultdict(list))
    for i,(a,b,c) in enumerate(triangles):
        e=[b[k]-a[k] for k in range(3)];f=[c[k]-a[k] for k in range(3)];det=e[1]*f[2]-e[2]*f[1]
        if abs(det)<1e-10:continue
        ranges=[range(max(0,math.ceil(4*(min(p[k] for p in (a,b,c))-(.000319 if k==1 else .000547))-.5-1e-8)),min(dimensions[k]*4-1,math.floor(4*(max(p[k] for p in (a,b,c))-(.000319 if k==1 else .000547))-.5+1e-8))+1) for k in (1,2)]
        for iy in ranges[0]:
            y=(iy+.5)/4+.000319-a[1]
            for iz in ranges[1]:
                z=(iz+.5)/4+.000547-a[2];u=(y*f[2]-z*f[1])/det;v=(e[1]*z-e[2]*y)/det
                if u>=-1e-8 and v>=-1e-8 and u+v<=1+1e-8:rays[iy,iz][root(i)].append((a[0]+u*e[0]+v*f[0],1 if det>0 else -1))
    for key,parts in list(rays.items()):
        closed=[]
        for hits in parts.values():
            events=[]
            for x,sign in sorted(hits):
                if events and x-events[-1][0]<=1e-6:events[-1][1].add(sign)
                else:events.append([x,{sign}])
            # Coincident opposite faces are internal boundaries, not holes.
            # Signed crossings also keep overlapping connected solids filled.
            winding=0;intervals=[]
            for x,signs in events:
                before=winding;winding+=sum(signs)
                if not before and winding:intervals.append(x)
                elif before and not winding:intervals.append(x)
            if intervals and winding==0 and len(intervals)%2==0:closed.append(intervals)
        rays[key]=closed
    depth={}
    if blue_inside and blue:
        occupied={tuple(c['xyz']) for c in cells}
        def neighbours(p):
            for axis in range(3):
                for step in (-1,1):
                    q=list(p);q[axis]+=step;yield tuple(q)
        queue=collections.deque()
        for p in occupied:
            if any(q not in occupied for q in neighbours(p)):depth[p]=0;queue.append(p)
        while queue:
            p=queue.popleft()
            for q in neighbours(p):
                if q in occupied and q not in depth:depth[q]=depth[p]+1;queue.append(q)
    offsets,variants=catalogue();full=(1<<len(offsets))-1;fitted=[];improvement={};choices=[];targets={}
    for cell in cells:
        x,y,z=cell['xyz'];target=0
        for index,(dx,dy,dz) in enumerate(offsets):
            sx=x+.5+dx;iy=round((y+.5+dy)*4-.5);iz=round((z+.5+dz)*4-.5)
            if any(bisect.bisect_right(hits,sx)%2 for hits in rays.get((iy,iz),())):target|=1<<index
        targets[tuple(cell['xyz'])]=target
    # Remove sampling-direction bias before choosing occupancy or orientation.
    for axis in symmetry_axes:
        for xyz in list(targets):
            other=reflect_position(xyz,dimensions,axis)
            targets[xyz]|=reflect_mask(targets[other],axis)
    for cell in cells:
        target=targets[tuple(cell['xyz'])]
        # Reject tiny closed-solid slivers instead of surrounding the model
        # with unrelated blue cubes. Open sheets retain conservative coverage.
        if target.bit_count()<4 and tuple(cell['xyz']) not in open_cells:continue
        # Open/thin surfaces with no reliable volume samples keep their cubes.
        best=0;best_cost=(full^target).bit_count() if target else 0
        baseline=best_cost
        yellow_best=None;yellow_cost=float('inf')
        if target:
            for shape,mask in variants:
                if not shape:continue
                missing=(target&~mask).bit_count();excess=(mask&~target).bit_count()
                cost=missing*3+excess+3+(24 if tuple(cell['xyz']) in planar and shape in CURVED_IDS else 0)+(48 if tuple(cell['xyz']) in boxlike and shape not in BOX_IDS else 0)
                if cost<yellow_cost:yellow_best,yellow_cost=shape,cost
                if cost<best_cost:best,best_cost=shape,cost
        if yellow_best is None:
            # A thin open sheet has no inside samples. Prefer a thin slab,
            # rather than an arbitrary rounded shape, for yellow-only output.
            yellow_best=182;yellow_cost=baseline+64
        # A rectangular sample volume represents straight faces and corners.
        # Prefer full blue cells for substantial box-like regions; keep yellow
        # fits at sparse boundaries and on genuinely curved/diagonal surfaces.
        points=[offsets[i] for i in range(len(offsets)) if target>>i&1]
        rectangular=bool(points) and len(points)==math.prod(len({p[a] for p in points}) for a in range(3))
        benefit=baseline-yellow_cost-(18 if rectangular and len(points)>=32 else 0)
        if rectangular and len(points)>=32 and benefit<=0:best=0
        interior_depth=depth.get(tuple(cell['xyz']),0)
        benefit-=64*interior_depth
        if interior_depth and len(points)>=48:best=0
        fitted.append({'xyz':list(cell['xyz']),'shape':best})
        choices.append((benefit,tuple(cell['xyz']),yellow_best))
        if best:improvement[tuple(cell['xyz'])]=baseline-best_cost
    if not yellow:
        for c in fitted:c['shape']=0
    elif not blue or yellow_ratio is not None:
        count=len(fitted) if not blue else round(len(fitted)*yellow_ratio/100)
        selected={xyz:shape for _,xyz,shape in sorted(choices,reverse=True)[:count]}
        for c in fitted:
            xyz=tuple(c['xyz']);c['shape']=selected.get(xyz,0)
            if c['shape']:improvement[xyz]=next(b for b,p,_ in choices if p==xyz)
    matching_groups=fit_matching_surfaces(fitted,targets,variants,blue,yellow,depth,planar,dimensions,symmetry_axes,boxlike) if yellow_ratio is None else []
    symmetry_groups=fit_mirrors(fitted,dimensions,symmetry_axes,targets,variants,blue,yellow)+matching_groups
    from import_contacts import repair,balance,prune_small_orphans
    contact_repairs=repair(fitted,triangles,targets,variants,blue,yellow,planar,boxlike,preserve_colour=yellow_ratio is not None)
    fitted=prune_small_orphans(fitted)
    if automatic_balance and yellow_ratio is None:balance(fitted,targets,variants,blue,yellow)
    if metrics is not None:
        metrics['contact_repairs']=contact_repairs
        masks=dict(variants);masks[0]=full
        selected={tuple(c['xyz']):masks[c['shape']] for c in fitted}
        intersection=sum((target&selected.get(xyz,0)).bit_count() for xyz,target in targets.items())
        union=sum((target|selected.get(xyz,0)).bit_count() for xyz,target in targets.items())
        metrics['volume_similarity']=intersection/max(1,union)
        metrics['symmetry_axes']=symmetry_axes
        metrics['symmetry_groups']=symmetry_groups
        metrics['matching_surface_groups']=len(matching_groups)
    return fitted,improvement

def certify_colours(dimensions,cells,improvement,allow_blue=True,symmetry_groups=None):
    from colour_logic import solve
    removed=0
    while True:
        try:
            solve(tuple(dimensions),{tuple(c['xyz']):1 if c['shape']==0 else 2 for c in cells},use_groups=True)
            return removed,True
        except AssertionError:
            if not allow_blue:return removed,False
            yellow=sorted((c for c in cells if c['shape']),key=lambda c:improvement.get(tuple(c['xyz']),0))
            if not yellow:return removed,False
            # Restore the least useful fits in batches; never change the occupied
            # cell layout to manufacture a solvable colour assignment.
            selected={tuple(c['xyz']) for c in yellow[:max(1,len(yellow)//8)]}
            while True:
                before=len(selected)
                for group in symmetry_groups or []:
                    if selected.intersection(group):selected.update(group)
                if len(selected)==before:break
            for cell in yellow:
                if tuple(cell['xyz']) in selected:cell['shape']=0;removed+=1

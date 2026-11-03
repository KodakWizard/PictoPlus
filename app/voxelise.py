"""Conservative triangle/voxel overlap followed by exterior flood filling.

Surface sampling at cell centres loses thin, open model parts (aircraft wings).
The separating-axis test includes every intersected voxel, irrespective of winding.
"""
import collections,itertools,math

def overlap(triangle,cell):
    points=[tuple(p[a]-cell[a]-.5 for a in range(3)) for p in triangle]
    edges=[tuple(points[(i+1)%3][a]-points[i][a] for a in range(3)) for i in range(3)]
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    axes=[(1,0,0),(0,1,0),(0,0,1),cross(edges[0],edges[1])]
    axes += [cross(edge,axis) for edge in edges for axis in ((1,0,0),(0,1,0),(0,0,1))]
    for axis in axes:
        if sum(n*n for n in axis)<1e-18:continue
        distances=[sum(p[a]*axis[a] for a in range(3)) for p in points]
        radius=.5*sum(abs(n) for n in axis)
        if min(distances)>radius+1e-8 or max(distances)<-radius-1e-8:return False
    return True

def convert(triangles,dimensions):
    assert len(dimensions)==3 and all(type(n)==int and 1<=n<=10 for n in dimensions),'Choose a grid from 1 to 10 on each axis.'
    assert 0<len(triangles)<=20000,'Choose a model with 1–20,000 triangles.'
    assert all(len(t)==3 and all(len(p)==3 and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<1e8 for v in p) for p in t) for t in triangles),'Invalid model geometry.'
    lo=[min(p[a] for t in triangles for p in t) for a in range(3)];hi=[max(p[a] for t in triangles for p in t) for a in range(3)]
    scale=min((dimensions[a]-.2)/max(hi[a]-lo[a],.001) for a in range(3))
    transformed=[[[ (p[a]-(lo[a]+hi[a])/2)*scale+dimensions[a]/2 for a in range(3)] for p in t] for t in triangles]
    surface=set()
    for triangle in transformed:
        ranges=[range(max(0,math.floor(min(p[a] for p in triangle))),min(dimensions[a]-1,math.floor(max(p[a] for p in triangle)))+1) for a in range(3)]
        for cell in itertools.product(*ranges):
            if cell not in surface and overlap(triangle,cell):surface.add(cell)
    # Flood through an extra cell outside all six sides, so boundary surfaces seal.
    exterior={(-1,-1,-1)};queue=collections.deque(exterior)
    while queue:
        point=queue.popleft()
        for axis in range(3):
            for step in (-1,1):
                neighbour=list(point);neighbour[axis]+=step;neighbour=tuple(neighbour)
                if all(-1<=neighbour[a]<=dimensions[a] for a in range(3)) and neighbour not in surface and neighbour not in exterior:
                    exterior.add(neighbour);queue.append(neighbour)
    occupied={p for p in itertools.product(*(range(n) for n in dimensions)) if p not in exterior}
    assert occupied,'No geometry intersects this grid.'
    return {'cells':[{'xyz':list(p),'shape':0} for p in sorted(occupied)],'triangles':len(triangles),
      'surface_cells':len(surface),'interior_cells':len(occupied-surface),'source_triangles':transformed,
      'warnings':['Thin surfaces are kept as at least one block. Inspect wings and small parts at the chosen resolution.']}

"""Voxelize the exact reveal mesh, preserving thin fin features."""
import itertools

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def load_groups(path):
    vertices=[];groups={};current='solid0'
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':vertices.append(tuple(map(float,fields[1:4])))
        elif fields[0]=='g':current=fields[1]
        elif fields[0]=='f':
            triangle=[vertices[int(i.split('/')[0])-1] for i in fields[1:4]]
            groups.setdefault(current,[]).append(triangle)
    return groups

def voxelize(path,dimensions):
    direction=(1,.217,.131)
    groups=load_groups(path)
    prepared={}
    for name,triangles in groups.items():
        cached=[]
        for a,b,c in triangles:
            edge1=sub(b,a);edge2=sub(c,a);h=cross(direction,edge2);det=dot(edge1,h)
            if abs(det)>1e-9:cached.append((a,edge1,edge2,h,1/det))
        prepared[name]=cached
    def inside(p,triangles):
        hits=[]
        for a,e1,e2,h,inv in triangles:
            s=sub(p,a);u=inv*dot(s,h)
            if u < -1e-7 or u > 1+1e-7:continue
            q=cross(s,e1);v=inv*dot(direction,q)
            if v < -1e-7 or u+v>1+1e-7:continue
            t=inv*dot(e2,q)
            if t>1e-7:hits.append(t)
        unique=[]
        for t in sorted(hits):
            if not unique or t-unique[-1]>1e-6:unique.append(t)
        return len(unique)%2==1
    body=prepared['solid0'];fins=[v for k,v in prepared.items() if k!='solid0']
    assert len(fins)==4
    occupied=set();feature_counts=[0]*4
    offsets=list(itertools.product((-.2,0,.2),repeat=3))
    for xyz in itertools.product(*(range(n) for n in dimensions)):
        p=(xyz[0]+.5-dimensions[0]/2,xyz[1]+.5,xyz[2]+.5-dimensions[2]/2)
        filled=inside(p,body)
        for i,fin in enumerate(fins):
            if any(inside(tuple(a+b for a,b in zip(p,offset)),fin) for offset in offsets):
                filled=True;feature_counts[i]+=1
        if filled:occupied.add(xyz)
    assert occupied and all(n>0 for n in feature_counts),feature_counts
    return occupied,{'source':'torpedo-source.obj','method':'body centre sampling plus 27-point fin preservation','fin_voxel_counts':feature_counts,'shared_mesh':True}

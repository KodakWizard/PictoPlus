"""Recognise broad flat faces and sharp corners before fitting curved solids."""
import collections,itertools,math
from voxelise import overlap

CURVED_IDS=set(range(73,122))|set(range(194,218))
BOX_IDS={0}|set(range(13,61))|set(range(182,194))

def flat_cells(triangles,cells,boxlike=None):
    occupied={tuple(c['xyz']) for c in cells};normals=collections.defaultdict(collections.Counter)
    for t in triangles:
        a,b,c=t;e=[b[i]-a[i] for i in range(3)];f=[c[i]-a[i] for i in range(3)]
        n=(e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0]);length=math.sqrt(sum(v*v for v in n))
        if length<1e-9:continue
        unit=tuple(v/length for v in n)
        if next((v for v in unit if abs(v)>1e-5),1)<0:unit=tuple(-v for v in unit)
        key=tuple(round(v,2) for v in unit)
        ranges=[range(math.floor(min(p[i] for p in t)),math.floor(max(p[i] for p in t))+1) for i in range(3)]
        for xyz in itertools.product(*ranges):
            if xyz in occupied and overlap(t,xyz):normals[xyz][key]+=min(length,2)
    result=set()
    for xyz,weights in normals.items():
        top=weights.most_common(3);total=sum(weights.values())
        if boxlike is not None and sum(w for n,w in weights.items() if max(map(abs,n))>=.99)/total>=.95:boxlike.add(xyz)
        if top[0][1]/total>=.88:result.add(xyz);continue
        if sum(w for _,w in top)/total<.95:continue
        # Gradually changing normals describe a curved source surface. Distinct
        # flat planes meeting at a sharp angle describe a hull or square corner.
        if all(abs(sum(a*b for a,b in zip(top[i][0],top[j][0])))<.82 for i in range(len(top)) for j in range(i)):
            result.add(xyz)
    return result

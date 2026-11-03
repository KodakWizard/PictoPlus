"""Fit actual native solid meshes to the shared torpedo, using traced rotations."""
import itertools,json,math,pathlib
import game_resources
from mesh_voxels import sub,dot,cross,load_groups
ROOT=pathlib.Path(__file__).resolve().parents[1]
# First table initialized at ARM 0x1d0ef0..0x1d1068. Degrees are converted
# to radians by 0x1e0e04. Matrix at 0x1d0e2c..0x1d0e88 is Rz*Ry*Rx.
ANGLES=((0,0,0),(0,90,0),(0,180,0),(0,270,0),(0,0,270),
 (270,0,270),(0,180,90),(270,180,90),(0,0,180),(270,270,270),
 (0,180,180),(270,90,90))
def matrix(angles):
    x,y,z=map(math.radians,angles);sx,cx=math.sin(x),math.cos(x);sy,cy=math.sin(y),math.cos(y);sz,cz=math.sin(z),math.cos(z)
    return tuple(tuple(round(v,8) for v in row) for row in (
      (cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx),
      (sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx),(-sy,cy*sx,cy*cx)))
def transform(p,m):return tuple(dot(row,p) for row in m)
DIRECTION=(1,.217,.131)
def prepare(triangles):
    cached=[]
    for a,b,c in triangles:
        e1=sub(b,a);e2=sub(c,a);h=cross(DIRECTION,e2);det=dot(e1,h)
        if abs(det)>1e-9:cached.append((a,e1,e2,h,1/det))
    return cached
def inside(p,cached):
    hits=[]
    for a,e1,e2,h,inv in cached:
        s=sub(p,a);u=inv*dot(s,h)
        if u< -1e-7 or u>1+1e-7:continue
        q=cross(s,e1);v=inv*dot(DIRECTION,q)
        if v< -1e-7 or u+v>1+1e-7:continue
        t=inv*dot(e2,q)
        if t>1e-7:hits.append(t)
    unique=[]
    for t in sorted(hits):
        if not unique or t-unique[-1]>1e-6:unique.append(t)
    return len(unique)%2==1
def variants(catalogue_path=None):
    catalogue=json.loads((catalogue_path or game_resources.generated()/'native-block-catalog.json').read_text())
    lookup=json.loads(game_resources.shape_map().read_text())
    result=[]
    for group in lookup:
        if group['extra_transform']:continue # mirrored table is a separate audit
        base=catalogue[group['mesh']]
        for orientation in range(group['orientation_count']):
            m=matrix(ANGLES[orientation]);positions=[transform(p,m) for p in base['positions']]
            triangles=[[positions[i] for i in base['triangles'][j:j+3]] for j in range(0,len(base['triangles']),3)]
            result.append({'id':group['first_id']+orientation,'mesh':group['mesh'],'orientation':orientation,'matrix':m,'triangles':triangles})
    return result
def build():
    offsets=list(itertools.product((-.4,-.2,0,.2,.4),repeat=3))
    candidates=variants();source={k:prepare(v) for k,v in load_groups(ROOT/'build/torpedo-source.obj').items()}
    old=json.loads((ROOT/'build/torpedo.json').read_text());occupied=set(map(tuple,old['voxels']))
    for c in candidates:
        cache=prepare(c['triangles']);c['sample_mask']=sum(1<<i for i,p in enumerate(offsets) if inside(p,cache))
    fitted=[];cube_error=0;fit_error=0
    for xyz in sorted(occupied):
        center=(xyz[0]+.5-5,xyz[1]+.5,xyz[2]+.5-2.5)
        target=sum(1<<i for i,p in enumerate(offsets) if any(inside(tuple(a+b for a,b in zip(center,p)),cache) for cache in source.values()))
        def cost(c):
            missing=(target&~c['sample_mask']).bit_count();excess=(c['sample_mask']&~target).bit_count()
            return (missing*2+excess+(2 if c['id'] else 0),missing+excess,c['id'])
        best=min(candidates,key=cost);error=(target^best['sample_mask']).bit_count()
        cube_error+=(target^candidates[0]['sample_mask']).bit_count();fit_error+=error
        fitted.append({'xyz':xyz,'shape':best['id'],'mesh':best['mesh'],'orientation':best['orientation'],'matrix':best['matrix'],
          'target_samples':target.bit_count(),'fitted_samples':best['sample_mask'].bit_count(),'sample_error':error})
    result={'status':'Native rotations traced; fitted result still requires emulator orientation confirmation',
      'dimensions':old['dimensions'],'cells':fitted,'baseline_cube_sample_error':cube_error,'fitted_sample_error':fit_error,
      'sample_points_per_cell':125,'excluded':'Mirrored native orientation table; no random shape assignment'}
    (ROOT/'build/fitted-torpedo.json').write_text(json.dumps(result,indent=2))
    print('Fit sample mismatch:',cube_error,'->',fit_error,'; blue',sum(c['shape']==0 for c in fitted),'orange',sum(c['shape']!=0 for c in fitted))
if __name__=='__main__':build()

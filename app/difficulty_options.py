"""Optional group constraints, with explicit, certified geometry additions."""
import copy,itertools,math

def add_requested_groups(document):
    from core import catalogue,solution,validate
    doc=copy.deepcopy(document);options=doc.get('generation',{});dims=doc['dimensions']
    for key,required in (('force_circle',2),('force_square',3)):
        if not options.get(key):continue
        def has_group(candidate):return any(required in row['groups'] for row in catalogue(tuple(dims),solution(candidate)))
        if has_group(doc):continue
        colours=solution(doc);occupied=set(colours);best=None
        # Add at most the missing groups to an existing row, retaining every
        # authored cell and shape. Try connected rows first, then minimal edits.
        for axis,length in enumerate(dims):
            if length<required*2-1:continue
            other=[a for a in range(3) if a!=axis]
            for fixed in itertools.product(*(range(dims[a]) for a in other)):
                for colour,shape in ((1,0),(2,13)):
                    line=[]
                    for n in range(length):
                        point=[0,0,0];point[axis]=n
                        for a,v in zip(other,fixed):point[a]=v
                        line.append(tuple(point))
                    current=[colours.get(p,0) for p in line]
                    for chosen in itertools.combinations(range(length),required):
                        if any(b-a<2 for a,b in zip(chosen,chosen[1:])):continue
                        if any(current[n] not in (0,colour) for n in chosen):continue
                        additions=[{'xyz':list(line[n]),'shape':shape} for n in chosen if not current[n]]
                        if not additions or len(additions)>required:continue
                        amended=list(current)
                        for n in chosen:amended[n]=colour
                        groups=sum(v==colour and (i==0 or amended[i-1]!=colour) for i,v in enumerate(amended))
                        if groups!=required:continue
                        contacts=sum(any(sum(abs(p[a]-q[a]) for a in range(3))==1 for q in occupied) for p in (tuple(c['xyz']) for c in additions))
                        rank=(len(additions),-contacts)
                        if best is not None and rank>=best[0]:continue
                        candidate=copy.deepcopy(doc);candidate['cells']+=additions
                        if required==3 and options.get('force_circle') and not any(2 in row['groups'] for row in catalogue(tuple(dims),solution(candidate))):continue
                        if validate(candidate)['valid']:best=(rank,candidate)
        assert best is not None,('Circle' if required==2 else 'Square')+' numbers need '+str(required*2-1)+' spaces along an axis and a logical arrangement. Increase the build space or edit the design.'
        doc=best[1]
    return doc

def time_targets(doc):
    count=len(doc['cells']);yellow=sum(c['shape']!=0 for c in doc['cells'])
    base=max(60,round((40+count*2.4+yellow*.7)/30)*30)
    return [base,round(base*1.65/30)*30,round(base*2.5/30)*30]

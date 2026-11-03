"""Independent, reproducible difficulty layouts and supported group ranges."""
import random,uuid,collections,threading,copy

_MODE_CACHE=collections.OrderedDict()
_CACHE_LOCK=threading.RLock()
_PLAN_CACHE=collections.OrderedDict()

def generate(doc,seed=None,checkpoint=None):
    from core import check,solution,catalogue,solve,qpp,geometry_hash,zero_envelope,Puzzle,verify
    check(doc);assert doc['cells'],'Add blocks first.'
    dims=tuple(doc['dimensions']);s=solution(doc);rows=catalogue(dims,s);total=dims[0]*dims[1]*dims[2]
    generation=doc.get('generation',{});levels=[generation.get(k+'_level',3) for k in ('easy','medium','hard')]
    assert all(type(n)==int and 1<=n<=5 for n in levels),'Difficulty levels must be 1 to 5.'
    # Reuse the layout identity for fine adjustments. Explicit Shuffle selects
    # a new identity; no mode consumes another mode's RNG or partial masks.
    identity=str(seed if seed is not None else doc.get('clues',{}).get('layout_seed') or geometry_hash(doc)[:16])
    easy=(0,.02,.04,.06,.08)[levels[0]-1];medium=(.20,.25,.30,.35,.40)[levels[1]-1];hard=(.50,.625,.75,.875,1.)[levels[2]-1]
    ratios=(easy,medium,medium+(hard-medium)/3,medium+2*(hard-medium)/3,hard)
    modes=[];proofs=[];ranges=[];signature=geometry_hash(doc)
    for mode,ratio in enumerate(ratios):
        if checkpoint:checkpoint()
        band='easy' if mode==0 else 'hard' if mode==4 else 'medium'
        shares=tuple(generation.get(band+'_'+kind+'_share',generation.get(kind+'_share',50)) for kind in ('square','circle'))
        assert all(type(n)==int and 0<=n<=100 for n in shares),'Choose number percentages from 0 to 100.'
        key=(signature,identity,mode,ratio,shares)
        with _CACHE_LOCK:
            cached=_MODE_CACHE.get(key)
            if cached is not None:_MODE_CACHE.move_to_end(key)
        if cached is not None:
            current,proof,group_stats=copy.deepcopy(cached)
            modes.extend(current);proofs.append(proof);ranges.append(group_stats);continue
        plan_key=(signature,identity,mode,shares)
        with _CACHE_LOCK:plan=_PLAN_CACHE.get(plan_key)
        if plan is None:
            rng=random.Random(identity+':'+str(mode));order=list(rows);rng.shuffle(order)
            masks=[bytearray([1])*(dims[a]*dims[b]) for a,b,_ in ((0,1,2),(0,2,1),(2,1,0))]
            def remove(row):
                if checkpoint:checkpoint()
                p,i=row['plane'],row['index']
                if not masks[p][i]:return True
                masks[p][i]=0
                try:solve(dims,s,masks,True)
                except AssertionError:masks[p][i]=1;return False
                return True
            protected=set();group_stats={};group_removals=[]
            for kind,group in (('square',3),('circle',2)):
                percentage=generation.get(band+'_'+kind+'_share',generation.get(kind+'_share',50))
                assert type(percentage)==int and 0<=percentage<=100,'Choose number percentages from 0 to 100.'
                group_rows=[r for r in order if group in r['groups']]
                # At zero, attempt every available group row, regardless of the
                # general difficulty removal budget. Failed removals are necessary.
                kept=round(len(group_rows)*percentage/100)
                protected.update((r['plane'],r['index']) for r in group_rows[:kept])
                group_removals.extend(group_rows[kept:])
                group_stats[kind]={'available':len(group_rows),'requested_percent':percentage}
            for row in group_removals:
                if (row['plane'],row['index']) not in protected:remove(row)
            removable=[]
            for row in order:
                if max(row['groups'])>=2 or (row['plane'],row['index']) in protected:continue
                if masks[row['plane']][row['index']] and remove(row):removable.append((row['plane'],row['index']))
            plan=([bytes(m) for m in masks],removable,group_stats)
            with _CACHE_LOCK:
                _PLAN_CACHE[plan_key]=copy.deepcopy(plan);_PLAN_CACHE.move_to_end(plan_key)
                while len(_PLAN_CACHE)>96:_PLAN_CACHE.popitem(last=False)
        maximum,removable,group_stats=copy.deepcopy(plan)
        masks=[bytearray(m) for m in maximum]
        # Micro difficulty is a share of deductions actually available for this
        # design, so Hard does not hit its minimum layout at every slider value.
        take=round(len(removable)*ratio)
        for plane,index in removable[take:]:masks[plane][index]=1
        for kind,group in (('square',3),('circle',2)):
            group_stats[kind]['shown']=sum(masks[r['plane']][r['index']] for r in rows if group in r['groups'])
        proof=solve(dims,s,masks,True);current=[bytes(m) for m in masks]
        with _CACHE_LOCK:
            _MODE_CACHE[key]=copy.deepcopy((current,proof,group_stats));_MODE_CACHE.move_to_end(key)
            while len(_MODE_CACHE)>96:_MODE_CACHE.popitem(last=False)
        modes.extend(current);proofs.append(proof);ranges.append(group_stats)
    encoded=Puzzle.read(qpp(doc,modes).write())
    for mode,proof in enumerate(proofs):verify(encoded,proof,mode)
    stats=[]
    for mode in range(5):
        current=modes[mode*3:mode*3+3]
        stats.append({'mode':mode,'visible':sum(map(sum,current)),'after_zero':zero_envelope(rows,current,total),'steps':len(proofs[mode]),'groups':ranges[mode]})
    return {'masks':[list(m) for m in modes],'stats':stats,'signature':geometry_hash(doc),'layout_seed':identity,'generation':dict(generation),'certified':True}

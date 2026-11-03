"""Compile only assets a native book needs; reuse unchanged certified outputs."""
import base64,copy,functools,hashlib,json,pathlib,shutil,struct,time,uuid,threading
from concurrent.futures import ThreadPoolExecutor
import core
import game_resources
ROOT=core.ROOT
_ASSET_LOCKS=[threading.Lock() for _ in range(64)]

@functools.lru_cache(maxsize=64)
def _file_hash(path,mtime,size):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def dependency(path):
    path=pathlib.Path(path);stat=path.stat();return _file_hash(str(path),stat.st_mtime_ns,stat.st_size)
def preparation_version():
    src=game_resources.romfs()
    paths=[ROOT/'app/number_layouts.py',src/'puzzle/609_FruitsGrape.qpp',src/'texture/book/cover/Book44.bch',src/'texture/book/icon/BookIcon44.ctpk']
    paths += [ROOT/'tools/modeltool'/name for name in ('BuildCustomModel.exe','StudioArtwork.exe','Thumbnail.exe','StudioDefaultCover.exe')]
    return hashlib.sha256(json.dumps(['prepared-assets-v1',*[dependency(path) for path in paths]]).encode()).hexdigest()

def cache_reference(kind,value):
    key=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    path=core.DATA/'compiled-book-cache'/'v1'/kind/(key+'.bin');seal=path.with_suffix('.json')
    info=json.loads(seal.read_text());stat=path.stat()
    return {'kind':kind,'key':key,'bytes':stat.st_size,'mtime':stat.st_mtime_ns,'seal_mtime':seal.stat().st_mtime_ns,'sha256':info['sha256']}

def references_valid(references):
    if not references:return False
    for ref in references:
        if ref.get('kind') not in ('numbers','model','thumbnail','cover','icon') or len(ref.get('key',''))!=64 or any(c not in '0123456789abcdef' for c in ref['key']):return False
        path=core.DATA/'compiled-book-cache'/'v1'/ref['kind']/(ref['key']+'.bin');seal=path.with_suffix('.json')
        try:
            stat=path.stat()
            if stat.st_size!=ref['bytes']:return False
            if stat.st_mtime_ns==ref['mtime'] and seal.stat().st_mtime_ns==ref['seal_mtime']:continue
            expected={'bytes':ref['bytes'],'sha256':ref['sha256']}
            if json.loads(seal.read_text())!=expected or hashlib.sha256(path.read_bytes()).hexdigest()!=ref['sha256']:return False
        except (OSError,ValueError,KeyError):return False
    return True
def cached(kind,value,builder):
    key=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    # Identical assets in concurrent puzzles must compile only once and may
    # never share a temporary output file while another writer is using it.
    with _ASSET_LOCKS[int(key[:8],16)%len(_ASSET_LOCKS)]:
        return _cached_locked(kind,key,builder)

def _cached_locked(kind,key,builder):
    directory=core.DATA/'compiled-book-cache'/'v1'/kind;directory.mkdir(parents=True,exist_ok=True)
    target=directory/(key+'.bin');seal=directory/(key+'.json')
    if target.exists() and seal.exists():
        raw=target.read_bytes()
        try:
            if json.loads(seal.read_text())=={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:return raw,True
        except (ValueError,OSError):pass
    # Legacy .NET helpers still have MAX_PATH limits. The cache key belongs
    # on the final asset, not in an unnecessarily long working directory.
    stage=directory/('work-'+uuid.uuid4().hex[:12]);stage.mkdir()
    try:raw=builder(stage);assert raw,'The asset compiler produced an empty file.'
    finally:shutil.rmtree(stage)
    temporary=target.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(target)
    core.atomic(seal,{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    return raw,False

def build_model(doc,folder):
    src=game_resources.romfs();id=0
    model_path=folder/'model.bch'
    canonical=None
    if doc.get('source_model')=='verified-torpedo' and (ROOT/'build/fitted-torpedo.json').is_file():
        original_fit=json.loads((ROOT/'build/fitted-torpedo.json').read_text());canonical={'dimensions':original_fit['dimensions'],'cells':[{'xyz':c['xyz'],'shape':c['shape']} for c in original_fit['cells']]}
    if doc.get('native_model') and doc.get('native_geometry_hash')==core.geometry_hash(doc):
        model_path.write_bytes(base64.b64decode(doc['native_model'],validate=True))
        if doc.get('imported_model'):
            # Older editable books can embed the already compiled reveal.
            # Repair its template camera too, without rebuilding its geometry.
            core.run_tool('BuildCustomModel.exe','front-view',model_path,model_path)
    elif canonical and doc.get('source_model')=='verified-torpedo' and core.geometry_hash(doc)==core.geometry_hash(canonical):
        shutil.copy2(ROOT/'build/torpedo-experimental/romfs/completemodel/cm_609_FruitsGrape.bch',model_path)
    else:
        model_doc={k:copy.deepcopy(doc[k]) for k in ('dimensions','cells','imported_model') if k in doc}
        imported=model_doc.get('imported_model')
        if imported:
            assert imported.get('fit_dimensions',doc['dimensions'])==doc['dimensions'],'Re-fit the attached model after changing the grid size.'
            for key in ('original','preview','signature','filename'):imported.pop(key,None)
        for cell in model_doc['cells']:
            group=next(g for g in core.SHAPE_MAP if g['first_id']<=cell['shape']<=g['last_id']);cell['mesh']=group['mesh'];cell['matrix']=core.matrix(core.ANGLES[cell['shape']-group['first_id']])
        spec=folder/f'model_{id}.json';core.atomic(spec,model_doc)
        core.run_tool('BuildCustomModel.exe',spec,src/'completemodel',src/'puzzlemodel/half_b.bch',model_path)
    return model_path.read_bytes()

def compile_assets(documents,book,progress=None,checkpoint=None,background=False):
    started=time.perf_counter();src=game_resources.romfs();assets={};puzzles=[];hits=0;built=0;timings=[];references=[]
    counter_lock=threading.Lock()
    completed=0;finished=0;total=len(documents)*3+3
    def report(stage,puzzle='',advance=False,puzzle_done=False):
        nonlocal completed,finished
        with counter_lock:
            completed+=int(advance);finished+=int(puzzle_done)
            if progress:progress({'completed':completed,'total':total,'stage':stage,'puzzle':puzzle,'puzzles_completed':finished,'puzzles_total':len(documents)})
    def get(kind,key,builder):
        nonlocal hits,built
        if checkpoint:checkpoint()
        raw,hit=cached(kind,key,builder)
        if checkpoint:checkpoint()
        with counter_lock:
            hits+=int(hit);built+=int(not hit)
            if background:references.append(cache_reference(kind,key))
        return raw
    number_version=[dependency(ROOT/'app/number_layouts.py'),dependency(src/'puzzle/609_FruitsGrape.qpp')]
    # Only model-generation changes invalidate models. UI/progress edits must
    # not discard expensive reveal models already compiled by this version.
    model_version=['model-input-v1',dependency(ROOT/'tools/modeltool/BuildCustomModel.exe')]
    artwork_version=[dependency(ROOT/'tools/modeltool/StudioArtwork.exe'),dependency(ROOT/'tools/modeltool/Thumbnail.exe')]
    def compile_puzzle(doc):
        puzzle_started=time.perf_counter();stages={}
        report('Checking number layouts',doc['name'])
        core.check(doc);assert doc['cells'],'Add blocks to the puzzle before exporting.'
        geometry=core.geometry_hash(doc);generation=doc.get('generation',{});seed=doc.get('clues',{}).get('layout_seed') or geometry[:16]
        def numbers(stage):
            clues=core.randomise(doc,checkpoint=checkpoint) if checkpoint else core.randomise(doc);return core.qpp(dict(doc,game_id=0),[bytes(m) for m in clues['masks']]).write()
        qpp=None
        if not background:
            stage_started=time.perf_counter();qpp=get('numbers',[number_version,geometry,generation,seed],numbers);stages['numbers']=round(time.perf_counter()-stage_started,3)
            report('Building reveal model',doc['name'],advance=True)
        else:report('Preparing reveal model',doc['name'])
        imported=doc.get('imported_model');model_input={k:imported.get(k) for k in ('triangles','uvs','texture','fit_dimensions')} if imported else None
        # Imported reveals depend on the fitted source, not the puzzle paint
        # or number layout. Hand-built reveals still depend on every block.
        model_key=[model_version,doc['dimensions'] if imported else geometry,model_input,doc.get('native_model'),doc.get('native_geometry_hash'),doc.get('source_model') if not imported else None]
        stage_started=time.perf_counter();model=get('model',model_key,lambda stage:build_model(doc,stage));stages['model']=round(time.perf_counter()-stage_started,3)
        if background:
            report('Checking number layouts',doc['name'],advance=True)
            stage_started=time.perf_counter();qpp=get('numbers',[number_version,geometry,generation,seed],numbers);stages['numbers']=round(time.perf_counter()-stage_started,3)
        report('Preparing puzzle artwork',doc['name'],advance=True)
        artwork=doc.get('image') or doc.get('imported_model',{}).get('preview')
        thumb_key=[artwork_version,'native-card-44x46',artwork] if artwork else [artwork_version,hashlib.sha256(model).hexdigest()]
        def thumbnail(stage):
            image=stage/'image.png';output=stage/'thumbnail.ctpk'
            if artwork:image.write_bytes(base64.b64decode(artwork.split(',')[1],validate=True))
            else:
                model_path=stage/'model.bch';model_path.write_bytes(model)
                core.run_tool('Thumbnail.exe',model_path,src/'texture/thumbnail/044_00609.ctpk',output)
                return output.read_bytes()
            core.run_tool('StudioArtwork.exe','thumbnail',image,src/'texture/thumbnail/044_00609.ctpk',output)
            return output.read_bytes()
        stage_started=time.perf_counter();thumb=get('thumbnail',thumb_key,thumbnail);stages['artwork']=round(time.perf_counter()-stage_started,3)
        with counter_lock:timings.append({'name':doc['name'],'stages':stages,'seconds':round(time.perf_counter()-puzzle_started,3)})
        report('Puzzle ready',doc['name'],advance=True,puzzle_done=True)
        return doc,qpp,model,thumb
    # Bound memory and CPU use: native model/texture tools can overlap with
    # the next puzzle's number checks. map retains the original book order.
    if background:puzzles=[compile_puzzle(doc) for doc in documents]
    else:
        with ThreadPoolExecutor(max_workers=2,thread_name_prefix='book-export') as pool:
            puzzles=list(pool.map(compile_puzzle,documents))
    if checkpoint:checkpoint()
    cover=core.book_cover(book).read_bytes()
    for kind,template,suffix in [('cover',src/'texture/book/cover/Book44.bch','.bch'),('icon',src/'texture/book/icon/BookIcon44.ctpk','.ctpk')]:
        report('Preparing book '+kind)
        def artwork_asset(stage,kind=kind,template=template,suffix=suffix):
            image=stage/'cover.png';image.write_bytes(cover);output=stage/('asset'+suffix)
            core.run_tool('StudioArtwork.exe',kind,image,template,output);return output.read_bytes()
        assets['assets/cover.bch' if kind=='cover' else 'assets/icon.ctpk']=get(kind,[artwork_version,dependency(template),hashlib.sha256(cover).hexdigest()],artwork_asset)
        report('Book '+kind+' ready',advance=True)
    return assets,puzzles,{'seconds':round(time.perf_counter()-started,3),'reused_assets':hits,'compiled_assets':built,'puzzles':timings,'cache_assets':references}

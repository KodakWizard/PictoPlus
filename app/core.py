"""Portable editor documents, certified clues, local library and safe mod journal."""
import base64,collections,copy,hashlib,json,os,pathlib,random,re,shutil,struct,subprocess,sys,textwrap,time,uuid,zipfile,threading
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import game_resources
from colour_logic import solve
from design_fitted_puzzle import catalogue,zero_envelope
from group_certificate import verify
from puzzle_format import Puzzle
from msbt import MessageFile
from scoring import calculate
from fit_native_shapes import ANGLES,matrix,prepare,inside
from build_block_tests import string
DATA=ROOT/'app/data';LIBRARY=DATA/'library';TITLE='0004000000187E00'
SHAPE_MAP=json.loads(game_resources.shape_map().read_text())
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temporary,path)
def check(doc):
    assert isinstance(doc,dict),'Invalid puzzle file.'
    dims=doc.get('dimensions');assert isinstance(dims,list) and len(dims)==3 and all(type(n)==int and 1<=n<=10 for n in dims),'Each dimension must be between 1 and 10.'
    assert isinstance(doc.get('cells'),list) and len(doc['cells'])<=1000,'Too many blocks.'
    seen=set()
    for c in doc['cells']:
        p=c.get('xyz');shape=c.get('shape')
        assert isinstance(p,list) and len(p)==3 and all(type(v)==int and 0<=v<n for v,n in zip(p,dims)),'A block is outside the puzzle.'
        assert tuple(p) not in seen,'Two blocks occupy the same position.'
        assert type(shape)==int and 0<=shape<=217,'Unknown block shape.'
        group=next(g for g in SHAPE_MAP if g['first_id']<=shape<=g['last_id'])
        assert not group['extra_transform'],'Mirrored shapes are not supported in this first version.'
        seen.add(tuple(p))
    assert isinstance(doc.get('name'),str) and 1<=len(doc['name'].strip())<=28,'Use a name of 1Ã¢â‚¬â€œ28 characters.'
    assert len(doc.get('description',''))<=220,'Keep the description under 220 characters.'
    assert 1<=len(doc.get('collection','Custom Puzzles'))<=24,'Use a collection name of 1Ã¢â‚¬â€œ24 characters.'
    for key in ('image','cover'):
        value=doc.get(key)
        if value:
            assert isinstance(value,str) and value.startswith('data:image/png;base64,') and len(value)<2_000_000,'Artwork must be a PNG under 1 MB.'
    return doc
def solution(doc):return {tuple(c['xyz']):1 if c['shape']==0 else 2 for c in doc['cells']}
def qpp(doc,masks=None):
    q=Puzzle.read((game_resources.romfs()/'puzzle/609_FruitsGrape.qpp').read_bytes());q.dimensions=tuple(doc['dimensions'])
    x,y,z=q.dimensions;h=bytearray(q.header)
    struct.pack_into('<I',h,4,doc.get('game_id',60008))
    for mode in range(5):struct.pack_into('<3H',h,0x96+mode*32,x*y,x*z,z*y)
    q.header=bytes(h);q.voxels=[(c['shape'],c['xyz'][0]|c['xyz'][1]<<4,c['xyz'][2]|4<<4,15) for c in sorted(doc['cells'],key=lambda c:c['xyz'])]
    q.masks=masks or [bytes([1])*(x*y),bytes([1])*(x*z),bytes([1])*(z*y)]*5
    return q
def validate(doc):
    check(doc)
    if not doc['cells']:return {'valid':False,'message':'Add a few blocks to begin.','warnings':[]}
    dims=tuple(doc['dimensions']);s=solution(doc);proof=None
    try:proof=solve(dims,s,use_groups=True)
    except AssertionError:return {'valid':False,'message':'The current shape needs guessing with these clue rules. Try changing a few blocks.','warnings':[]}
    rows=catalogue(dims,s);nonzero=[r for r in rows if sum(r['counts'])];hist=collections.Counter(r['counts'] for r in nonzero)
    repetition=hist.most_common(1)[0][1]/len(nonzero);warnings=[]
    if repetition>.4:warnings.append('Many lines repeat the same counts. This shape may work better as an introductory puzzle.')
    if len(doc['cells'])>500:warnings.append('A large number of blocks can be harder to read on the 3DS screen.')
    return {'valid':True,'message':'Solves without guessing','blocks':len(s),'blue':sum(v==1 for v in s.values()),'orange':sum(v==2 for v in s.values()),
      'circle_clues':sum(g==2 for r in rows for g in r['groups']),'square_clues':sum(g==3 for r in rows for g in r['groups']),
      'repetition':round(repetition*100),'steps':len(proof),'warnings':warnings}
def randomise(doc,seed=None,checkpoint=None):
    from number_layouts import generate
    return generate(doc,seed,checkpoint=checkpoint)

def geometry_hash(doc):return hashlib.sha256(json.dumps([doc['dimensions'],sorted(doc['cells'],key=lambda c:c['xyz'])],sort_keys=True).encode()).hexdigest()
def seed_library():
    # Fresh libraries contain no sample puzzles; list_books creates My Book.
    LIBRARY.mkdir(parents=True,exist_ok=True)

def list_library():
    seed_library();return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(LIBRARY.glob('*.json'))]

def cover_catalog():return json.loads((ROOT/'app/assets/covers/catalog.json').read_text(encoding='utf-8'))

_COVER_LOCK=threading.RLock()
def book_cover(book):
    with _COVER_LOCK:return _book_cover(book)

def _book_cover(book):
    style=next((s for s in cover_catalog() if s['id']==book.get('cover_style','02')),cover_catalog()[1])
    title=book.get('show_cover_title',not bool(book.get('cover')))
    key=hashlib.sha256(json.dumps([book['name'],book.get('cover'),style['id'],title,'portrait-v2']).encode()).hexdigest()
    output=DATA/'cover-cache'/(key+'.png')
    if not output.exists():
        output.parent.mkdir(parents=True,exist_ok=True)
        if book.get('cover'):
            source=output.with_suffix('.source.png');source.write_bytes(base64.b64decode(book['cover'].split(',')[1],validate=True))
            run_tool('StudioDefaultCover.exe',book['name'],output,source,style['ink'],'custom',str(title).lower())
        else:run_tool('StudioDefaultCover.exe',book['name'],output,ROOT/'app/assets/covers'/style['art'],style['ink'],'template',str(title).lower())
    return output

def list_books(previews=False,documents=None):
    path=DATA/'books.json';books=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    for name in dict.fromkeys(d['collection'] for d in (list_library() if documents is None else documents)):
        if not any(b['name']==name for b in books):books.append({'id':uuid.uuid4().hex,'name':name})
    if not books:books.append({'id':uuid.uuid4().hex,'name':'My Book','cover_style':'02','show_cover_title':False})
    atomic(path,books)
    if previews:
        books=[dict(book,preview='data:image/png;base64,'+base64.b64encode(book_cover(book).read_bytes()).decode()) for book in books]
    return books

def save_book(value):
    name=value.get('name','').strip();assert 1<=len(name)<=24,'Book names need 1Ã¢â‚¬â€œ24 characters.'
    books=list_books();existing=next((b for b in books if b['id']==value.get('id')),None)
    assert not any(b['name']==name and b is not existing for b in books),'A book already has this name.'
    cover=value.get('cover')
    if cover:assert isinstance(cover,str) and cover.startswith('data:image/png;base64,') and len(cover)<2_000_000,'Use a PNG cover smaller than 1 MB.'
    style=value.get('cover_style','02');assert style in {s['id'] for s in cover_catalog()},'Unknown cover design.'
    if existing:
        old=existing['name'];existing['name']=name
        if 'cover' in value:existing['cover']=cover
        if 'cover_style' in value:existing['cover_style']=style
        if 'show_cover_title' in value:existing['show_cover_title']=bool(value['show_cover_title'])
        for d in list_library():
            if d['collection']==old:d['collection']=name;atomic(LIBRARY/(d['id']+'.json'),d)
    else:books.append({'id':uuid.uuid4().hex,'name':name,'cover_style':style,'show_cover_title':bool(value.get('show_cover_title',False)),**({'cover':cover} if cover else {})})
    atomic(DATA/'books.json',books);return {'books':list_books(True),'library':list_library()}

def import_book(value):
    assert value.get('format')=='voxel-studio-book-1','Choose a PictoPlus book file.'
    items=value.get('puzzles');assert isinstance(items,list) and 0<len(items)<=210,'A book needs 1 to 210 puzzles.'
    name=value.get('name','Imported book');assert isinstance(name,str) and 1<=len(name)<=24,'Invalid book name.'
    for item in items:check(dict(item,collection=name))
    books=list_books();base=name;counter=2
    while any(b['name']==name for b in books):name=base[:20]+f' {counter}';counter+=1
    save_book({'name':name,'cover':value.get('cover'),'cover_style':value.get('cover_style','02'),'show_cover_title':value.get('show_cover_title',not bool(value.get('cover')))})
    for item in items:
        item=copy.deepcopy(item)
        for key in ('id','game_id','save_index'):item.pop(key,None)
        item['collection']=name;save(item)
    return {'books':list_books(True),'library':list_library(),'name':name}

def patch_custom_save(original,manifest):
    assert len(original)==45688,'Choose the European gameÃ¢â‚¬â„¢s 45,688-byte SAVEDATA backup.'
    changed=bytearray(original)
    for base in (12,0x3b84,0x76fc):
        for offset in [base+0x20+book*4 for book in manifest['books']]:
            if not any(changed[offset:offset+4]):changed[offset]=3
        for offset in [base+0x220+slot*16 for slot in manifest['save_indices']]:
            if not any(changed[offset:offset+16]):changed[offset]=9
    return bytes(changed)

def export_luma(docs,save_data=None):
    from book_packs import LUMA_READY
    if not LUMA_READY:raise ValueError('Luma export is temporarily blocked while the engine patch is relocated away from Luma LayeredFS code.')
    folder=DATA/'exports'/uuid.uuid4().hex;folder.mkdir(parents=True)
    manifest=export_package(docs,folder);output=folder/'Voxel-Studio-Luma.zip'
    instructions=('PictoPlus - European Picross 3D Round 2\n'
      '1. Keep a backup of your existing luma/titles/0004000000187E00 folder.\n'
      '2. Copy the luma folder from this archive to the SD root. Enable game patching in Luma.\n'
      '3. Open the game normally. Custom books are enabled by the included code.ips.\n'
      'No Checkpoint restore or external save editing is required. The game saves progress normally.\n'
      'The executable patch is for the verified European revision only; other revisions are unsupported.\n'
      'Azahar restart/persistence has been tested. Physical 3DS loading and performance still need testing.\n'
      'To remove, restore your previous title folder. Game progress is not reset.\n')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in manifest['files']:archive.write(folder/'romfs'/name,f'luma/titles/{TITLE}/romfs/{name}')
        archive.write(folder/'code.ips',f'luma/titles/{TITLE}/code.ips')
        archive.writestr('READ ME.txt',instructions);archive.writestr('manifest.json',json.dumps(manifest,indent=2))
    return {'file':str(output.relative_to(DATA/'exports')),'message':'Luma package ready. No Checkpoint save preparation is needed.','needs_hardware_test':True}

def save(doc):
    doc.setdefault('collection','Custom Puzzles');doc.setdefault('description','');check(doc);assert doc['cells'],'Add a block before saving this puzzle.';docs=list_library();existing=next((d for d in docs if d['id']==doc.get('id')),None)
    assert sum(d['collection']==doc['collection'] and d['id']!=doc.get('id') and bool(d['cells']) for d in docs)<210,'This book already has 210 puzzles. Choose another book or create a new one.'
    if not existing:
        doc['id']=uuid.uuid4().hex;doc['game_id']=max([60007]+[d['game_id'] for d in docs])+1;doc['save_index']=max([402]+[d['save_index'] for d in docs])+1
    else:doc['game_id']=existing['game_id'];doc['save_index']=existing['save_index']
    if doc.get('clues',{}).get('signature')!=geometry_hash(doc):doc.pop('clues',None)
    if not doc.get('manual_time_targets'):
        from difficulty_options import time_targets
        doc['time_targets']=time_targets(doc)
    doc['format']='voxel-studio-1';doc['updated']=time.time();atomic(LIBRARY/(doc['id']+'.json'),doc);return doc
def settings(value=None):
    path=DATA/'settings.json'
    current=json.loads(path.read_text()) if path.exists() else {'azahar':str(ROOT/'tools/azahar-studio'),'launch_after_install':False}
    if value:
        if 'azahar' in value:current['azahar']=str(pathlib.Path(value['azahar']).resolve())
        for key in ('live_save','overwrite_shapes','navigation_pinned','visible_block_preview','background_preparation','compact_layout'):
            if key in value:current[key]=bool(value[key])
        if 'launch_after_install' in value:current['launch_after_install']=bool(value['launch_after_install'])
        if 'interface_scale' in value:
            assert value['interface_scale'] in ('auto','100','90','80','75'),'Unknown interface scale.'
            current['interface_scale']=value['interface_scale']
        if 'theme' in value:
            assert value['theme'] in ('light','dark'),'Unknown theme.'
            current['theme']=value['theme']
        atomic(path,current)
    return current
def run_tool(name,*args):
    import threading
    priority=getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0) if threading.current_thread().name=='export-prepare' else 0
    process=subprocess.run([str(ROOT/'tools/modeltool'/name),*map(str,args)],capture_output=True,text=True,timeout=120,
      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|priority)
    if process.returncode:raise ValueError((process.stderr or process.stdout or 'Game conversion failed.')[-1600:])
    return process.stdout
def read_native_model(files):
    import tempfile
    if not isinstance(files,list) or not 1<=len(files)<=8:
        raise ValueError('Choose one native model and up to seven texture files.')
    with tempfile.TemporaryDirectory(prefix='pictoplus-model-') as directory:
        stage=pathlib.Path(directory)
        paths=[]
        remaining=12_000_000
        for index,encoded in enumerate(files):
            if not isinstance(encoded,str) or len(encoded)>10_666_668:
                raise ValueError('Each native resource must be smaller than 8 MB.')
            data=base64.b64decode(encoded,validate=True)
            remaining-=len(data)
            if len(data)>8_000_000 or remaining<0:
                raise ValueError('Select at most 12 MB of native resources in total.')
            path=stage/f'{index}.bin'
            path.write_bytes(data)
            paths.append(path)
        output=stage/'model.json'
        try:run_tool('ImportNativeModel.exe',output,*paths)
        except subprocess.TimeoutExpired:raise ValueError('The native model took too long to read.') from None
        return json.loads(output.read_text(encoding='utf-8'))

def put(folder,name,data):
    p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
def export_package(docs,folder,compile_only=False):
    assert docs and len(docs)<=(210 if compile_only else 109),'Select at least one puzzle, within the save capacity.'
    if not compile_only:assert all(d['save_index']<512 for d in docs),'Export this book for the PictoPlus loader; the legacy installer has no remaining save slots.'
    collections_={}
    for doc in docs:
        check(doc);assert validate(doc)['valid'],'A selected puzzle needs guessing.'
        collections_.setdefault(doc['collection'],[]).append(doc)
    books=[]
    for name,items in collections_.items():
        page=210 if compile_only else 15
        for start in range(0,len(items),page):books.append((name if len(items)<=page else name[:19]+f' {start//page+1}',items[start:start+page]))
    assert len(books)<=70,'Too many collections for the reserved book area.'
    src=game_resources.romfs();romfs=folder/'romfs';b=bytearray((src/'master/default.bms').read_bytes());old_count=struct.unpack_from('<H',b,8)[0]
    old_secondary=struct.unpack_from('<I',b,20)[0];records=[bytearray(b[28+i*404:28+(i+1)*404]) for i in range(old_count)]
    for record in records:
        offset=struct.unpack_from('<I',record,396)[0]
        if offset:struct.pack_into('<I',record,396,offset+len(books)*404)
    body=bytearray(b[old_secondary:]);new_records=[];text_entries=[]
    for index,(name,items) in enumerate(books):
        number=57+index;book=bytearray(records[3]);struct.pack_into('<HH',book,0,57+index,number);book[4:7]=bytes((len(items),0,0));book[28:44]=bytes(16)
        string(book,44,32,f'STUDIO_BOOKNO_{index}');string(book,76,32,f'STUDIO_BOOKNAME_{index}')
        struct.pack_into('<I',book,396,old_secondary+len(books)*404+len(body))
        string(book,140,128,f'r:/texture/book/cover/Studio{index}.bch',True);string(book,268,128,f'r:/texture/book/icon/Studio{index}.ctpk',True)
        layout=b[28+39*404:28+40*404] if compile_only else next(b[28+i*404:28+(i+1)*404] for i in range(old_count) if b[28+i*404+4]>=len(items))
        lp=struct.unpack_from('<I',layout,396)[0]
        for slot,doc in enumerate(items):
            local=slot%15 if compile_only else slot
            e=bytearray(b[lp+local*244:lp+(local+1)*244]);struct.pack_into('<HHI',e,0,slot,57+index,doc['game_id']);e[212:]=bytes(32);e[213]=4;struct.pack_into('<H',e,214,doc['save_index'])
            string(e,20,32,f"PUZZLE_NO_{doc['game_id']}");string(e,52,32,f"PUZZLE_NAME_{doc['game_id']}");string(e,84,128,f"r:/texture/thumbnail/studio_{doc['game_id']}.ctpk",True);body+=e
            text_entries.append((doc,f'C{len(text_entries)+1:03}'))
        new_records.append(book)
    header=bytearray(b[:28]);struct.pack_into('<H',header,8,old_count+len(books));struct.pack_into('<I',header,20,old_secondary+len(books)*404)
    put(romfs,'master/default.bms',bytes(header)+b''.join(records+new_records)+body)
    p=bytearray((src/'master/default.pms').read_bytes());n=struct.unpack_from('<H',p,8)[0];secondary=struct.unpack_from('<I',p,20)[0]
    template=bytes(p[28+608*404:28+609*404]);extra=[]
    for doc,_ in sorted(text_entries,key=lambda pair:pair[0]['game_id']):
        id=doc['game_id'];clues=doc.get('clues')
        if not clues or clues.get('signature')!=geometry_hash(doc) or clues.get('generation')!=doc.get('generation',{}):clues=randomise(doc)
        model=f'completemodel/cm_studio_{id}.bch';r=bytearray(template);struct.pack_into('<I',r,0,id)
        string(r,4,32,f'PUZZLE_NO_{id}');string(r,36,32,f'PUZZLE_NAME_{id}');string(r,68,128,f'r:/puzzle/studio_{id}.qpp',True);string(r,196,128,'r:/'+model,True);r[328:331]=bytes(doc['dimensions'])
        for offset,value in zip((368,376,400),doc.get('time_targets',[180,360,600])):struct.pack_into('<I',r,offset,value)
        extra.append(r);put(romfs,f'puzzle/studio_{id}.qpp',qpp(doc,[bytes(m) for m in clues['masks']]).write())
        model_path=romfs/model;model_path.parent.mkdir(parents=True,exist_ok=True)
        original_fit=json.loads((ROOT/'build/fitted-torpedo.json').read_text())
        canonical={'dimensions':original_fit['dimensions'],'cells':[{'xyz':c['xyz'],'shape':c['shape']} for c in original_fit['cells']]}
        if doc.get('native_model') and doc.get('native_geometry_hash')==geometry_hash(doc):
            model_path.write_bytes(base64.b64decode(doc['native_model'],validate=True))
        elif doc.get('source_model')=='verified-torpedo' and geometry_hash(doc)==geometry_hash(canonical):
            shutil.copy2(ROOT/'build/torpedo-experimental/romfs/completemodel/cm_609_FruitsGrape.bch',model_path)
        else:
            model_doc=copy.deepcopy(doc)
            imported=model_doc.get('imported_model')
            if imported:assert imported.get('fit_dimensions',doc['dimensions'])==doc['dimensions'],'Re-fit the attached model after changing the grid size.'
            for cell in model_doc['cells']:
                group=next(g for g in SHAPE_MAP if g['first_id']<=cell['shape']<=g['last_id']);cell['mesh']=group['mesh'];cell['matrix']=matrix(ANGLES[cell['shape']-group['first_id']])
            spec=folder/f'model_{id}.json';atomic(spec,model_doc)
            run_tool('BuildCustomModel.exe',spec,src/'completemodel',src/'puzzlemodel/half_b.bch',model_path)
        image=folder/f'image_{id}.png'
        artwork=doc.get('image') or doc.get('imported_model',{}).get('preview')
        if artwork:image.write_bytes(base64.b64decode(artwork.split(',')[1],validate=True))
        else:
            thumb=romfs/f'texture/thumbnail/studio_{id}.ctpk';thumb.parent.mkdir(parents=True,exist_ok=True)
            run_tool('Thumbnail.exe',model_path,src/'texture/thumbnail/044_00609.ctpk',thumb)
            shutil.copy2(str(thumb)+'.png',image)
        run_tool('StudioArtwork.exe','thumbnail',image,src/'texture/thumbnail/044_00609.ctpk',romfs/f'texture/thumbnail/studio_{id}.ctpk')
    struct.pack_into('<H',p,8,n+len(extra));struct.pack_into('<I',p,20,secondary+len(extra)*404)
    put(romfs,'master/default.pms',bytes(p[:secondary])+b''.join(extra)+p[secondary:])
    for index,(name,items) in enumerate(books):
        image=folder/f'cover_{index}.png'
        stored=next((b for b in list_books() if b['name']==items[0]['collection']),{})
        if not stored.get('name'):stored={'name':name}
        if stored['name']!=name:stored=dict(stored,name=name)
        shutil.copy2(book_cover(stored),image)
        run_tool('StudioArtwork.exe','cover',image,src/'texture/book/cover/Book44.bch',romfs/f'texture/book/cover/Studio{index}.bch')
        run_tool('StudioArtwork.exe','icon',image,src/'texture/book/icon/BookIcon44.ctpk',romfs/f'texture/book/icon/Studio{index}.ctpk')
    for lang in ('en','fr','de','es','it'):
        for resource in ('PuzzleName','PuzzleNo','Trivia','BookName','BookNo'):
            m=MessageFile((src/f'text/{lang}/{resource}.msbt').read_bytes())
            if resource.startswith('Book'):
                for index,(name,_) in enumerate(books):m.set(f"STUDIO_{'BOOKNAME' if resource=='BookName' else 'BOOKNO'}_{index}",name if resource=='BookName' else str(57+index))
            else:
                for doc,number in text_entries:
                    text=doc['name'] if resource=='PuzzleName' else number if resource=='PuzzleNo' else '\n'.join(textwrap.wrap(doc.get('description','Custom puzzle'),27))
                    m.set(f"PUZZLE_{'NO' if resource=='PuzzleNo' else 'NAME'}_{doc['game_id']}",text)
            put(romfs,f'text/{lang}/{resource}.msbt',m.write())
    manifest={'files':[f.relative_to(romfs).as_posix() for f in romfs.rglob('*') if f.suffix in ('.qpp','.bch','.ctpk','.msbt','.bms','.pms')],
      'books':[57+i for i in range(len(books))],'save_indices':[d['save_index'] for d in docs]}
    if compile_only:return manifest
    from build_availability_patch import build
    ips,_,patch_report=build(manifest);(folder/'code.ips').write_bytes(ips)
    manifest['code_patch']='code.ips';manifest['code_patch_sha256']=hashlib.sha256(ips).hexdigest();manifest['source_code_sha256']=patch_report['source_sha256'];manifest['external_save_edit']=False
    return manifest

def export_play_pack(ids,progress=None):
    from book_packs import FORMAT, TITLE, validate as validate_pack
    from native_book import write_book
    selected=set(ids);documents=[d for d in list_library() if d['id'] in selected]
    assert documents and len(documents)==len(selected),'A selected puzzle was not found.'
    names={d['collection'] for d in documents};assert len(names)==1,'Export one book at a time.'
    documents=[d for d in documents if d['cells']];assert documents,'This book has no blocks yet. Add a puzzle before exporting.'
    name=next(iter(names));book=next(b for b in list_books() if b['name']==name)
    author_file=DATA/'pack-author-ids.json'
    author=json.loads(author_file.read_text(encoding='utf-8')) if author_file.exists() else {}
    record=author.setdefault(book['id'],{'id':book.get('native_id',uuid.uuid4().hex),'revision':book.get('native_revision',0)})
    revision=record['revision']+1;folder=DATA/'exports'/uuid.uuid4().hex
    from export_assets import compile_assets
    assets,compiled,performance=compile_assets(documents,book,progress=progress)
    if progress:progress({'completed':len(documents)*3+2,'total':len(documents)*3+3,'stage':'Writing book file','book':name})
    puzzles=[]
    for index,(original,qpp_bytes,model_bytes,thumb_bytes) in enumerate(compiled):
        doc=original;key=original.get('native_puzzle_id') if original.get('native_geometry_hash')==geometry_hash(original) else None
        key=key or uuid.uuid5(uuid.UUID(record['id']),original['id']+':'+geometry_hash(original)).hex
        item={'id':key,'name':doc['name'],'description':doc.get('description',''),'dimensions':doc['dimensions'],
              'time_targets':doc.get('time_targets',[180,360,600])}
        qpp_bytes=bytearray(qpp_bytes);struct.pack_into('<I',qpp_bytes,4,60000+index)
        for kind,raw,suffix in (('puzzle',bytes(qpp_bytes),'.qpp'),('model',model_bytes,'.bch'),('thumbnail',thumb_bytes,'.ctpk')):
            item[kind]='assets/'+key+suffix;assets[item[kind]]=raw
        puzzles.append(item)
    manifest={'format':FORMAT,'title_id':TITLE,'id':record['id'],'revision':revision,'name':name,'cover':'assets/cover.bch','icon':'assets/icon.ctpk','puzzles':puzzles}
    manifest['files']={name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in assets.items()}
    editable={'format':'voxel-studio-book-1','name':name,'cover':book.get('cover'),'cover_style':book.get('cover_style','02'),
              'show_cover_title':book.get('show_cover_title',False),'puzzles':copy.deepcopy(documents)}
    # Native models copied on import are game-template derivatives. Keep their
    # editable geometry, but do not duplicate a raw template in the JSON tail.
    for document in editable['puzzles']:
        document.pop('native_model',None)
    output=folder/'Book.pictobook';write_book(output,{'manifest':manifest,'assets':assets},editable,installed_game=True)
    atomic(DATA/'last-export-timing.json',performance)
    record['revision']=revision;atomic(author_file,author)
    if progress:progress({'completed':len(documents)*3+3,'total':len(documents)*3+3,'stage':'Book ready','book':name})
    return {'file':str(output.relative_to(DATA/'exports')),'message':'Book ready. Copy it to PictoPlus/Books on your SD card with the updated SD loader.','performance':performance}

def export_books(book_ids,progress=None):
    """Each selected book stays a standalone, directly playable .pictobook."""
    selected=set(book_ids);books=[b for b in list_books() if b['id'] in selected]
    assert selected and len(books)==len(selected),'Select one or more existing books.'
    documents=list_library();groups=[[d['id'] for d in documents if d['collection']==b['name'] and d['cells']] for b in books]
    assert all(groups),'An empty book cannot be exported. Add a puzzle or deselect it.'
    total=sum(len(ids)*3+3 for ids in groups)+(1 if len(groups)>1 else 0);offset=0;results=[]
    for book,ids in zip(books,groups):
        def report(value):
            if progress:progress(dict(value,completed=offset+value['completed'],total=total,book=book['name']))
        results.append(export_play_pack(ids,progress=report) if progress else export_play_pack(ids));offset+=len(ids)*3+3
    if len(results)==1:return results[0]
    folder=DATA/'exports'/uuid.uuid4().hex;folder.mkdir(parents=True)
    output=folder/'PictoPlus books.zip'
    if progress:progress({'completed':offset,'total':total,'stage':'Packing books for download'})
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for i,(book,result) in enumerate(zip(books,results),1):
            safe=re.sub(r'[^\w .-]','_',book['name']).strip(' .') or 'Book'
            archive.write(DATA/'exports'/result['file'],f'{i:02d} - {safe}.pictobook')
        archive.writestr('READ ME.txt','Install the updated USA PictoPlus loader once. Copy the .pictobook files into PictoPlus/Books on the SD card (or the emulator virtual SD card), then restart the game. Keep existing progress files. European setup remains separate.\n')
    if progress:progress({'completed':total,'total':total,'stage':'Books ready'})
    return {'file':str(output.relative_to(DATA/'exports')),'message':f'{len(books)} books exported. Extract the ZIP and copy its .pictobook files into PictoPlus/Books.'}

def import_native_book(path):
    from native_book import read_book
    from book_packs import read_pack
    path=pathlib.Path(path)
    with path.open('rb') as source:magic=source.read(8)
    pack=read_book(path) if magic==b'VXBOOK01' else read_pack(path)
    manifest=pack['manifest'];editable=copy.deepcopy(pack.get('editable'))
    if not editable:
        documents=[]
        for item in manifest['puzzles']:
            q=Puzzle.read(pack['assets'][item['puzzle']])
            documents.append({'format':'voxel-studio-1','name':item['name'],'description':item.get('description',''),
                'dimensions':list(q.dimensions),'cells':[{'xyz':[xy&15,xy>>4,zc&15],'shape':shape} for shape,xy,zc,flags in q.voxels],
                'time_targets':item['time_targets'],'manual_time_targets':True,
                'native_model':base64.b64encode(pack['assets'][item['model']]).decode()})
        editable={'format':'voxel-studio-book-1','name':manifest['name'],'puzzles':documents}
    assert len(editable['puzzles'])==len(manifest['puzzles']),'Editable puzzle count does not match the book.'
    for document,item in zip(editable['puzzles'],manifest['puzzles']):
        check(dict(document,collection=editable['name']))
        q=Puzzle.read(pack['assets'][item['puzzle']])
        cells={(xy&15,xy>>4,zc&15):shape for shape,xy,zc,flags in q.voxels}
        assert tuple(document['dimensions'])==q.dimensions and {tuple(c['xyz']):c['shape'] for c in document['cells']}==cells,'Editable design does not match the playable book.'
        document.update(native_puzzle_id=item['id'],native_geometry_hash=geometry_hash(document))
    result=import_book(editable)
    books=list_books();book=next(b for b in books if b['name']==result['name'])
    book.update(native_id=manifest['id'],native_revision=manifest['revision']);atomic(DATA/'books.json',books)
    result['books']=list_books(True);return result

def running():
    if os.name!='nt':return False
    from windows_process import is_running
    return is_running('azahar.exe')
def mod_root(azahar):
    p=pathlib.Path(azahar).resolve();assert (p/'azahar.exe').is_file(),'Select the portable Azahar folder containing azahar.exe.'
    assert (p/'user').is_dir(),'This installation has no portable user folder. Use the prepared Studio copy.'
    return p/'user/load/mods'/TITLE/'romfs'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def restore(azahar):
    assert not running(),'Close Azahar before restoring.'
    mod=mod_root(azahar);journal=DATA/'installations'/(hashlib.sha256(str(mod).encode()).hexdigest()+'.json')
    if not journal.exists():return {'message':'No Studio installation to restore.'}
    receipt=json.loads(journal.read_text())
    if receipt.get('root')=='title':mod=mod.parent
    for item in receipt['files']:
        p=mod/item['path'];assert p.resolve().is_relative_to(mod.resolve())
        pending=receipt.get('state')=='installing'
        allowed={item['installed_hash']}
        if pending and item.get('previous_hash'):allowed.add(item['previous_hash'])
        assert (p.is_file() and sha(p) in allowed) or (pending and not p.exists() and not item['backup']),'A mod file changed outside Studio. Restore stopped to preserve it.'
    for item in receipt['files']:
        p=mod/item['path']
        if item['backup']:shutil.copy2(item['backup'],p)
        elif p.exists():p.unlink()
    journal.unlink();return {'message':'Previous game files restored. Save progress was preserved.'}
def install(docs,azahar):
    assert not running(),'Close Azahar before installing.'
    mod=mod_root(azahar);package=DATA/'exports'/uuid.uuid4().hex;package.mkdir(parents=True)
    manifest=export_package(docs,package)
    restore(azahar)
    backup=DATA/'backups'/uuid.uuid4().hex;backup.mkdir(parents=True);entries=[]
    # Read-only save backups: installation never writes SAVEDATA.
    for index,savefile in enumerate((pathlib.Path(azahar)/'user/sdmc').rglob('SAVEDATA')):
        assert savefile.stat().st_size==45688,'Unrecognized game save. Installation stopped.'
        shutil.copy2(savefile,backup/f'SAVEDATA-{index}')
    file_root=mod.parent
    sources={'romfs/'+name:package/'romfs'/name for name in manifest['files']}
    sources['exefs/code.ips']=package/'code.ips'
    for name,source in sources.items():
        target=file_root/name;assert target.resolve().is_relative_to(file_root.resolve())
        old=None
        if target.exists():old=backup/'files'/name;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,old)
        entries.append({'path':name,'backup':str(old) if old else None,'previous_hash':sha(target) if old else None,'installed_hash':sha(source)})
    journal=DATA/'installations'/(hashlib.sha256(str(mod).encode()).hexdigest()+'.json')
    atomic(journal,{'root':'title','files':entries,'books':manifest['books'],'backup':str(backup),'state':'installing'})
    try:
        for item in entries:
            target=file_root/item['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(sources[item['path']],target)
    except Exception:
        for item in entries:
            target=file_root/item['path']
            if item['backup']:shutil.copy2(item['backup'],target)
            elif target.exists():target.unlink()
        journal.unlink(missing_ok=True)
        raise
    atomic(journal,{'root':'title','files':entries,'books':manifest['books'],'backup':str(backup),'state':'complete'})
    return {'message':f"Installed {len(docs)} puzzle(s) in Book {manifest['books'][0]}. Game patch installed. Save files were backed up without editing them.",
      'needs_playtest':True,'books':manifest['books']}
def launch(azahar):
    mod_root(azahar);roms=list(ROOT.glob('*.3ds'));assert len(roms)==1,'Select exactly one game ROM in this project.'
    subprocess.Popen([str(pathlib.Path(azahar)/'azahar.exe'),str(roms[0])],cwd=azahar)
    return {'message':'Azahar launched.'}
def import_model(triangles,dimensions,fit_shapes=True,blue=True,yellow=True,yellow_ratio=None,blue_inside=False):
    # Endpoints are strict single-colour requests, even when both colour
    # checkboxes remain available in the UI. Certification must not undo them.
    if yellow_ratio==0 and blue:yellow=False
    if yellow_ratio==100 and yellow:blue=False
    if dimensions is None:
        candidates=[]
        for edge in (6,7,8,9,10):
            try:
                candidate=import_model(triangles,[edge]*3,fit_shapes,blue,yellow,yellow_ratio,blue_inside)
                quality=candidate.get('fit_quality',0)
                score=quality-.004*(edge-6)
                if candidate.get('shape_fitting',{}).get('solvable',True):candidates.append((score,-edge,candidate))
            except AssertionError:
                continue
        assert candidates,'No logical conversion was found. Try a manual size or different block settings.'
        chosen=max(candidates,key=lambda item:item[:2])[2]
        chosen['automatic_size']=True
        chosen['warnings'].append('Automatic size compares five grids for shape fidelity and favours a smaller puzzle when their fit is similar.')
        return chosen
    from voxelise import convert
    result=convert(triangles,dimensions)
    result['dimensions']=list(dimensions)
    if fit_shapes:
        from import_shapes import fit,certify_colours
        conservative_count=len(result['cells'])
        metrics={}
        result['cells'],improvement=fit(result['source_triangles'],dimensions,result['cells'],blue,yellow,yellow_ratio,metrics,blue_inside,automatic_balance=yellow_ratio is None)
        result['fit_quality']=metrics['volume_similarity']
        assert result['cells'],'This model is too thin at the selected size. Try a larger grid or turn off yellow shape fitting.'
        restored,valid=certify_colours(dimensions,result['cells'],improvement,allow_blue=blue,symmetry_groups=metrics['symmetry_groups'])
        result['shape_fitting']={'blue':sum(c['shape']==0 for c in result['cells']),'yellow':sum(c['shape']!=0 for c in result['cells']),'restored_for_logic':restored,'solvable':valid}
        result['warnings'].append('Yellow shapes follow the source volume. Open sheets retain cubes; small closed-surface slivers are omitted.')
        result['shape_fitting']['sliver_cells_removed']=conservative_count-len(result['cells'])
        result['shape_fitting']['symmetry_axes']=metrics['symmetry_axes']
        result['shape_fitting']['mirrored_surface_groups']=metrics['matching_surface_groups']
        if metrics['symmetry_axes']:result['warnings'].append('Mirrored shape fitting preserves the detected '+', '.join('XYZ'[a] for a in metrics['symmetry_axes'])+' symmetry.')
        elif metrics['matching_surface_groups']:result['warnings'].append('Matching mirrored surfaces use consistent block shapes without copying asymmetric details.')
        if restored:result['warnings'].append(str(restored)+' low-confidence shape fits were restored to blue cubes to keep logical deductions available.')
    return result


def tune_difficulty(document):
    from difficulty_options import time_targets
    check(document);doc=copy.deepcopy(document);doc.setdefault('generation',{}).pop('force_circle',None);doc['generation'].pop('force_square',None);doc['clues']=randomise(doc)
    if not doc.get('manual_time_targets'):doc['time_targets']=time_targets(doc)
    return doc

def delete_library_item(kind,id=None,name=None):
    assert kind in ('book','puzzle'),'Unknown item type.'
    books=list_books() if kind=='book' else None
    if kind=='book' and len(books)<=1:raise ValueError('Keep at least one book in your library.')
    docs=list_library();targets=[d for d in docs if d.get('id')==id] if kind=='puzzle' else [d for d in docs if d['collection']==name]
    archive=DATA/'deleted-items'/uuid.uuid4().hex;archive.mkdir(parents=True)
    for doc in targets:
        source=LIBRARY/(doc['id']+'.json')
        assert source.resolve().is_relative_to(LIBRARY.resolve())
        shutil.move(str(source),str(archive/source.name))
    if kind=='book':
        removed=[b for b in books if b['name']==name];atomic(archive/'books.json',removed)
        atomic(DATA/'books.json',[b for b in books if b['name']!=name])
    return {'books':list_books(True),'library':list_library()}

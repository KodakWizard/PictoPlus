"""Import only a validated local-game authoring profile; never accept ROM dumps."""
import hashlib,itertools,json,os,pathlib,shutil,struct,sys,time,uuid,zlib
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import game_resources
LIMIT=64*1024*1024
def manifest():return json.loads((ROOT/'app/config/authoring-manifest.json').read_text())
def status():return {'ready':game_resources.ready(),'region':'USA','requires_installed_game':True}
def rename_ready(source,target):
    # Windows indexers/antivirus can briefly hold newly generated files open.
    for attempt in range(10):
        try:source.rename(target);return
        except PermissionError:
            if attempt==9:raise ValueError('Windows is still using the setup files. Close other apps using this folder and try setup again.')
            time.sleep(.1*(attempt+1))

def generate_shapes(stage):
    import core
    from fit_native_shapes import variants,prepare,inside
    generated=stage/'generated';generated.mkdir()
    core.run_tool('BlockCatalog.exe',stage/'romfs/puzzlemodel/half_b.bch',generated/'native-block-catalog')
    offsets=[[x+.000173,y+.000319,z+.000547] for x,y,z in itertools.product((-.375,-.125,.125,.375),repeat=3)]
    shapes=[]
    for v in variants(generated/'native-block-catalog.json'):
        cached=prepare(v['triangles']);mask=sum(1<<i for i,p in enumerate(offsets) if inside(p,cached))
        shapes.append({'shape':v['id'],'mask':hex(mask)})
    (generated/'native-shape-samples.json').write_text(json.dumps(dict(offsets=offsets,variants=shapes)))

def import_profile(path,progress=None):
    path=pathlib.Path(path);expected=manifest()['files'];home=game_resources.home();home.parent.mkdir(parents=True,exist_ok=True)
    stage=home.with_name(home.name+'.import-'+uuid.uuid4().hex);stage.mkdir()
    try:
        with path.open('rb') as source:
            h=source.read(32)
            if len(h)!=32 or h[:8]!=b'PPAUTH01':raise ValueError('Open the PictoPlus-Setup.pictosetup file prepared by your game.')
            version,count,record,total,table_crc,header_crc=struct.unpack_from('<6I',h,8)
            if version!=1 or count!=len(expected) or record!=176 or total!=path.stat().st_size or total>LIMIT or zlib.crc32(h[:28]+bytes(4))!=header_crc:raise ValueError('Invalid setup file header.')
            table=source.read(count*176)
            if len(table)!=count*176 or zlib.crc32(table)!=table_crc:raise ValueError('The setup file index is damaged.')
            end=32+len(table)
            for i,item in enumerate(expected):
                row=table[i*176:(i+1)*176];name=row[:160].split(b'\0',1)[0].decode('ascii');n,crc,offset,reserved=struct.unpack_from('<4I',row,160)
                if (name,n,crc,offset,reserved)!=(item['name'],item['size'],item['crc'],end,0) or n>total-end:raise ValueError('This setup file does not match the supported USA game.')
                target=stage/'romfs'/item['name'];target.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();checksum=0;left=n
                with target.open('wb') as output:
                    while left:
                        blob=source.read(min(65536,left))
                        if not blob:raise ValueError('Setup is incomplete. Let the game finish preparing it.')
                        output.write(blob);digest.update(blob);checksum=zlib.crc32(blob,checksum);left-=len(blob)
                if checksum!=crc or digest.hexdigest()!=item['sha256']:raise ValueError('A game template is damaged or from an unsupported version.')
                end+=n
                if progress:progress({'completed':i+1,'total':count+1,'stage':'Checking setup files'})
            if end!=total or source.read(1):raise ValueError('Unexpected setup file data.')
        if progress:progress({'completed':count,'total':count+1,'stage':'Preparing block shapes'})
        generate_shapes(stage)
        (stage/'ready.json').write_text(json.dumps({'format':'PPAUTH01','region':'USA','files':len(expected)}))
        # The old working resources remain intact if validation or generation fails.
        backup=home.with_name(home.name+'.previous-'+uuid.uuid4().hex[:8])
        if home.exists():rename_ready(home,backup)
        try:rename_ready(stage,home)
        except (OSError,ValueError):
            if backup.exists():rename_ready(backup,home)
            raise
        # Keep the previous, app-owned resource set as a recovery copy.
        from game_asset_edits import _models
        _models.cache_clear()
        if progress:progress({'completed':count+1,'total':count+1,'stage':'Setup ready'})
        return {'ready':True,'message':'Setup complete. You can now create and export books.'}
    finally:
        if stage.exists():shutil.rmtree(stage)

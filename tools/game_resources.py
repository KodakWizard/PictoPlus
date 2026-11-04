"""Local, user-prepared authoring resources. Public builds never use work/romfs."""
import hashlib,json,os,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def public_build():return (ROOT/'app/public-release.json').is_file()
def home():return pathlib.Path(os.environ.get('PICTOPLUS_RESOURCES',str(ROOT/'app/data/game-resources')))
def romfs():
    local=home()/'romfs'
    if public_build() or os.environ.get('PICTOPLUS_RESOURCES'):return local
    # Preserve the existing developer/EUR installation paths. Only the public
    # build or an explicit local-resource selection uses the USA authoring set.
    if (ROOT/'work/romfs').is_dir():return ROOT/'work/romfs'
    return local
def generated():
    if romfs()==ROOT/'work/romfs':return ROOT/'build'
    return home()/'generated'
def shape_map():return ROOT/('app/config/native-shape-map.json' if public_build() else 'build/native-shape-map.json')
def templates_intact(resources):
    manifest=(ROOT/'app/config/authoring-manifest.json').read_bytes()
    key=hashlib.sha256(manifest).hexdigest()
    stamp=resources/'integrity.json'
    try:
        previous=json.loads(stamp.read_text())
        cached=previous['files'] if previous['manifest']==key and isinstance(previous['files'],dict) else {}
    except (OSError,ValueError,KeyError,TypeError):
        previous=None
        cached={}
    verified={}
    for item in json.loads(manifest)['files']:
        name=item['name']
        path=resources/'romfs'/name
        before=path.stat()
        if before.st_size!=item['size']:return False
        identity=[before.st_size,before.st_mtime_ns,before.st_ctime_ns]
        # Export inputs are small and shared by nearly every book. Always
        # check them, even if a damaged file retained its timestamps.
        if not name.startswith('completemodel/') or cached.get(name)!=identity:
            with path.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=item['sha256']:return False
            after=path.stat()
            if [after.st_size,after.st_mtime_ns,after.st_ctime_ns]!=identity:return False
        verified[name]=identity
    result={'manifest':key,'files':verified}
    if result!=previous:
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',dir=resources,delete=False) as stream:
                temporary=pathlib.Path(stream.name)
                json.dump(result,stream)
            temporary.replace(stamp)
        except OSError:
            # The cache is optional. A fully validated read-only install works.
            if temporary:
                try:temporary.unlink(missing_ok=True)
                except OSError:pass
    return True

def ready():
    if romfs()==ROOT/'work/romfs':return (romfs()/'puzzlemodel/half_b.bch').is_file()
    if not (home()/'ready.json').is_file():return False
    if not all((generated()/name).is_file() for name in ('native-block-catalog.json','native-shape-samples.json')):return False
    try:
        marker=json.loads((home()/'ready.json').read_text())
        if marker.get('format')!='PPAUTH01' or marker.get('region')!='USA':return False
        catalogue=json.loads((generated()/'native-block-catalog.json').read_text())
        samples=json.loads((generated()/'native-shape-samples.json').read_text())
        if not isinstance(catalogue,list) or len(catalogue)!=18 or not isinstance(samples,dict) or not samples.get('variants'):return False
        return templates_intact(home())
    except (OSError,ValueError,KeyError,AttributeError,TypeError):return False

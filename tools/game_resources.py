"""Local, user-prepared authoring resources. Public builds never use work/romfs."""
import os,pathlib
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
def ready():
    if romfs()==ROOT/'work/romfs':return (romfs()/'puzzlemodel/half_b.bch').is_file()
    if not (home()/'ready.json').is_file():return False
    if not all((generated()/name).is_file() for name in ('native-block-catalog.json','native-shape-samples.json')):return False
    try:
        import json
        marker=json.loads((home()/'ready.json').read_text())
        if marker.get('format')!='PPAUTH01' or marker.get('region')!='USA':return False
        catalogue=json.loads((generated()/'native-block-catalog.json').read_text())
        samples=json.loads((generated()/'native-shape-samples.json').read_text())
        if not isinstance(catalogue,list) or len(catalogue)!=18 or not isinstance(samples,dict) or not samples.get('variants'):return False
        files=json.loads((ROOT/'app/config/authoring-manifest.json').read_text())['files']
        return all((romfs()/f['name']).stat().st_size==f['size'] for f in files)
    except (OSError,ValueError,KeyError,AttributeError,TypeError):return False

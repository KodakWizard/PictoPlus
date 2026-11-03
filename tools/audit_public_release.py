"""Local distribution/source audit. Technical checks, not legal clearance."""
import hashlib,io,json,pathlib,re,struct,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN={'.3ds','.cci','.cia','.bch','.qpp','.ctpk','.msbt','.arc','.pictoauthoring','.pictosetup','.pictobook','.voxpack','.voxbook','.sav','.dmp'}
PRIVATE=re.compile(rb'(?:[A-Za-z]:[\\/](?:Users|EMULATION)[\\/]|OneDrive[\\/]|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})')
def inspect(entries,source=False):
 for name,raw in entries.items():
  p=pathlib.PurePosixPath(name);parts=p.parts
  assert not p.is_absolute() and '..' not in parts and '\\' not in name,name
  assert p.suffix.lower() not in FORBIDDEN,'Private/game asset: '+name
  assert not any(x in parts for x in ('.git','__pycache__','node_modules')),name
  assert not name.startswith(('work/','backups/','app/data/','tools/azahar')),name
  if p.suffix.lower() in ('.py','.cs','.c','.cpp','.h','.s','.json','.js','.html','.css','.md','.txt','.yml'):
   assert not PRIVATE.search(raw),'Private path/key candidate: '+name
  if name.endswith('.zip') and not (source and name.startswith('vendor/downloads/')):
   with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert len(z.namelist())==len(set(z.namelist())),'Duplicate ZIP entries: '+name
    inspect({x:z.read(x) for x in z.namelist() if not x.endswith('/')})
def docs(root):
 for path in [root/'README.md',*sorted((root/'docs').glob('*.md'))]:
  text=path.read_text(encoding='utf-8-sig');assert '\u2014' not in text,path
  for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
   if link.startswith(('https://','http://','#')):continue
   target=link.split('#')[0];assert (path.parent/target).exists(),f'{path.name}: {link}'
 raw=(root/'app/assets/pictoplus.ico').read_bytes()
 for i in range(struct.unpack_from('<H',raw,4)[0]):
  w,h,_,_,_,_,n,at=struct.unpack_from('<BBBBHHII',raw,6+i*16);assert raw[at:at+n]==(root/f'docs/images/icon-{w or 256}.png').read_bytes()
def run():
 archive=ROOT/'build/public-release/PictoPlus-Windows-USA.zip'
 with zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==len(set(z.namelist()));entries={n:z.read(n) for n in z.namelist()}
  inspect(entries);manifest=json.loads(entries['release-manifest.json'])
  for name,value in manifest.items():assert hashlib.sha256(entries[name]).hexdigest()==value['sha256'],name
  assert entries['LICENSE']==(ROOT/'LICENSE').read_bytes()
  assert 'LICENSES/Noto-OFL.txt' in entries and 'SOURCE/loader-startup.s' in entries
  assert not any('visual-preview' in n for n in entries)
  setup=entries['app/distribution/USA/PictoPlus-USA-SD-Setup.zip']
  assert setup==(ROOT/'build/public-release/PictoPlus-USA-SD-Setup.zip').read_bytes()
  with zipfile.ZipFile(io.BytesIO(setup)) as sd:
   assert 'PictoPlus/licenses/Noto-OFL.txt' in sd.namelist()
 docs(ROOT)
 result=dict(binary_entries=len(entries),binary_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),icons_match=True,docs_links=True,game_assets_or_private_paths_found=False,history='No project Git repository supplied; external history not certified',legal_clearance=False)
 source=ROOT/'build/public-release/PictoPlus-Source.zip'
 if source.exists():
  with zipfile.ZipFile(source) as z:inspect({n:z.read(n) for n in z.namelist()},source=True)
  result['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
 (ROOT/'build/public-release/release-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result
if __name__=='__main__':run()

"""Curate a new source archive; never publish or modify Git history."""
import hashlib,json,pathlib,shutil,uuid,zipfile
from audit_public_release import inspect,docs
ROOT=pathlib.Path(__file__).resolve().parents[1]
def prepare():
 release=ROOT/'build/public-release';archive=release/'PictoPlus-Windows-USA.zip';entries={}
 with zipfile.ZipFile(archive) as z:
  for name in z.namelist():
   p=pathlib.PurePosixPath(name)
   if name.startswith(('app/','tools/')) and p.suffix in ('.py','.js','.css','.html','.json','.png','.ico','.cs','.zip','.manifest'):
    entries[name]=z.read(name)
   elif name in ('app/native/Microsoft.Web.WebView2.Core.dll','app/native/Microsoft.Web.WebView2.WinForms.dll','app/native/WebView2Loader.dll'):entries[name]=z.read(name)
   elif name.startswith('LICENSES/'):entries[name]=z.read(name)
 def put(name,path):entries[name]=path.read_bytes()
 for name in ('README.md','LICENSE','CONTRIBUTING.md','SECURITY.md','CHANGELOG.md'):put(name,ROOT/name)
 for p in sorted((ROOT/'app/native').glob('*.cs')):put(p.relative_to(ROOT).as_posix(),p)
 for name in ('BlockCatalog','BookCover','BuildCustomModel','StudioArtwork','StudioDefaultCover','Thumbnail'):put('tools/modeltool/'+name+'.cs',ROOT/'tools/modeltool'/(name+'.cs'))
 put('app/native/PictoPlus.manifest',ROOT/'app/native/PictoPlus.manifest')
 for folder in ('docs','.github','native'):
  for p in sorted((ROOT/folder).rglob('*')):
   if p.is_file():put(p.relative_to(ROOT).as_posix(),p)
 for name in ('release_build.py','release-dependencies.json','package_public_app.py','build_public_loader.py','audit_public_release.py','prepare_public_source.py','build_picto_loading_assets.ps1','test_release_preparation.py','test_puzzle_grid.py'):put('tools/'+name,ROOT/'tools'/name)
 for p in sorted((ROOT/'tools/branding').rglob('*')):
  if p.is_file() and p.suffix in ('.py','.ttf','.txt','.json'):put(p.relative_to(ROOT).as_posix(),p)
 for p in sorted((ROOT/'tools/SPICA/SPICA').rglob('*.cs')):put(p.relative_to(ROOT).as_posix(),p)
 put('tools/SPICA/LICENSE.txt',ROOT/'tools/SPICA/LICENSE.txt')
 for p in (ROOT/'app').glob('*.test.mjs'):put(p.relative_to(ROOT).as_posix(),p)
 put('app/vendor/package/package.json',ROOT/'app/vendor/package/package.json')
 put('app/vendor/package/LICENSE',ROOT/'app/vendor/package/LICENSE')
 put('app/vendor/webview2/LICENSE.txt',ROOT/'app/vendor/webview2/LICENSE.txt')
 put('app/assets/covers/PROMPTS.md',ROOT/'app/assets/covers/PROMPTS.md')
 lock=json.loads((ROOT/'tools/release-dependencies.json').read_text())
 from release_build import dependency_path
 for name in lock['files']:
  put('vendor/downloads/'+pathlib.PurePosixPath(name).name if name.startswith('build/release-downloads/') else name,dependency_path(ROOT,name))
 put('vendor/downloads/'+pathlib.PurePosixPath(lock['python']['archive']).name,dependency_path(ROOT,lock['python']['archive']))
 downloads=ROOT/'vendor/downloads' if (ROOT/'vendor/downloads').exists() else ROOT/'build/release-downloads'
 for name in ('MPL-2.0.txt','libctru-README.txt','newlib-notices.txt','GCC-runtime-exception.txt','GPL-3.0.txt'):put('vendor/downloads/'+name,downloads/name)
 if (ROOT/'tools/roslyn/ThirdPartyNotices.rtf').exists():put('LICENSES/Roslyn-ThirdPartyNotices.rtf',ROOT/'tools/roslyn/ThirdPartyNotices.rtf')
 put('LICENSES/Roslyn-MIT.txt',ROOT/'LICENSES/Roslyn-MIT.txt')
 entries['app/public-release.json']=json.dumps(dict(format=1,region='USA',authoring='local-installed-game-profile',hardware_verified=False)).encode()
 entries['.gitignore']=b'/build/\n/work/\n/backups/\n/app/data/\n__pycache__/\n*.py[cod]\n*.log\n*.pictosetup\n*.pictoauthoring\n*.pictobook\n*.voxbook\n*.voxpack\n*.3ds\n*.cci\n*.cia\n*.bch\n*.qpp\n*.ctpk\n*.msbt\n*.arc\n*.sav\n/tools/modeltool/*.exe\n/tools/modeltool/SPICA.dll\n/app/native/PictoPlus*.exe\n/PictoPlus.exe\n'
 inspect(entries,source=True)
 entries['SOURCE-MANIFEST.json']=json.dumps({n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in sorted(entries.items())},indent=2).encode()
 target=release/'PictoPlus-Source.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in sorted(entries.items()):info=zipfile.ZipInfo(n,(2026,11,3,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
 stage=ROOT/'build/public-source'/uuid.uuid4().hex;stage.mkdir(parents=True)
 with zipfile.ZipFile(target) as z:z.extractall(stage)
 docs(stage)
 report=dict(source=str(target),directory=str(stage),files=len(entries),bytes=target.stat().st_size)
 (release/'source-preparation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));return stage
if __name__=='__main__':prepare()

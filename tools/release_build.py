"""Pinned, deterministic .NET release builds. No packing, injection or self-extraction."""
import hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
HELPERS=('BlockCatalog','BuildCustomModel','StudioArtwork','StudioDefaultCover','Thumbnail')
FLAGS=['/nologo','/noconfig','/codepage:65001','/deterministic+','/optimize+','/debug-','/r:System.dll','/r:System.Core.dll']

def dependency_path(root,name):
 path=root/name
 if not path.is_file() and name.startswith('build/release-downloads/'):
  path=root/'vendor/downloads'/path.name
 return path
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def source_tree(path):
 return {p.relative_to(path).as_posix():sha(p) for p in sorted(path.rglob('*.cs'))}
def verify_inputs(root=ROOT):
 lock=json.loads((root/'tools/release-dependencies.json').read_text())
 for name,expected in {**lock['files'],lock['python']['archive']:lock['python']['sha256']}.items():
  if sha(dependency_path(root,name))!=expected:raise ValueError('Release dependency changed: '+name)
 tree=source_tree(root/lock['spica']['source'])
 if hashlib.sha256(json.dumps(tree,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=lock['spica']['source_tree_sha256']:raise ValueError('SPICA source changed; review the upstream pin before release.')
 return lock

def build(output):
 lock=verify_inputs();output=pathlib.Path(output);output.mkdir(parents=True,exist_ok=True)
 compiler=ROOT/'tools/roslyn/tasks/net472/csc.exe'
 def compile(name,sources,options=()):
  result=subprocess.run([str(compiler),*FLAGS,*options,'/out:'+str((output/name).relative_to(ROOT)),*sources],cwd=ROOT,capture_output=True,text=True)
  if result.returncode:raise RuntimeError('Release compilation failed: '+name+'\n'+'\n'.join(line for line in (result.stdout+result.stderr).splitlines() if ': error ' in line))
 assembly='app/native/AssemblyInfo.cs';manifest='/win32manifest:app/native/PictoPlus.manifest';icon='/win32icon:app/assets/pictoplus.ico'
 compile('PictoPlus-v07.exe',['app/native/Studio.cs',assembly,'app/native/InstallerIntegrity.cs'],['/target:winexe','/platform:x64',manifest,icon,'/r:System.Drawing.dll','/r:System.Windows.Forms.dll','/r:System.Web.Extensions.dll',*[f'/r:app/native/Microsoft.Web.WebView2.{n}.dll' for n in ('Core','WinForms')]])
 compile('PictoPlus.exe',['app/native/Launcher.cs',assembly],['/target:winexe','/platform:x64','/define:PICTOPLUS_LAUNCHER',manifest,icon,'/r:System.Windows.Forms.dll'])
 model=output/'modeltool';model.mkdir(exist_ok=True)
 spica_sources=[str(p.relative_to(ROOT)) for p in sorted((ROOT/lock['spica']['source']).rglob('*.cs'))]
 # .NET Framework reflection order can change after a partial field lookup/GC.
 # SPICA's binary format follows declaration order; make that order explicit.
 serialization=ROOT/lock['spica']['source']/'Serialization/BinarySerialization.cs'
 patch=output/'SPICA-BinarySerialization.cs';original=serialization.read_text(encoding='utf-8-sig')
 assert original.count('ObjectType.GetFields(Binding)')==1
 patch.write_text(original.replace('ObjectType.GetFields(Binding)','System.Linq.Enumerable.OrderBy(ObjectType.GetFields(Binding), field => field.MetadataToken)'),encoding='utf-8')
 spica_sources=[str(patch.relative_to(ROOT)) if name==str(serialization.relative_to(ROOT)) else name for name in spica_sources]

 compile('modeltool/SPICA.dll',spica_sources,['/target:library','/unsafe','/r:System.Drawing.dll','/r:System.Numerics.dll','/r:System.Numerics.Vectors.dll','/r:System.Xml.dll','/r:Microsoft.CSharp.dll'])
 for name in HELPERS:
  sources=['tools/modeltool/'+name+'.cs']
  if name in ('BuildCustomModel','StudioArtwork'):sources.append('tools/modeltool/BookCover.cs')
  compile('modeltool/'+name+'.exe',sources,['/target:exe','/main:'+name,'/r:'+str((model/'SPICA.dll').relative_to(ROOT)),'/r:System.Drawing.dll','/r:System.Numerics.dll','/r:System.Numerics.Vectors.dll','/r:System.Web.Extensions.dll'])
 sources=['app/native/Launcher.cs','app/native/Studio.cs',assembly,'app/native/InstallerIntegrity.cs','app/native/PictoPlus.manifest','tools/package_public_app.py','tools/release_build.py','tools/release-dependencies.json',*['tools/modeltool/'+name+'.cs' for name in HELPERS],'tools/modeltool/BookCover.cs']
 return dict(format=1,version='0.8.0',compiler_sha256=sha(compiler),compiler_flags=FLAGS,dependencies=lock,compatibility_patches={"SPICA declaration-order deserialization":sha(patch)},source_sha256={name:sha(ROOT/name) for name in sources},binary_sha256={p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*')) if p.suffix in ('.exe','.dll')},signing='PictoPlus binaries are unsigned; no signing certificate is available. Microsoft/Python binaries retain upstream signatures.')
if __name__=='__main__':
 try:print(json.dumps(build(ROOT/'build/security-review/rebuild'),indent=2))
 except subprocess.CalledProcessError as error:print(error.stdout,error.stderr);raise

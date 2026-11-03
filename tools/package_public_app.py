"""Explicit public Windows x64 allowlist. No work/, build assets or user data."""
import hashlib,json,pathlib,re,shutil,subprocess,sys,zipfile
from release_build import build as build_release,dependency_path
ROOT=pathlib.Path(__file__).resolve().parents[1]
APP_PY=['authoring_setup','book_packs','core','difficulty_options','distribution','export_assets','export_preparation','game_asset_edits','import_contacts','import_shapes','import_surfaces','import_symmetry','native_book','windows_process','number_layouts','pack_install','server','voxelise']
TOOLS_PY=['game_resources','colour_logic','clue_difficulty','design_fitted_puzzle','group_certificate','puzzle_format','msbt','scoring','fit_native_shapes','mesh_voxels','build_block_tests']
HELPERS=['BlockCatalog','BuildCustomModel','StudioArtwork','StudioDefaultCover','Thumbnail']
def package():
    out=ROOT/'build/public-release';out.mkdir(parents=True,exist_ok=True);host=out/'host';host.mkdir(exist_ok=True)
    provenance=build_release(host)
    entries={}
    entries['SOURCE/SPICA-BinarySerialization.cs']=(host/'SPICA-BinarySerialization.cs').read_bytes()
    def put(name,path):entries[name]=pathlib.Path(path).read_bytes()
    put('PictoPlus.exe',host/'PictoPlus.exe');put('app/native/PictoPlus-v07.exe',host/'PictoPlus-v07.exe')
    for name in ('Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','WebView2Loader.dll'):put('app/native/'+name,ROOT/'app/native'/name)
    for name in APP_PY:put('app/'+name+'.py',ROOT/'app'/(name+'.py'))
    for name in TOOLS_PY:put('tools/'+name+'.py',ROOT/'tools'/(name+'.py'))
    for p in (ROOT/'app').iterdir():
        if p.suffix in ('.js','.css','.html') and '.test.' not in p.name and not p.name.startswith('visual-preview.'):put('app/'+p.name,p)
    put('app/assets/covers/catalog.json',ROOT/'app/assets/covers/catalog.json')
    for cover in json.loads((ROOT/'app/assets/covers/catalog.json').read_text(encoding='utf-8')):
        for name in (cover['art'],'previews/'+cover['id']+'.png'):
            p=(ROOT/'app/assets/covers'/name).resolve();p.relative_to((ROOT/'app/assets/covers').resolve());put(p.relative_to(ROOT).as_posix(),p)
    for name in ('pictoplus-logo.png','pictoplus.ico'):put('app/assets/'+name,ROOT/'app/assets'/name)
    shape_map=ROOT/'app/config/native-shape-map.json'
    put('app/config/native-shape-map.json',shape_map if shape_map.is_file() else ROOT/'build/native-shape-map.json')
    put('app/config/authoring-manifest.json',ROOT/'app/config/authoring-manifest.json')
    with zipfile.ZipFile(dependency_path(ROOT,provenance['dependencies']['python']['archive'])) as runtime:
        for item in runtime.infolist():
            if not item.is_dir():entries['app/runtime/python/'+item.filename]=runtime.read(item)
    three=(ROOT/'app/vendor/package').resolve();pending=[three/'build/three.module.js']
    pending += [three/'examples/jsm'/name for name in re.findall(r"from ['\"]three/addons/([^'\"]+)", (ROOT/'app/studio.js').read_text(encoding='utf-8'))]
    visited=set()
    while pending:
        p=pending.pop().resolve()
        if p in visited:continue
        p.relative_to(three);visited.add(p);put(p.relative_to(ROOT).as_posix(),p)
        for dep in re.findall(r"(?:from|import)\s*['\"]([^'\"]+)['\"]",p.read_text(encoding='utf-8')):
            if dep.startswith('.'):pending.append(p.parent/dep)
    put('app/vendor/package/LICENSE',ROOT/'app/vendor/package/LICENSE')
    for name in HELPERS:
        for suffix in ('.exe','.cs'):put('tools/modeltool/'+name+suffix,(host/'modeltool' if suffix=='.exe' else ROOT/'tools/modeltool')/(name+suffix))
    put('tools/modeltool/BookCover.cs',ROOT/'tools/modeltool/BookCover.cs');put('tools/modeltool/SPICA.dll',host/'modeltool/SPICA.dll')
    put('app/distribution/USA/build-info.json',ROOT/'app/distribution/USA/build-info.json')
    downloads=ROOT/'vendor/downloads' if (ROOT/'vendor/downloads').is_dir() else ROOT/'build/release-downloads'
    put('app/runtime/MicrosoftEdgeWebview2Setup.exe',downloads/'MicrosoftEdgeWebview2Setup.exe')
    artic=ROOT/'native/vendor/ArticBase-MIT.txt'
    licenses={'SPICA-Unlicense.txt':ROOT/'tools/SPICA/LICENSE.txt','three-MIT.txt':ROOT/'app/vendor/package/LICENSE','Python.txt':ROOT/'app/runtime/python/LICENSE.txt','WebView2-SDK.txt':ROOT/'app/vendor/webview2/LICENSE.txt','ArticBase-MIT.txt':artic if artic.is_file() else ROOT/'tools/native-loader/artic-source/LICENSE','MPL-2.0.txt':downloads/'MPL-2.0.txt','libctru.txt':downloads/'libctru-README.txt','newlib.txt':downloads/'newlib-notices.txt','GCC-runtime-exception.txt':downloads/'GCC-runtime-exception.txt','GPL-3.0.txt':downloads/'GPL-3.0.txt'}
    for name,path in licenses.items():
        if name!='Python.txt':put('LICENSES/'+name,path)
    put('LICENSES/Noto-OFL.txt',ROOT/'tools/branding/fonts/OFL.txt')
    put('LICENSE',ROOT/'LICENSE')
    for p in (ROOT/'docs').glob('*.md'):put('docs/'+p.name,p)
    for p in (ROOT/'docs/images').glob('*.png'):put('docs/images/'+p.name,p)
    for name in ('README.md','CONTRIBUTING.md','SECURITY.md','CHANGELOG.md'):put(name,ROOT/name)
    entries['LICENSES/Python.txt']=entries['app/runtime/python/LICENSE.txt']
    put('SOURCE/loader-startup.s',ROOT/'native/usa/startup.s');put('SOURCE/loader-csvc.s',ROOT/'native/vendor/csvc.s')
    put('SOURCE/loader-font-atlas.ps1',ROOT/'tools/build_picto_loading_assets.ps1')
    for name in ('NotoSans-Bold.ttf','OFL.txt'):put('SOURCE/fonts/'+name,ROOT/'tools/branding/fonts'/name)
    for name in ('Studio.cs','Launcher.cs','AssemblyInfo.cs','InstallerIntegrity.cs','PictoPlus.manifest'):put('SOURCE/'+name,ROOT/'app/native'/name)
    for name in ('release_build.py','release-dependencies.json','package_public_app.py'):put('SOURCE/'+name,ROOT/'tools'/name)
    entries['BUILD-PROVENANCE.json']=json.dumps(provenance,indent=2).encode()
    entries['app/public-release.json']=json.dumps({'format':1,'region':'USA','authoring':'local-installed-game-profile','hardware_verified':False}).encode()
    entries['THIRD-PARTY-NOTICES.txt']=b'Original PictoPlus code is MIT licensed; see LICENSE. Dependencies retain their licences: Python (PSF and bundled library notices), three.js (MIT), SPICA (Unlicense; declaration-order fix in SOURCE/SPICA-BinarySerialization.cs), Microsoft WebView2 SDK/bootstrapper, libctru, newlib and GCC runtime components. See LICENSES/. The loader atlas uses Noto Sans Bold (SIL OFL 1.1); its font and generator are in SOURCE/. Modified ArticBase startup is MPL 2.0, with complete modified source in SOURCE/loader-startup.s. csvc.s retains its permissive notice. Microsoft runtime installation uses its own terms and may need internet. No extracted Nintendo assets are included. Compatibility patch metadata remains subject to the review notes in docs/RELEASE-AUDIT.md; this is not legal clearance. Do not relicense the whole bundle MIT.\n'
    import io
    setup=io.BytesIO()
    with zipfile.ZipFile(ROOT/'app/distribution/USA/PictoPlus-USA-SD-Setup.zip') as original,zipfile.ZipFile(setup,'w',zipfile.ZIP_DEFLATED) as target:
        for item in original.infolist():
            if not item.filename.startswith('PictoPlus/licenses/'):target.writestr(item,original.read(item))
        for name in ('MPL-2.0.txt','libctru.txt','newlib.txt','GCC-runtime-exception.txt','GPL-3.0.txt','ArticBase-MIT.txt','Noto-OFL.txt'):target.writestr(zipfile.ZipInfo('PictoPlus/licenses/'+name,(2026,11,2,0,0,0)),entries['LICENSES/'+name])
        target.writestr(zipfile.ZipInfo('PictoPlus/licenses/loader-startup.s',(2026,11,2,0,0,0)),entries['SOURCE/loader-startup.s']);target.writestr(zipfile.ZipInfo('PictoPlus/licenses/loader-csvc.s',(2026,11,2,0,0,0)),entries['SOURCE/loader-csvc.s'])
        target.writestr(zipfile.ZipInfo('PictoPlus/licenses/NOTICE.txt',(2026,11,2,0,0,0)),entries['THIRD-PARTY-NOTICES.txt'])
    entries['app/distribution/USA/PictoPlus-USA-SD-Setup.zip']=setup.getvalue()
    (out/'PictoPlus-USA-SD-Setup.zip').write_bytes(setup.getvalue())
    entries['PictoPlus-First-Time-Setup.txt']=b'PictoPlus - Windows 10 22H2 / Windows 11 x64, USA game\n\nExtract this entire ZIP into a writable folder, then run PictoPlus.exe. Python and the compiler helpers are included. If Microsoft WebView2 is missing, PictoPlus offers the included official installer (one-time internet download).\n\nFirst use: choose Download USA SD Setup, extract to SD root and launch your legitimately installed USA Picross 3D: Round 2 with Luma plugins enabled. Let Preparing first-time setup finish. Back on the PC, choose Import setup file and select SD:/PictoPlus/PictoPlus-Setup.pictosetup. The app validates it and finishes setup automatically. This file contains your local game resources: keep it private. No ROM dump or manual extraction is needed.\n\nThen create puzzles/books and export .pictobook files. Copy books to SD:/PictoPlus/Books, or the same folder on the emulator virtual SD, and restart the game. Use the updated USA loader; EUR is separate. Keep registry and progress files.\n\nEarlier USA setup and gameplay were verified by the owner. The final release candidate still needs the hardware smoke test, including its updated loading font. No game assets, sample game books or user data are included in this ZIP. See HARDWARE-TEST.md.\n'
    entries['HARDWARE-TEST.md']=(ROOT/'docs/HARDWARE-TEST.md').read_bytes()
    forbidden=('native-block-catalog','native-shape-samples','fitted-torpedo','availability-template')
    assert not any(name.startswith(('work/','build/','app/data/')) or any(x in name for x in forbidden) for name in entries)
    assert not any(pathlib.PurePosixPath(n).suffix.lower() in ('.bch','.qpp','.ctpk','.msbt','.arc','.3ds','.cci','.cia','.pictoauthoring','.pictosetup') for n in entries)
    hashes={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in entries.items()}
    entries['release-manifest.json']=json.dumps(hashes,indent=2).encode()
    target=out/'PictoPlus-Windows-USA.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(entries.items()):
            info=zipfile.ZipInfo(name,(2026,11,2,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
    print(json.dumps(dict(file=str(target),files=len(entries),bytes=target.stat().st_size)))
    return target
if __name__=='__main__':package()

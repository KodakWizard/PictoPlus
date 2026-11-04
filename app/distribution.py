"""Allowlisted standalone USA setup; never export private console-test archives."""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
SETUP_FILES={'luma/plugins/0004000000187D00/PictoPlus.3gx','PictoPlus/Books/','PictoPlus-First-Time-Setup.txt','PictoPlus/Setup files/Create setup file/authoring.request','PictoPlus/Setup files/Skip Setup/authoring.skip'}
SETUP_NOTICES={'PictoPlus/licenses/'+name for name in ('MPL-2.0.txt','loader-startup.s','loader-csvc.s','NOTICE.txt','libctru.txt','newlib.txt','GCC-runtime-exception.txt','GPL-3.0.txt','ArticBase-MIT.txt','Noto-OFL.txt')}
def usa_setup():
    folder=ROOT/'app/distribution/USA';source=folder/'PictoPlus-USA-SD-Setup.zip'
    if not source.is_file():raise ValueError('Build the standalone USA setup before exporting it.')
    info=json.loads((folder/'build-info.json').read_text())
    with zipfile.ZipFile(source) as z:
        names=z.namelist();actual=set(names)
        if len(names)!=len(actual) or not SETUP_FILES<=actual or actual-(SETUP_FILES|SETUP_NOTICES):raise ValueError('Unexpected files in the USA setup package.')
        raw=z.read('luma/plugins/0004000000187D00/PictoPlus.3gx')
        if hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('USA setup integrity check failed.')
    return source

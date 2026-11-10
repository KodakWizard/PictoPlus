"""Validate the bundled SD installer before offering it to the user."""
import hashlib,json,pathlib,struct,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
TITLE_IDS={'USA':'0004000000187D00','EUR':'0004000000187E00'}
PLUGINS={region:f'luma/plugins/{title}/PictoPlus.3gx' for region,title in TITLE_IDS.items()}
SETUP_FILES=set(PLUGINS.values())|{'PictoPlus/Books/','PictoPlus-First-Time-Setup.txt','PictoPlus/Setup files/Create setup file/authoring.request','PictoPlus/Setup files/Skip Setup/authoring.skip'}
SETUP_NOTICES={'PictoPlus/licenses/'+name for name in ('MPL-2.0.txt','loader-startup.s','loader-csvc.s','NOTICE.txt','libctru.txt','newlib.txt','GCC-runtime-exception.txt','GPL-3.0.txt','ArticBase-MIT.txt','Noto-OFL.txt')}

def sd_loader():
    folder=ROOT/'app/distribution';source=folder/'PictoPlus-SD-Loader.zip'
    if not source.is_file():raise ValueError('Build the combined SD loader before exporting it.')
    info=json.loads((folder/'build-info.json').read_text())
    with zipfile.ZipFile(source) as z:
        names=z.namelist();actual=set(names)
        if len(names)!=len(actual) or not SETUP_FILES<=actual or actual-(SETUP_FILES|SETUP_NOTICES):
            raise ValueError('Unexpected files in the SD loader package.')
        for region,name in PLUGINS.items():
            raw=z.read(name)
            count,offset=struct.unpack_from('<II',raw,128)
            if (raw[:8]!=b'3GX$0002' or count!=1 or offset>len(raw)-4 or
                struct.unpack_from('<I',raw,offset)[0]!=int(TITLE_IDS[region][-8:],16) or
                info[region]['title_id']!=TITLE_IDS[region] or
                hashlib.sha256(raw).hexdigest()!=info[region]['sha256']):
                raise ValueError(f'{region} loader integrity check failed.')
    return source

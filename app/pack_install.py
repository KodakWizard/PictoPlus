"""Transactional desktop pack sync; shared by Azahar and Luma staging exports."""
import hashlib, json, os, pathlib, shutil, tempfile, uuid, zipfile
from book_packs import ROOT, TITLE, LUMA_READY, scan, compile_catalog


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2),encoding='utf-8');os.replace(temporary,path)


def sync(packs_folder, state_folder, target=None, luma_zip=None):
    """Only touch files owned by this manager. Keep IDs for absent packs as tombstones."""
    if luma_zip and not LUMA_READY:
        raise ValueError('Luma export is temporarily blocked: its LayeredFS code overlaps the current paging patch. A relocated patch must be verified first.')
    packs=scan(packs_folder)
    if not packs:raise ValueError('Add at least one .pictopack or legacy .voxpack file to the Book Packs folder.')
    state_folder=pathlib.Path(state_folder).resolve();state_folder.mkdir(parents=True,exist_ok=True)
    lock=state_folder/'sync.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise ValueError('Another pack sync is active, or a previous sync needs recovery.')
    os.close(fd)
    try:
        if (state_folder/'pending.json').exists():raise ValueError('A previous sync was interrupted. Restore its backup before syncing again.')
        old=json.loads((state_folder/'state.json').read_text(encoding='utf-8')) if (state_folder/'state.json').exists() else None
        with tempfile.TemporaryDirectory(prefix='pack-stage-',dir=state_folder) as staging:
            output=pathlib.Path(staging)/'package'
            manifest,registry=compile_catalog(packs,output,old['registry'] if old else None)
            if luma_zip:
                if old and old['target'] is not None:raise ValueError('Use separate state folders for Azahar and Luma.')
                destination=pathlib.Path(luma_zip).resolve()
                if destination.exists():raise ValueError('Choose a new filename for the Luma ZIP.')
                destination.parent.mkdir(parents=True,exist_ok=True)
                temporary=destination.with_suffix('.tmp')
                try:
                    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
                        for name in manifest['files']:archive.write(output/'romfs'/name,f'luma/titles/{TITLE}/romfs/{name}')
                        archive.write(output/'code.ips',f'luma/titles/{TITLE}/code.ips')
                        archive.writestr('READ ME.txt','Combined European Picross 3D: Round 2 book packs.\nCopy luma to your SD root and enable game patching.\nNo external save editing or Checkpoint restore. Physical 3DS test pending.\nKeep this pack manager state when adding or removing packs; it owns your permanent progress mapping.\n')
                        archive.writestr('installed-books.json',json.dumps(manifest['packs'],indent=2))
                    temporary.replace(destination)
                    atomic(state_folder/'state.json',{'registry':registry,'files':{},'target':None,'packs':manifest['packs']})
                finally:temporary.unlink(missing_ok=True)
                return {'file':str(destination),'packs':manifest['packs'],'puzzles':len(manifest['save_indices'])}
            if target is None:raise ValueError('Choose an Azahar title-mod folder or a Luma ZIP output.')
            target=pathlib.Path(target).resolve()
            if old and old['target']!=str(target):raise ValueError('This progress registry belongs to a different installation.')
            sources={'romfs/'+name:output/'romfs'/name for name in manifest['files']}
            sources['exefs/code.ips']=output/'code.ips'
            previous=old['files'] if old else {}
            names=set(sources)|set(previous)
            for name in names:
                path=target/name
                if not path.resolve().is_relative_to(target):raise ValueError('Invalid managed output path.')
                if name in previous:
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=previous[name]:
                        raise ValueError('An installed file changed outside the pack manager: '+name)
                elif path.exists():raise ValueError('Another mod already owns this file: '+name)
            backup=state_folder/'backups'/uuid.uuid4().hex;backup.mkdir(parents=True)
            atomic(backup/'state-before.json',old)
            for name in previous:
                path=backup/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target/name,path)
            pending={'target':str(target),'backup':str(backup),'previous':previous,'new_files':sorted(sources)}
            atomic(state_folder/'pending.json',pending)
            consistent=False
            try:
                for name,source in sources.items():
                    path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
                    temporary=path.with_name(path.name+'.pack-tmp');shutil.copy2(source,temporary);os.replace(temporary,path)
                for name in set(previous)-set(sources):(target/name).unlink()
                hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sources.items()}
                atomic(state_folder/'state.json',{'registry':registry,'files':hashes,'target':str(target),'packs':manifest['packs']})
                consistent=True
            except Exception:
                for name in names:
                    path=target/name
                    if name in previous:path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(backup/name,path)
                    elif path.exists():path.unlink()
                consistent=True
                raise
            finally:
                if consistent:(state_folder/'pending.json').unlink(missing_ok=True)
            return {'packs':manifest['packs'],'puzzles':len(manifest['save_indices']),'target':str(target),'save_files_edited':False}
    finally:lock.unlink(missing_ok=True)

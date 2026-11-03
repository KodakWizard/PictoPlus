"""Loopback-only UI bridge. Authenticated API, no uploaded files leave this PC."""
import argparse,concurrent.futures,hashlib,http.server,json,mimetypes,pathlib,secrets,sys,threading,time,traceback,urllib.parse
APP=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(APP))
import core
from export_preparation import PREPARATION
STATIC_TYPES={'.html':'text/html','.css':'text/css','.js':'application/javascript','.json':'application/json','.png':'image/png','.ico':'image/x-icon','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml','.woff':'font/woff','.woff2':'font/woff2','.ttf':'font/ttf','.wasm':'application/wasm','.glb':'model/gltf-binary','.gltf':'model/gltf+json'}
TOKEN=secrets.token_urlsafe(32);JOBS={};JOB_PROGRESS={};POOL=concurrent.futures.ThreadPoolExecutor(max_workers=2);MUTATE=threading.RLock()
RESOURCE_READY=None
BACKGROUND_STARTED=False

def resources_ready():
    # Validate the installed set once per process, not on every navigation.
    global RESOURCE_READY
    if RESOURCE_READY is None:
        import game_resources
        RESOURCE_READY=game_resources.ready()
    return RESOURCE_READY

def begin_background_preparation():
    global BACKGROUND_STARTED
    with MUTATE:
        if BACKGROUND_STARTED or not resources_ready():return
        BACKGROUND_STARTED=True
    def prepare():
        try:PREPARATION.start_library()
        except Exception:
            with (core.DATA/'error.log').open('a',encoding='utf-8') as log:traceback.print_exc(file=log)
    threading.Thread(target=prepare,name='startup-preparation',daemon=True).start()
def start_job(fn,progress=False):
    id=secrets.token_hex(12)
    started=time.monotonic()
    def report(value):JOB_PROGRESS[id]=dict(value,elapsed_seconds=round(time.monotonic()-started,1))
    if progress:report({'completed':0,'total':1,'stage':'Preparing books'})
    def run():
        try:return {'done':True,'result':fn(report) if progress else fn()}
        except (AssertionError,ValueError) as e:return {'done':True,'error':str(e) or 'This operation could not be completed.'}
        except Exception as e:
            with (core.DATA/'error.log').open('a',encoding='utf-8') as log:traceback.print_exc(file=log)
            return {'done':True,'error':'The operation failed. Details were saved to the local error log.'}
    JOBS[id]=POOL.submit(run);return {'job':id}

def interactive(fn):
    with PREPARATION.export_priority():return fn()
def dispatch(route,data):
    if route=='startup-ready':
        begin_background_preparation();return {'ready':True}
    if route=='authoring-status':
        return {'ready':resources_ready(),'region':'USA','requires_installed_game':True}
    if route=='authoring-setup':
        import uuid
        from authoring_setup import setup_archive
        folder=core.DATA/'exports'/uuid.uuid4().hex;folder.mkdir(parents=True)
        target=folder/'PictoPlus-USA-SD-Setup.zip';setup_archive(target)
        return {'file':str(target.relative_to(core.DATA/'exports'))}
    if route=='preparation-activity':PREPARATION.editing();return {'paused':True}
    if route=='prepare-export':
        document=core.check(data['document']);assert document['cells'],'Add blocks before preparing.'
        key=str(document.get('id') or data.get('key','draft'))[:128]
        with MUTATE:
            books_path=core.DATA/'books.json'
            books=json.loads(books_path.read_text(encoding='utf-8')) if books_path.exists() else []
            book=next((b for b in books if b['name']==document['collection']),{'name':document['collection']})
            enabled=core.settings().get('background_preparation',True)
        PREPARATION.configure(enabled)
        return PREPARATION.request(key,document,book,data.get('previous'))
    if route=='loader-export':
        import shutil,uuid
        from distribution import usa_setup
        source=usa_setup()
        folder=core.DATA/'exports'/uuid.uuid4().hex;folder.mkdir(parents=True)
        target=folder/'PictoPlus-USA-SD-Setup.zip';shutil.copy2(source,target)
        return {'file':str(target.relative_to(core.DATA/'exports'))}
    if route=='books-export':
        def export_books(report):
            with PREPARATION.export_priority(),MUTATE:return core.export_books(data['books'],progress=report)
        return start_job(export_books,progress=True)
    if route in ('book-export','play-pack-export'):
        def export_pack():
            with PREPARATION.export_priority(),MUTATE:return core.export_play_pack(data['ids'])
        return start_job(export_pack)
    if route=='save':
        with MUTATE:result=core.save(data['document'])
        PREPARATION.seed_library([result['id']]);return result
    if route=='book':
        with MUTATE:result=core.save_book(data)
        PREPARATION.seed_library();return result
    if route=='import-book':
        with MUTATE:result=core.import_book(data)
        PREPARATION.seed_library();return result
    if route=='luma-export':
        def export():
            with MUTATE:
                selected=[d for d in core.list_library() if d['id'] in set(data['ids'])]
                return core.export_luma(selected,data.get('save'))
        return start_job(export)
    if route=='delete':
        with MUTATE:result=core.delete_library_item(data['kind'],data.get('id'),data.get('name'))
        PREPARATION.seed_library();return result
    if route=='tune-difficulty':return start_job(lambda:interactive(lambda:core.tune_difficulty(data['document'])))
    if route=='validate':return start_job(lambda:interactive(lambda:core.validate(data['document'])))
    if route=='geometry-hash':
        core.check(data['document']);return {'signature':core.geometry_hash(data['document'])}
    if route=='randomise':return start_job(lambda:interactive(lambda:core.randomise(data['document'],secrets.token_hex(8) if data.get('shuffle') else None)))
    if route=='import-model':return start_job(lambda:interactive(lambda:core.import_model(data['triangles'],data['dimensions'],data.get('fit_shapes',True),data.get('blue',True),data.get('yellow',True),data.get('yellow_ratio'),data.get('blue_inside',True))))
    if route=='settings':
        with MUTATE:result=core.settings(data)
        if 'background_preparation' in data:PREPARATION.configure(result['background_preparation'])
        return result
    if route=='install':
        def perform():
            with MUTATE:
                documents=core.list_library();ids=set(data['ids']);selected=[d for d in documents if d['id'] in ids]
                assert len(selected)==len(ids),'A selected puzzle was not found. Save it first.'
                return core.install(selected,core.settings()['azahar'])
        return start_job(perform)
    if route=='restore':
        with MUTATE:return core.restore(core.settings()['azahar'])
    if route=='launch':return core.launch(core.settings()['azahar'])
    if route=='shutdown':threading.Thread(target=SERVER.shutdown,daemon=True).start();return {'message':'Closing'}
    raise ValueError('Unknown operation.')
class Handler(http.server.BaseHTTPRequestHandler):
    server_version='PictoPlus'
    def log_message(self,*args):pass
    def end_headers(self):
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
        super().end_headers()
    def send_json(self,value,status=200):
        raw=json.dumps(value,ensure_ascii=False).encode('utf-8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
    def permitted(self):
        expected=f'127.0.0.1:{self.server.server_port}'
        return self.headers.get('Host')==expected and self.headers.get('X-Studio-Token')==TOKEN and self.headers.get('Origin',f'http://{expected}')==f'http://{expected}'
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path.startswith('/api/'):
            if not self.permitted():return self.send_json({'error':'Access denied.'},403)
            if path=='/api/loader-package/usa':
                from distribution import usa_setup
                target=usa_setup()
                if not target.is_file():return self.send_json({'error':'The local USA test package is unavailable.'},404)
                raw=target.read_bytes();self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw);return
            if path.startswith('/api/export/'):
                root=(core.DATA/'exports').resolve();target=(root/urllib.parse.unquote(path[len('/api/export/'):])).resolve()
                if not target.is_relative_to(root) or target.suffix not in ('.pictobook','.pictopack','.voxpack','.zip') or not target.is_file():return self.send_json({'error':'Not found.'},404)
                raw=target.read_bytes();self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw);return
            if path=='/api/bootstrap':
                documents=core.list_library()
                return self.send_json({'library':documents,'books':core.list_books(documents=documents),'covers':core.cover_catalog(),'settings':core.settings(),'version':'0.2 preview'})
            if path=='/api/book-previews':return self.send_json(core.list_books(True))
            if path=='/api/preparation':
                selected=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('ids')
                keys=selected[0].split(',')[:512] if selected else None
                return self.send_json(PREPARATION.snapshot(keys))
            if path.startswith('/api/job/'):
                job=JOBS.get(path.rsplit('/',1)[1])
                if job is None:return self.send_json({'error':'Unknown task.'},404)
                return self.send_json(job.result() if job.done() else {'done':False,'progress':JOB_PROGRESS.get(path.rsplit('/',1)[1])})
            return self.send_json({'error':'Not found.'},404)
        import game_resources
        if path in ('/','/index.html') and game_resources.public_build() and not resources_ready():path='/authoring-setup.html'
        aliases={'/assets/default-cover.png':core.ROOT/'build/studio-default-cover.png','/assets/meshes.json':game_resources.generated()/'native-block-catalog.json','/assets/shapes.json':game_resources.shape_map(),'/assets/torpedo.png':core.ROOT/'build/fitted-torpedo-preview.png'}
        target=aliases.get(path)
        if target is None:
            target=(APP/urllib.parse.unquote(path.lstrip('/') or 'index.html')).resolve()
            if not target.is_relative_to(APP) or any(target.is_relative_to(APP/folder) for folder in ('data','runtime','native','config','distribution')) or target.suffix in ('.py','.cs','.exe','.dll','.zip','.tgz'):
                return self.send_json({'error':'Not found.'},404)
        if not target.is_file():return self.send_json({'error':'Not found.'},404)
        raw=target.read_bytes();mime=STATIC_TYPES.get(target.suffix.lower(),'application/octet-stream')
        if target.suffix in ('.html','.css','.js'):mime+='; charset=utf-8'
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache');self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if not self.permitted():return self.send_json({'error':'Access denied.'},403)
        try:
            if urllib.parse.urlsplit(self.path).path=='/api/import-authoring':
                from authoring_setup import LIMIT,import_profile
                assert self.headers.get('Content-Type')=='application/octet-stream','Expected a setup file.'
                length=int(self.headers.get('Content-Length','0'));assert 0<length<=LIMIT,'The setup file must be under 64 MB.'
                folder=core.DATA/'imports';folder.mkdir(parents=True,exist_ok=True);target=folder/(secrets.token_hex(16)+'.pictosetup')
                try:
                    with target.open('wb') as output:
                        left=length
                        while left:
                            chunk=self.rfile.read(min(left,65536));assert chunk,'Incomplete setup file upload.';output.write(chunk);left-=len(chunk)
                except Exception:target.unlink(missing_ok=True);raise
                def import_authoring(report):
                    global RESOURCE_READY
                    try:
                        with PREPARATION.export_priority(),MUTATE:result=import_profile(target,report)
                        RESOURCE_READY=True;begin_background_preparation();return result
                    finally:target.unlink(missing_ok=True)
                return self.send_json(start_job(import_authoring,progress=True))
            if urllib.parse.urlsplit(self.path).path=='/api/import-native-book':
                assert self.headers.get('Content-Type')=='application/octet-stream','Expected a book file.'
                length=int(self.headers.get('Content-Length','0'));assert 0<length<=256*1024*1024,'Book exceeds 256 MB.'
                folder=core.DATA/'imports';folder.mkdir(parents=True,exist_ok=True);target=folder/(secrets.token_hex(16)+'.pictobook')
                try:
                    with target.open('wb') as output:
                        remaining=length
                        while remaining:
                            chunk=self.rfile.read(min(remaining,65536));assert chunk,'Incomplete book upload.'
                            output.write(chunk);remaining-=len(chunk)
                except Exception:target.unlink(missing_ok=True);raise
                def import_uploaded():
                    try:
                        with MUTATE:result=core.import_native_book(target)
                        PREPARATION.seed_library();return result
                    finally:target.unlink(missing_ok=True)
                return self.send_json(start_job(import_uploaded))
            assert self.headers.get('Content-Type','').startswith('application/json'),'Expected JSON.'
            length=int(self.headers.get('Content-Length','0'));assert 0<length<=20_000_000,'The imported file is too large.'
            data=json.loads(self.rfile.read(length));route=urllib.parse.urlsplit(self.path).path.removeprefix('/api/')
            self.send_json(dispatch(route,data))
        except (AssertionError,ValueError,KeyError) as e:self.send_json({'error':str(e) or 'Please check the puzzle and try again.'},400)
        except Exception:
            with (core.DATA/'error.log').open('a',encoding='utf-8') as log:traceback.print_exc(file=log)
            self.send_json({'error':'Something went wrong. The details are in the local error log.'},500)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=0);parser.add_argument('--test-token');parser.add_argument('--data-dir');args=parser.parse_args()
    if args.data_dir:core.DATA=pathlib.Path(args.data_dir).resolve();core.LIBRARY=core.DATA/'library'
    if args.test_token:TOKEN=args.test_token
    core.DATA.mkdir(parents=True,exist_ok=True);core.seed_library()
    import game_resources
    PREPARATION.configure(core.settings().get('background_preparation',True))
    setup_required=game_resources.public_build() and not resources_ready()
    SERVER=http.server.ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(json.dumps({'url':f'http://127.0.0.1:{SERVER.server_port}/?token={TOKEN}','setup_required':setup_required}),flush=True)
    SERVER.serve_forever()

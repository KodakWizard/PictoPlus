"""Latest-edit-only background asset preparation; never gates Export."""
import collections,contextlib,copy,hashlib,json,pathlib,threading,time,uuid

class Superseded(Exception):pass

def signature(doc,book):
    imported=doc.get('imported_model')
    model={k:imported.get(k) for k in ('triangles','uvs','texture','preview','fit_dimensions')} if imported else None
    value=[doc['dimensions'],doc['cells'],doc.get('generation',{}),doc.get('clues',{}).get('layout_seed'),model,doc.get('native_model'),doc.get('native_geometry_hash'),doc.get('source_model'),doc.get('image'),{k:book.get(k) for k in ('name','cover','cover_style','show_cover_title')}]
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Preparation:
    def __init__(self,compiler=None,delay=1.5):
        self.compiler=compiler;self.delay=delay;self.entries=collections.OrderedDict();self.condition=threading.Condition();self.worker=None;self.foreground=0;self.enabled=True;self.closed=False
        self.store=None;self.library=None;self.records={};self.version=None;self.books={};self.scan=collections.deque();self.scan_pending=set();self.active_key=None;self.interactive_until=0;self.editing_until=0

    def start_library(self,library=None,store=None):
        import core
        from export_assets import preparation_version
        with self.condition:
            if self.store is None:
                self.library=pathlib.Path(library or core.LIBRARY);self.store=pathlib.Path(store or core.DATA/'preparation-index.json');self.version=preparation_version()
                try:
                    saved=json.loads(self.store.read_text(encoding='utf-8'))
                    if isinstance(saved,dict) and saved.get('version')==self.version and isinstance(saved.get('puzzles'),dict):self.records=saved['puzzles']
                except (OSError,ValueError):pass
        self.seed_library()

    def seed_library(self,keys=None):
        if self.library is None:return
        try:
            path=self.library.parent/'books.json';books=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        except (OSError,ValueError):books=[]
        with self.condition:
            self.books={b['name']:b for b in books}
            paths=list(self.library.glob('*.json')) if keys is None else [self.library/(key+'.json') for key in keys];ids={p.stem for p in paths}
            if keys is None:
                for key in set(self.records)|set(self.entries):
                    if key not in ids and not key.startswith('draft-'):self.records.pop(key,None);self.entries.pop(key,None)
            for path in paths:
                if str(path) not in self.scan_pending:self.scan.append(path);self.scan_pending.add(str(path))
            self.ensure_worker();self.condition.notify_all()

    def editing(self,seconds=2):
        with self.condition:self.editing_until=time.monotonic()+seconds;self.condition.notify_all()

    def ensure_worker(self):
        if self.worker is None:
            self.worker=threading.Thread(target=self.run,name='export-prepare',daemon=True);self.worker.start()

    @staticmethod
    def stamp(path):
        stat=path.stat();return [stat.st_mtime_ns,stat.st_size]

    @staticmethod
    def book_signature(book):return hashlib.sha256(json.dumps({k:book.get(k) for k in ('name','cover','cover_style','show_cover_title')},sort_keys=True).encode()).hexdigest()

    def scan_file(self,path):
        from export_assets import references_valid
        key=path.stem
        try:stamp=self.stamp(path)
        except OSError:return
        with self.condition:
            current=self.entries.get(key);record=self.records.get(key)
            if current and current['state']=='preparing':return
            if current and current['state']=='queued' and current.get('priority',0)==0:return
            book=self.books.get(record.get('book_name')) if record else None
        if record and record.get('source_stamp')==stamp and book and record.get('book_signature')==self.book_signature(book) and references_valid(record.get('assets')):
            with self.condition:
                if self.entries.get(key) is current:self.entries[key]={'signature':record['signature'],'state':'ready','stage':'Prepared for faster export','done':1,'total':1,'source_stamp':stamp,'priority':2}
            return
        with self.condition:
            if self.entries.get(key) is not current:return
            self.entries[key]={'signature':None,'ticket':uuid.uuid4().hex,'state':'queued' if self.enabled else 'paused','stage':'Preparing library for faster export','done':0,'total':1,'due':time.monotonic()+self.delay,'path':path,'source_stamp':stamp,'priority':2}

    def persist_ready(self,key,entry,performance):
        if self.store is None or key.startswith('draft-') or not performance:return
        path=self.library/(key+'.json')
        try:
            stamp=self.stamp(path);saved=json.loads(path.read_text(encoding='utf-8'))
            if signature(saved,entry['book'])!=entry['signature']:return
        except (OSError,ValueError,KeyError):return
        with self.condition:
            if self.entries.get(key) is not entry:return
            entry['source_stamp']=stamp
            self.records[key]={'signature':entry['signature'],'source_stamp':stamp,'book_name':entry['book']['name'],'book_signature':self.book_signature(entry['book']),'assets':performance.get('cache_assets',[])}
            value={'version':self.version,'puzzles':copy.deepcopy(self.records)}
        import core
        core.atomic(self.store,value)

    def request(self,key,doc,book,previous=None):
        fingerprint=signature(doc,book)
        with self.condition:
            self.active_key=key;self.interactive_until=time.monotonic()+self.delay
            if previous and previous!=key:self.entries.pop(previous,None)
            old=self.entries.get(key)
            if old and old['signature']==fingerprint and old['state']!='attention':
                if old['state'] in ('queued','paused'):old['priority']=0
                self.condition.notify_all()
                return self.public(old)
            snapshot=copy.deepcopy(doc);snapshot.pop('preview',None)
            if snapshot.get('imported_model'):snapshot['imported_model'].pop('original',None)
            entry={'signature':fingerprint,'ticket':uuid.uuid4().hex,'state':'queued' if self.enabled else 'paused','stage':'Preparing for faster export','done':0,'total':1,'due':time.monotonic()+self.delay,'document':snapshot,'book':copy.deepcopy(book),'priority':0}
            self.entries[key]=entry;self.entries.move_to_end(key)
            self.ensure_worker()
            self.condition.notify_all();return self.public(entry)

    @staticmethod
    def public(entry):return {k:entry[k] for k in ('signature','state','stage','done','total')}

    def snapshot(self,keys=None):
        with self.condition:return {key:self.public(self.entries[key]) for key in (self.entries if keys is None else keys) if key in self.entries}

    def configure(self,enabled):
        with self.condition:
            self.enabled=enabled
            for entry in self.entries.values():
                if not enabled and entry['state'] in ('queued','preparing'):entry['state']='paused'
                elif enabled and entry['state']=='paused':entry.update(state='queued',due=time.monotonic()+self.delay)
            self.condition.notify_all()

    @contextlib.contextmanager
    def export_priority(self):
        with self.condition:self.foreground+=1;self.condition.notify_all()
        try:yield
        finally:
            with self.condition:self.foreground-=1;self.condition.notify_all()

    def run(self):
        while True:
            with self.condition:
                if self.closed:return
                if not self.enabled or self.foreground:self.condition.wait();continue
                available=[(key,entry) for key,entry in self.entries.items() if entry['state']=='queued']
                urgent=[pair for pair in available if pair[1].get('priority',0)==0]
                if self.scan and not urgent:
                    path=self.scan.popleft();self.scan_pending.discard(str(path));entry=None
                elif not available:self.condition.wait();continue
                else:key,entry=min(urgent or available,key=lambda pair:(pair[1].get('priority',0),pair[1]['due']))
                if entry is None:
                    # Scan only file/cache metadata; large source models are read
                    # lazily when their turn arrives, not all at app startup.
                    pass
                else:
                    remaining=max(entry['due'],self.editing_until)-time.monotonic()
                    if entry.get('priority',0)>0:remaining=max(remaining,self.interactive_until-time.monotonic())
                    if remaining>0:self.condition.wait(remaining);continue
                    entry['state']='preparing'
            if entry is None:
                try:self.scan_file(path)
                except (OSError,ValueError,KeyError):pass
                time.sleep(.001);continue
            def checkpoint():
                with self.condition:
                    urgent_other=entry.get('priority',0)>0 and (self.active_key!=key and (time.monotonic()<self.interactive_until or any(e['state']=='queued' and e.get('priority',0)==0 for e in self.entries.values())))
                    if self.closed or not self.enabled or self.foreground or time.monotonic()<self.editing_until or urgent_other or self.entries.get(key) is not entry:raise Superseded()
            def progress(value):
                checkpoint()
                with self.condition:entry.update(stage=value['stage'],done=value['completed'],total=value['total'])
            try:
                checkpoint()
                if 'document' not in entry:
                    document=json.loads(entry['path'].read_text(encoding='utf-8'))
                    import core
                    core.check(document)
                    if not document.get('cells'):
                        with self.condition:self.entries.pop(key,None)
                        continue
                    book=self.books.get(document['collection'],{'name':document['collection']})
                    document.pop('preview',None)
                    if document.get('imported_model'):document['imported_model'].pop('original',None)
                    entry.update(document=document,book=book,signature=signature(document,book))
                record=self.records.get(key)
                if record and record['signature']==entry['signature'] and record.get('book_signature')==self.book_signature(entry['book']):
                    from export_assets import references_valid
                    if references_valid(record.get('assets')):
                        checkpoint()
                        with self.condition:entry.update(state='ready',stage='Prepared for faster export',done=entry['total'])
                        self.persist_ready(key,entry,{'cache_assets':record['assets']});entry.pop('document',None);entry.pop('book',None);continue
                if self.compiler is None:
                    from export_assets import compile_assets
                    compiler=compile_assets
                else:compiler=self.compiler
                result=compiler([entry['document']],entry['book'],progress=progress,checkpoint=checkpoint,background=True)
                checkpoint()
                with self.condition:entry.update(state='ready',stage='Prepared for faster export',done=entry['total'])
                if result:self.persist_ready(key,entry,result[2])
                with self.condition:
                    entry.pop('document',None);entry.pop('book',None)
                time.sleep(.05)
            except Superseded:
                with self.condition:
                    if self.entries.get(key) is entry:entry.update(state='queued' if self.enabled else 'paused',due=time.monotonic()+self.delay)
            except Exception as error:
                with self.condition:
                    if self.entries.get(key) is entry:entry.update(state='attention',stage=str(error)[:240] or 'Export will check this puzzle')

    def close(self):
        with self.condition:self.closed=True;self.condition.notify_all()
        if self.worker:self.worker.join(timeout=2)

PREPARATION=Preparation()

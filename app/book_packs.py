"""Portable compiled book packs and a persistent, recipient-owned ID registry.

Packs never contain shared catalogues, code patches or sender-assigned save slots.
The local compiler combines them into one revision-checked game installation.
"""
import copy, hashlib, json, pathlib, struct, sys, textwrap, uuid, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from msbt import MessageFile
from puzzle_format import Puzzle
from build_block_tests import string

FORMAT = 'voxel-studio-play-pack-1'
TITLE = '0004000000187E00'
MAX_BOOKS = 4  # Current executable-padding budget; expand only with a new verified patch.
MAX_PUZZLES = 210
FIRST_SAVE, SAVE_LIMIT = 3000, 3840
MAX_BYTES = 256 * 1024 * 1024
LUMA_READY = False  # LayeredFS currently chooses the same text padding as our code.


def identity(value):
    try:
        result = uuid.UUID(value).hex
    except (ValueError, TypeError, AttributeError):
        raise ValueError('A pack or puzzle has an invalid permanent ID.')
    if value != result:
        raise ValueError('Pack IDs must use lowercase UUID hex.')
    return result


def asset_name(value):
    if not isinstance(value, str) or '\\' in value or ':' in value:
        raise ValueError('Invalid asset path.')
    p = pathlib.PurePosixPath(value)
    if not value.startswith('assets/') or '..' in p.parts or str(p) != value:
        raise ValueError('Assets must stay inside the pack assets folder.')
    return value


def text(value, maximum, label):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or '\0' in value:
        raise ValueError(f'Invalid {label}.')
    return value


def validate(manifest, assets):
    if not isinstance(manifest,dict):raise ValueError('Invalid pack index.')
    if manifest.get('format') != FORMAT or manifest.get('title_id') != TITLE:
        raise ValueError('Choose a European Picross 3D: Round 2 play pack.')
    identity(manifest.get('id')); text(manifest.get('name'), 24, 'book name')
    revision = manifest.get('revision')
    if type(revision) is not int or revision < 1:
        raise ValueError('Invalid pack revision.')
    puzzles = manifest.get('puzzles')
    if not isinstance(puzzles, list) or not 1 <= len(puzzles) <= MAX_PUZZLES:
        raise ValueError('A play pack needs 1 to 210 puzzles.')
    seen = set(); used = set()
    def require(path, suffix):
        path = asset_name(path)
        if not path.endswith(suffix) or path not in assets:
            raise ValueError('A pack is missing a required asset.')
        used.add(path)
        return assets[path]
    require(manifest.get('cover'), '.bch'); require(manifest.get('icon'), '.ctpk')
    for puzzle in puzzles:
        if not isinstance(puzzle,dict):raise ValueError('Invalid puzzle entry.')
        ident = identity(puzzle.get('id'))
        if ident in seen: raise ValueError('A pack repeats a puzzle ID.')
        seen.add(ident); text(puzzle.get('name'), 28, 'puzzle name')
        description = puzzle.get('description', '')
        if not isinstance(description, str) or len(description) > 220 or '\0' in description:
            raise ValueError('Invalid puzzle description.')
        dims = puzzle.get('dimensions')
        if not isinstance(dims, list) or len(dims) != 3 or any(type(n) is not int or not 1 <= n <= 10 for n in dims):
            raise ValueError('Invalid puzzle dimensions.')
        targets = puzzle.get('time_targets')
        if not isinstance(targets, list) or len(targets) != 3 or any(type(n) is not int or not 1 <= n <= 86400 for n in targets):
            raise ValueError('Invalid scoring targets.')
        qpp = Puzzle.read(require(puzzle.get('puzzle'), '.qpp'))
        if list(qpp.dimensions) != dims: raise ValueError('Puzzle dimensions do not match its metadata.')
        require(puzzle.get('model'), '.bch'); require(puzzle.get('thumbnail'), '.ctpk')
    if used != set(assets): raise ValueError('The pack contains unexpected assets.')
    records = manifest.get('files')
    if not isinstance(records, dict) or set(records) != used:
        raise ValueError('The asset index does not match the pack.')
    for name, raw in assets.items():
        record = records[name]
        if record != {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}:
            raise ValueError('A pack asset is damaged or its checksum is incorrect.')
    return manifest


def write_pack(path, manifest, assets):
    manifest = copy.deepcopy(manifest)
    manifest.update(format=FORMAT, title_id=TITLE)
    manifest['files'] = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in sorted(assets.items())}
    validate(manifest, assets)
    if sum(map(len, assets.values())) > MAX_BYTES: raise ValueError('The pack exceeds 256 MB.')
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('pack.json', json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode('utf-8'))
            for name, raw in sorted(assets.items()): archive.writestr(name, raw)
        temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)
    return manifest


def read_pack(path):
    with pathlib.Path(path).open('rb') as source:
        if source.read(8)==b'VXBOOK01':
            from native_book import read_book
            return read_book(path)
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist(); names = [entry.filename for entry in entries]
            if len(entries) > 2 + MAX_PUZZLES * 3 + 1 or len(names) != len(set(names)):
                raise ValueError('A pack contains duplicate or too many files.')
            if sum(entry.file_size for entry in entries) > MAX_BYTES:
                raise ValueError('The pack exceeds 256 MB.')
            for entry in entries:
                if entry.filename != 'pack.json': asset_name(entry.filename)
                if entry.flag_bits & 1 or entry.is_dir(): raise ValueError('Unsupported pack entry.')
            info = archive.getinfo('pack.json')
            if info.file_size > 2_000_000: raise ValueError('The pack index is too large.')
            manifest = json.loads(archive.read(info).decode('utf-8'))
            assets = {name: archive.read(name) for name in names if name != 'pack.json'}
    except (zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('The play pack is damaged or incomplete.') from error
    validate(manifest, assets)
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'manifest': manifest, 'assets': assets, 'digest': digest, 'path': str(path)}


def scan(folder):
    selected = {}
    for path in sorted(p for p in pathlib.Path(folder).iterdir() if p.is_file() and p.suffix.lower() in ('.pictobook','.pictopack','.voxpack')):
        pack = read_pack(path); m = pack['manifest']; old = selected.get(m['id'])
        if old:
            om = old['manifest']
            if om['revision'] == m['revision'] and old['digest'] != pack['digest']:
                raise ValueError('Two different copies claim the same pack revision: ' + m['name'])
            if om['revision'] >= m['revision']: continue
        selected[m['id']] = pack
    if len(selected) > MAX_BOOKS: raise ValueError('This experimental loader supports up to four book packs at once.')
    return list(selected.values())


def allocate(packs, registry=None):
    registry = copy.deepcopy(registry or {'format': 'voxel-studio-pack-registry-1', 'packs': {}, 'next_slot': FIRST_SAVE})
    if registry.get('format') != 'voxel-studio-pack-registry-1': raise ValueError('Unknown local pack registry.')
    used = set()
    for book in registry['packs'].values():
        for row in book['puzzles'].values():
            slot = row['save_index']
            if not FIRST_SAVE <= slot < SAVE_LIMIT or slot in used or row['game_id'] != 62000 + slot - FIRST_SAVE:
                raise ValueError('The local progress registry is inconsistent.')
            used.add(slot)
    next_slot = registry['next_slot']
    if next_slot < max(used, default=FIRST_SAVE - 1) + 1: raise ValueError('The local progress registry counter is invalid.')
    # Migrate existing registries from their original first-seen insertion order.
    order=registry.setdefault('book_order',list(registry['packs']))
    if len(order)!=len(set(order)):raise ValueError('The saved book order is inconsistent.')
    result = []
    for pack in packs:
        manifest = pack['manifest']; old = registry['packs'].get(manifest['id'])
        if manifest['id'] not in order:order.append(manifest['id'])
        if old and manifest['revision'] < old['revision']: raise ValueError('An older pack would replace a newer installed version: ' + manifest['name'])
        if old and manifest['revision'] == old['revision'] and pack['digest'] != old['digest']:
            raise ValueError('Changed content needs a newer pack revision: ' + manifest['name'])
        book = registry['packs'].setdefault(manifest['id'], {'puzzles': {}})
        book.update(revision=manifest['revision'], digest=pack['digest'], name=manifest['name'])
        assigned = []
        for puzzle in manifest['puzzles']:
            key = puzzle['id']; qpp = Puzzle.read(pack['assets'][puzzle['puzzle']])
            geometry_hash = hashlib.sha256(json.dumps([qpp.dimensions,sorted(qpp.voxels)]).encode()).hexdigest()
            prior = book['puzzles'].get(key)
            if prior and prior['geometry'] != geometry_hash:
                raise ValueError('A changed puzzle needs a new permanent puzzle ID: ' + puzzle['name'])
            if prior is None:
                if next_slot >= SAVE_LIMIT: raise ValueError('The reserved progress bank is full. Existing progress slots are never reused.')
                prior = {'save_index': next_slot, 'game_id': 62000 + next_slot - FIRST_SAVE, 'geometry': geometry_hash}
                book['puzzles'][key] = prior; next_slot += 1
            assigned.append(dict(puzzle, **prior))
        result.append(dict(pack, assigned=assigned))
    registry['next_slot'] = next_slot
    result.sort(key=lambda pack:order.index(pack['manifest']['id']))
    return result, registry


def compile_catalog(packs, destination, registry=None, source=None):
    """Build entirely in a new staging folder; never reads or edits SAVEDATA."""
    if not packs or len(packs) > MAX_BOOKS: raise ValueError('Choose one to four play packs.')
    if len({p['manifest']['id'] for p in packs})!=len(packs):raise ValueError('A book pack was selected twice.')
    packs, registry = allocate(packs, registry)
    source = pathlib.Path(source or ROOT / 'work/romfs'); destination = pathlib.Path(destination)
    if destination.exists(): raise ValueError('Choose a new staging folder for the combined catalogue.')
    destination.mkdir(parents=True); romfs = destination / 'romfs'; files = []
    def put(name, raw):
        path = romfs / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw); files.append(name)
    bms = (source / 'master/default.bms').read_bytes(); count = struct.unpack_from('<H', bms, 8)[0]
    if count != 57: raise ValueError('Unexpected original book catalogue.')
    secondary = struct.unpack_from('<I', bms, 20)[0]
    originals = [bytearray(bms[28+i*404:28+(i+1)*404]) for i in range(count)]
    for record in originals:
        pointer = struct.unpack_from('<I', record, 396)[0]
        if pointer: struct.pack_into('<I', record, 396, pointer + len(packs)*404)
    body = bytearray(bms[secondary:]); new_books = []; rows = []; cover_keys = []
    layout = struct.unpack_from('<I', bms, 28+39*404+396)[0]
    pms = (source / 'master/default.pms').read_bytes(); pcount = struct.unpack_from('<H', pms, 8)[0]
    psecondary = struct.unpack_from('<I', pms, 20)[0]; pextra = []
    template = pms[28+608*404:28+609*404]
    for book_index, pack in enumerate(packs):
        m = pack['manifest']; native_book = 57 + book_index; key = str(native_book); cover_keys.append(key)
        book = bytearray(originals[3]); struct.pack_into('<HH', book, 0, native_book, native_book)
        book[4:7] = bytes((len(pack['assigned']), 0, 0)); book[28:44] = bytes(16)
        string(book, 44, 32, f'PACK_BOOKNO_{key}'); string(book, 76, 32, f'PACK_BOOKNAME_{key}')
        struct.pack_into('<I', book, 396, secondary+len(packs)*404+len(body))
        cover = f'texture/book/cover/Pack{key}.bch'; icon = f'texture/book/icon/Pack{key}.ctpk'
        string(book, 140, 128, 'r:/'+cover, True); string(book, 268, 128, 'r:/'+icon, True)
        put(cover, pack['assets'][m['cover']]); put(icon, pack['assets'][m['icon']])
        for index, puzzle in enumerate(pack['assigned']):
            ident = puzzle['game_id']; base = f'pack_{ident}'
            entry = bytearray(bms[layout+(index%15)*244:layout+(index%15+1)*244])
            struct.pack_into('<HHI', entry, 0, index, native_book, ident); entry[212:] = bytes(32); entry[213] = 4
            struct.pack_into('<H', entry, 214, puzzle['save_index'])
            string(entry, 20, 32, f'PUZZLE_NO_{ident}'); string(entry, 52, 32, f'PUZZLE_NAME_{ident}')
            string(entry, 84, 128, f'r:/texture/thumbnail/{base}.ctpk', True); body += entry
            record = bytearray(template); struct.pack_into('<I', record, 0, ident)
            string(record, 4, 32, f'PUZZLE_NO_{ident}'); string(record, 36, 32, f'PUZZLE_NAME_{ident}')
            string(record, 68, 128, f'r:/puzzle/{base}.qpp', True)
            string(record, 196, 128, f'r:/completemodel/cm_{base}.bch', True); record[328:331] = bytes(puzzle['dimensions'])
            for offset, target in zip((368,376,400), puzzle['time_targets']): struct.pack_into('<I', record, offset, target)
            pextra.append((ident, record)); rows.append((puzzle, index))
            qpp = bytearray(pack['assets'][puzzle['puzzle']]); struct.pack_into('<I', qpp, 4, ident)
            put(f'puzzle/{base}.qpp', bytes(qpp)); put(f'completemodel/cm_{base}.bch', pack['assets'][puzzle['model']])
            put(f'texture/thumbnail/{base}.ctpk', pack['assets'][puzzle['thumbnail']])
        new_books.append(book)
    header = bytearray(bms[:28]); struct.pack_into('<H', header, 8, count+len(packs)); struct.pack_into('<I', header, 20, secondary+len(packs)*404)
    put('master/default.bms', bytes(header)+b''.join(originals+new_books)+body)
    header = bytearray(pms[:28]); struct.pack_into('<H', header, 8, pcount+len(rows)); struct.pack_into('<I', header, 20, psecondary+len(rows)*404)
    put('master/default.pms', bytes(header)+pms[28:psecondary]+b''.join(r for _,r in sorted(pextra))+pms[psecondary:])
    for language in ('en','fr','de','es','it'):
        for resource in ('BookNo','BookName','PuzzleNo','PuzzleName','Trivia'):
            messages = MessageFile((source/f'text/{language}/{resource}.msbt').read_bytes())
            if resource.startswith('Book'):
                for index, pack in enumerate(packs):
                    label = ('PACK_BOOKNO_' if resource == 'BookNo' else 'PACK_BOOKNAME_')+cover_keys[index]
                    messages.set(label, str(57+index) if resource == 'BookNo' else pack['manifest']['name'])
                if resource == 'BookNo':
                    messages.set('BOOKNO_STUDIO_PREVIOUS','L: Previous'); messages.set('BOOKNO_STUDIO_NEXT','Next: R')
            else:
                for puzzle,index in rows:
                    value = f'C{index+1:03}' if resource == 'PuzzleNo' else puzzle['name'] if resource == 'PuzzleName' else '\n'.join(textwrap.wrap(puzzle.get('description',''),27))
                    messages.set(f"PUZZLE_{'NO' if resource=='PuzzleNo' else 'NAME'}_{puzzle['game_id']}", value)
            put(f'text/{language}/{resource}.msbt', messages.write())
    from build_paging_patch import build
    from book_page_art import build as artwork
    manifest = {'books': list(range(57,57+len(packs))), 'save_indices': sorted(p['save_index'] for p,_ in rows)}
    ips, _, patch = build(dict(manifest, pack_bank=True))
    (destination/'code.ips').write_bytes(ips); art, _ = artwork(); put('layout/Body_PuzzleSelect.arc', art)
    manifest.update(files=sorted(files), packs=[{'id':p['manifest']['id'],'name':p['manifest']['name'],'revision':p['manifest']['revision'],'puzzles':len(p['assigned'])} for p in packs], patch=patch,
                    external_save_edit=False, progress_registry=registry)
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest, registry

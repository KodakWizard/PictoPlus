"""Flat, seekable book container for the SD-card loader (experimental v1).

The editable source is optional; native assets can be read without a ZIP/JSON
runtime. All offsets are absolute and every payload has a CRC32.
"""
import hashlib
import json
import pathlib
import struct
import uuid
import zlib

MAGIC = b'VXBOOK01'
HEADER = 160
RECORD = 640
LIMIT = 256 * 1024 * 1024


def _text(value, units):
    raw = value.encode('utf-16-le')
    if b'\0\0' == raw[:2] or '\0' in value or len(raw) > units * 2:
        raise ValueError('Book text exceeds its game limit.')
    return raw.ljust(units * 2, b'\0')


def write_book(path, pack, editable=None, installed_game=False):
    from book_packs import validate
    m, assets = pack['manifest'], pack['assets']
    validate(m, assets)
    data = bytearray(HEADER + RECORD * len(m['puzzles']))
    data[:8] = MAGIC
    struct.pack_into('<II16sIHHII', data, 8, 1, HEADER,
                     uuid.UUID(m['id']).bytes, m['revision'], len(m['puzzles']),
                     0, HEADER, RECORD)
    data[48:96] = _text(m['name'], 24)
    if installed_game:
        from game_asset_edits import encode as encode_asset
        encoded={}
        def encode(raw,kind):
            key=(kind,hashlib.sha256(raw).digest())
            if key not in encoded:encoded[key]=encode_asset(raw,kind)
            return encoded[key]
        struct.pack_into('<H',data,38,1)

    def payload(at, raw):
        data.extend(b'\0' * (-len(data) % 16))
        struct.pack_into('<III', data, at, len(data), len(raw), zlib.crc32(raw))
        data.extend(raw)
        if len(data) > LIMIT:
            raise ValueError('Book exceeds 256 MB.')

    payload(96, encode(assets[m['cover']],'cover') if installed_game else assets[m['cover']])
    payload(108, encode(assets[m['icon']],'icon') if installed_game else assets[m['icon']])
    if editable is not None:
        payload(120, json.dumps(editable, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    for i, p in enumerate(m['puzzles']):
        at = HEADER + i * RECORD
        data[at:at+16] = uuid.UUID(p['id']).bytes
        data[at+16:at+19] = bytes(p['dimensions'])
        struct.pack_into('<III', data, at+20, *p['time_targets'])
        data[at+32:at+88] = _text(p['name'], 28)
        data[at+88:at+528] = _text(p.get('description', ''), 220)
        for pos, key in ((528, 'puzzle'), (540, 'model'), (552, 'thumbnail')):
            payload(at+pos, encode(assets[p[key]],key) if installed_game else assets[p[key]])
        struct.pack_into('<I', data, at+564, zlib.crc32(data[at:at+RECORD]))
    struct.pack_into('<I', data, 132, len(data))
    if installed_game:struct.pack_into('<I',data,140,zlib.crc32(data[HEADER:]))
    struct.pack_into('<I', data, 136, zlib.crc32(data[:HEADER]))
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read_book(path):
    from book_packs import FORMAT, TITLE, validate
    path = pathlib.Path(path)
    if not HEADER <= path.stat().st_size <= LIMIT:
        raise ValueError('Invalid book length.')
    raw = path.read_bytes()
    if raw[:8] != MAGIC:
        raise ValueError('Not a native book.')
    version, header, ident, revision, count, flags, table, record = struct.unpack_from('<II16sIHHII', raw, 8)
    if (version, header, table, record) != (1, HEADER, HEADER, RECORD) or flags not in (0,1) or not 1 <= count <= 210:
        raise ValueError('Unsupported book header.')
    if struct.unpack_from('<I', raw, 132)[0] != len(raw) or HEADER + count * RECORD > len(raw):
        raise ValueError('Incomplete book.')

    def crc(at, size, field):
        block = bytearray(raw[at:at+size])
        expected = struct.unpack_from('<I', block, field)[0]
        struct.pack_into('<I', block, field, 0)
        if zlib.crc32(block) != expected:
            raise ValueError('Book metadata checksum failed.')

    crc(0, HEADER, 136)
    spans = []
    def payload(at, optional=False):
        offset, size, checksum = struct.unpack_from('<III', raw, at)
        if optional and (offset, size, checksum) == (0, 0, 0):
            return None
        if offset % 16 or offset < HEADER + count * RECORD or not size or offset + size > len(raw):
            raise ValueError('Book asset points outside its data.')
        if any(offset < end and start < offset + size for start, end in spans):
            raise ValueError('Book assets overlap.')
        spans.append((offset, offset + size))
        blob = raw[offset:offset+size]
        if zlib.crc32(blob) != checksum:
            raise ValueError('Book asset checksum failed.')
        return blob

    def text(at, size):
        return raw[at:at+size].decode('utf-16-le').rstrip('\0')

    def asset(at):
        data=payload(at)
        if flags:
            from game_asset_edits import decode
            return decode(data)
        return data
    assets = {'assets/cover.bch': asset(96), 'assets/icon.ctpk': asset(108)}
    source = payload(120, True)
    m = dict(format=FORMAT, title_id=TITLE, id=uuid.UUID(bytes=ident).hex,
             revision=revision, name=text(48, 48), cover='assets/cover.bch',
             icon='assets/icon.ctpk', puzzles=[])
    for i in range(count):
        at = HEADER + i * RECORD
        crc(at, RECORD, 564)
        p = dict(id=uuid.UUID(bytes=raw[at:at+16]).hex, name=text(at+32, 56),
                 description=text(at+88, 440), dimensions=list(raw[at+16:at+19]),
                 time_targets=list(struct.unpack_from('<III', raw, at+20)))
        for pos, key, ext in ((528, 'puzzle', 'qpp'), (540, 'model', 'bch'), (552, 'thumbnail', 'ctpk')):
            name = f'assets/{i:03d}.{ext}'
            assets[name] = asset(at+pos)
            p[key] = name
        m['puzzles'].append(p)
    m['files'] = {name: {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()} for name, blob in assets.items()}
    validate(m, assets)
    return dict(manifest=m, assets=assets, editable=json.loads(source) if source is not None else None,
                digest=hashlib.sha256(raw).hexdigest(), path=str(path))

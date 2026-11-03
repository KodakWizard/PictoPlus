"""Experimental QPP v5 reader. Unknown header fields are preserved verbatim."""
from dataclasses import dataclass
import struct

@dataclass
class Puzzle:
    header: bytes
    dimensions: tuple
    voxels: list
    masks: list

    @classmethod
    def read(cls, data):
        assert len(data) >= 592 and data[0] == 5
        dims = tuple(data[1:4])
        assert all(1 <= n <= 10 for n in dims)
        count = struct.unpack_from('<I', data, 8)[0]
        offsets = struct.unpack_from('<31I', data, 0x1d4)
        assert offsets[0] == 592
        end = 592 + count*4
        assert offsets[1] == end
        voxels = [tuple(data[i:i+4]) for i in range(592, end, 4)]
        seen = set()
        for shape, xy, zcolour, flags in voxels:
            xyz = (xy & 15, xy >> 4, zcolour & 15)
            assert all(v < n for v, n in zip(xyz, dims))
            assert xyz not in seen
            seen.add(xyz)
            assert shape < 218
        sizes = (dims[0]*dims[1], dims[0]*dims[2], dims[1]*dims[2])
        modes = data[0x91]
        assert modes in (1, 5)
        masks = []
        for i in range(modes*3):
            assert offsets[i+1] == end
            mask = data[end:end+sizes[i%3]]
            assert len(mask) == sizes[i%3] and set(mask) <= {0,1}
            masks.append(mask)
            end += len(mask)
        assert end == len(data)
        assert not any(offsets[1+modes*3:])
        return cls(data[:592], dims, voxels, masks)

    def write(self):
        h = bytearray(self.header)
        h[1:4] = bytes(self.dimensions)
        struct.pack_into('<I', h, 8, len(self.voxels))
        offsets = [592]
        end = 592 + 4*len(self.voxels)
        for mask in self.masks:
            offsets.append(end)
            end += len(mask)
        offsets += [0]*(31-len(offsets))
        struct.pack_into('<31I', h, 0x1d4, *offsets)
        return bytes(h) + b''.join(bytes(v) for v in self.voxels) + b''.join(self.masks)

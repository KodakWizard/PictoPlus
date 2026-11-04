"""Check compiler grid encoding without any installed game data."""
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import core
from puzzle_format import Puzzle


class PuzzleGridTests(unittest.TestCase):
    def test_compiles_full_extent_on_every_axis(self):
        template = bytearray(592)
        template[0] = 5
        template[0x91] = 5
        original = Puzzle(bytes(template), (3, 5, 3), [],
                          [bytes(n) for n in (15, 9, 15)] * 5).write()
        for dims in [(1, 1, 1), (4, 5, 6), (9, 8, 9), (10, 10, 10),
                     (10, 1, 2), (2, 10, 1), (1, 2, 10)]:
            with self.subTest(dims=dims), patch.object(Path, 'read_bytes', return_value=original):
                x, y, z = dims
                cells = [{'xyz': [i, j, k], 'shape': 0}
                         for i in range(x) for j in range(y) for k in range(z)]
                puzzle = Puzzle.read(core.qpp({'dimensions': dims, 'cells': cells}).write())
                self.assertEqual(puzzle.dimensions, dims)
                self.assertEqual([(xy & 15, xy >> 4, zc & 15) for _, xy, zc, _ in puzzle.voxels],
                                 [tuple(cell['xyz']) for cell in cells])
                self.assertEqual(list(map(len, puzzle.masks)), [x*y, x*z, y*z] * 5)
                for mode in range(5):
                    self.assertEqual(struct.unpack_from('<3H', puzzle.header, 0x96 + 32*mode),
                                     (x*y, x*z, y*z))


if __name__ == '__main__':
    unittest.main()

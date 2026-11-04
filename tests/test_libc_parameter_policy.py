#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import struct
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from libc_parameter_policy import bind_heap


def image():
    r = bytearray(4096)
    r[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<Q', r, 32, 64)
    struct.pack_into('<HH', r, 54, 56, 2)
    struct.pack_into('<IIQQQQQQ', r, 64, 1, 4, 0, 0, 0, len(r), len(r), 16384)
    struct.pack_into('<IIQQQQQQ', r, 120, 0x61000001, 4, 512, 512, 0, 0x60, 0x60, 8)
    struct.pack_into('<Q', r, 512, 0x60)
    r[520:524] = b'ORBI'
    at = 512 + 0x60
    for size, count in zip((0xa8, 0x38, 0x10, 0x78, 0xc0, 0x38), (0x10000000e, 0, 0, 2, 3, 1)):
        struct.pack_into('<QQ', r, at, size, count)
        at += size
    struct.pack_into('<QI', r, at, 0xffffffffffffffff, 1)
    for i, (target, value) in enumerate(((512 + 0x38, 608), (608 + 0x10, 608 + 0x260), (608 + 0x20, 608 + 0x268))):
        struct.pack_into('<QQQ', r, 2048 + i * 24, target, 8, value)
    return r


class ParameterTests(unittest.TestCase):
    def test_only_heap_field_changes(self):
        r = image()
        out, proof = bind_heap(r, 8 << 20)
        at = proof['heap_size_file_offset']
        self.assertEqual(out[:at], r[:at])
        self.assertEqual(out[at + 8:], r[at + 8:])
        self.assertEqual(struct.unpack_from('<Q', out, at)[0], 8 << 20)

    def test_other_heap_bound_refused(self):
        with self.assertRaises(ValueError):
            bind_heap(image(), 1 << 20)

    def test_wrong_process_magic_refused(self):
        r = image(); r[520] = 0
        with self.assertRaises(ValueError): bind_heap(r, 8 << 20)

    def test_wrong_libc_layout_refused(self):
        r = image(); r[608] = 0
        with self.assertRaises(ValueError): bind_heap(r, 8 << 20)

    def test_missing_relative_pointer_refused(self):
        r = image(); r[2048:2072] = bytes(24)
        with self.assertRaises(ValueError): bind_heap(r, 8 << 20)

    def test_duplicate_relative_pointer_refused(self):
        r = image(); r[2300:2324] = r[2048:2072]
        with self.assertRaises(ValueError): bind_heap(r, 8 << 20)

    def test_outside_load_refused(self):
        r = image(); struct.pack_into('<Q', r, 64 + 32, 768)
        with self.assertRaises(ValueError): bind_heap(r, 8 << 20)

    def test_already_modified_heap_refused(self):
        r = image(); struct.pack_into('<Q', r, 608 + 0x260, 16 << 20)
        with self.assertRaises(ValueError): bind_heap(r, 8 << 20)


if __name__ == '__main__': unittest.main()

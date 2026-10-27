#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from kernel_zone_snapshot import FIELDS,MAX_NODE,decode_variable_dump
def dump(data):
    return b'\n'.join(f'{i:08x}  '.encode()+b' '.join(f'{v:02x}'.encode()for v in data[i:i+16])+b'  |...|'for i in range(0,len(data),16))+b'\n$ '
class Zones(unittest.TestCase):
    def test_exact_payload(self):
        raw=b'ITEM SIZE LIMIT USED FREE REQUESTS FAILURES SLEEPS\nmbuf: 256, 0, 10, 4, 20, 0, 0\n\0'
        self.assertEqual(decode_variable_dump(dump(raw)),raw)
    def test_unavailable_is_explicit(self):self.assertIsNone(decode_variable_dump(b'sysctl: unknown oid vm.zone\n$ '))
    def test_invalid_or_unbounded(self):
        for raw in(b'',b'$ ',b'00000010  01  |.|\n',b'00000000  01 ZZ  |.|\n',dump(bytes(MAX_NODE+1))):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):decode_variable_dump(raw)
    def test_fixed_read_only_scope(self):
        self.assertEqual(len(FIELDS),9)
        self.assertEqual(FIELDS[0],('boot_before','kern.boottime',16));self.assertEqual(FIELDS[-1],('boot_after','kern.boottime',16))
        self.assertTrue(all(name and'='not in name and' 'not in name for _,name,_ in FIELDS))
if __name__=='__main__':unittest.main()

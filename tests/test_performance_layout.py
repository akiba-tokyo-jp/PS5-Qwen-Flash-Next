# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('layout',Path(__file__).resolve().parents[1]/'tools/performance_layout.py')
layout=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(layout)


class LayoutTests(unittest.TestCase):
    def test_boundary_bytes_are_preserved(self):
        self.assertEqual(layout.split_extent(3,15,10,16),[((3,0),15,1),((3,1),0,9)])
        self.assertEqual(layout.split_extent(0,0,32,16),[((0,0),0,16),((0,1),0,16)])
        for args in ((-1,0,1,2),(0,-1,1,2),(0,0,0,2),(0,0,1,0)):
            with self.assertRaises(ValueError):layout.split_extent(*args)

    def test_smaller_chunks_increase_calls_without_changing_bytes(self):
        m=1<<20
        rows=[dict(files=[0,0],aligned_offsets=[63*m,100*m],requested_bytes=[3*m,3*m])]
        a=layout.screen_trace(rows,[200*m],128*m)
        b=layout.screen_trace(rows,[200*m],64*m)
        self.assertEqual(a['sampled_returned_bytes'],b['sampled_returned_bytes'])
        self.assertEqual(a['sampled_physical_calls'],2)
        self.assertEqual(b['sampled_physical_calls'],3)
        self.assertEqual(b['sampled_parallel_geometry_eligible_pairs'],0)
        rows[0]['aligned_offsets'][1]=199*m
        with self.assertRaises(ValueError):layout.screen_trace(rows,[200*m],64*m)

    def test_truncated_or_unbounded_headers_refuse(self):
        import struct
        root=Path(__file__).resolve().parents[1]/'.test-tmp'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            p=Path(folder)/'original.gguf'
            for data in (b'GGUF',b'GGUF'+struct.pack('<IQQ',3,4097,0)):
                p.write_bytes(data)
                with self.assertRaises(ValueError):layout.read_header(p)


if __name__=='__main__':unittest.main()

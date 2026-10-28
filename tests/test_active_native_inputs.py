# SPDX-License-Identifier: MIT
"""Keep current link commitments while excluding unused parent images."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from active_native_inputs import active_link_inputs

class ActiveLinkTests(unittest.TestCase):
    def fixture(self):
        def row(path):return dict(path=path,bytes=10,sha256='a'*64)
        return dict(artifact=row('/work/current/app.elf'),link_command=['ld','/work/current/main.o','/work/driver.a','-o','/work/current/app.elf'],
            inputs_before=[row('/work/unused-parent/app.elf'),row('/work/current/main.o'),row('/work/current/main.cpp'),row('/work/driver.a')])
    def test_every_real_link_input_and_current_source_are_retained(self):
        paths={r['path']for r in active_link_inputs(self.fixture())}
        self.assertEqual(paths,{'/work/current/app.elf','/work/current/main.o','/work/current/main.cpp','/work/driver.a'})
    def test_missing_archive_or_ambiguous_digest_is_refused(self):
        data=self.fixture();data['inputs_before'].pop()
        with self.assertRaises(ValueError):active_link_inputs(data)
        data=self.fixture();data['inputs_before'].append(dict(data['inputs_before'][1],sha256='b'*64))
        with self.assertRaises(ValueError):active_link_inputs(data)

if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: MIT
"""Reject stale native sources and archives that discard compatibility members."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_driver as native

def write_archive(path,rows):
    with path.open('wb') as stream:
        stream.write(b'!<arch>\n')
        for name,body in rows.items():
            encoded=name.encode();data=encoded+body
            header=('#1/'+str(len(encoded))).ljust(16)+'0'.ljust(12)+'0'.ljust(6)*2
            header+='100644'.ljust(8)+str(len(data)).ljust(10)+'`\n'
            stream.write(header.encode()+data+(b'\n'if len(data)%2 else b''))

class NativePlatformInputs(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);directory=self.root/'native/driver';directory.mkdir(parents=True)
        self.source=directory/'platform.c';self.source.write_text('/* fixture source */\n')
        self.header=self.root/'public-header.h';self.header.write_text('/* fixture public ABI */\n')
        self.rows={native.NATIVE_PLATFORM[0]:b'\x7fELForiginal'}
        self.rows.update({'other-%d.o'%n:b'\x7fELF'+str(n).encode()for n in range(703)})
        self.donor=self.root/'donor.a';write_archive(self.donor,self.rows)
        self.final_rows={**self.rows,native.NATIVE_PLATFORM[0]:b'\x7fELFqwen'}
        self.archive=self.root/'native.a';write_archive(self.archive,self.final_rows)
        (self.root/native.NATIVE_PLATFORM[0]).write_bytes(self.final_rows[native.NATIVE_PLATFORM[0]])
        self.selected={'source_revision':'source-pin','profile':'cumulative-idle'}
        self.lock={'selected_composition_sha256':native.sha(self.donor)}
        def record(path):return {'path':str(path),'sha256':native.sha(path)}
        self.value={'schema':'ps5-qwen-native-platform-build-v1','selected_driver':self.selected,
            'composition_archive_sha256':self.lock['selected_composition_sha256'],
            'modified_members':[list(native.NATIVE_PLATFORM)],'unmodified_members_preserved':703,
            'other_application_log_fallback':False,'deployment_allowed':False,'console_access':False,
            'GPU_executed':False,'persistent_caches_disabled_required':True,'CI':False,
            'native_source':[record(self.source)],'native_headers':[record(self.header)],
            'inputs_before_after':[record(self.donor)],'archive_path':str(self.archive),'archive_sha256':native.sha(self.archive)}
        self.manifest=self.root/'manifest.json';self.save()
        self.addCleanup(patch.stopall);patch.object(native,'ROOT',self.root).start()

    def save(self):self.manifest.write_text(json.dumps(self.value))
    def validate(self):return native.validate_native_platform(self.manifest,self.selected,self.lock)

    def test_exact_native_archive_is_separate_from_console_qualification(self):
        result=self.validate();self.assertEqual(result['archive_sha256'],native.sha(self.archive))
        self.assertFalse(result['console_qualified'])

    def test_same_count_with_different_compatibility_bytes_is_rejected(self):
        changed={**self.final_rows,'other-3.o':b'\x7fELFwrong-compatible-object'}
        write_archive(self.archive,changed);self.value['archive_sha256']=native.sha(self.archive);self.save()
        with self.assertRaisesRegex(ValueError,'unrelated member'):self.validate()

    def test_changed_source_and_header_are_rejected(self):
        for path in [self.source,self.header]:
            original=path.read_bytes();path.write_bytes(b'changed')
            with self.subTest(path=path.name),self.assertRaisesRegex(ValueError,'changed'):self.validate()
            path.write_bytes(original)

    def test_wrong_profile_cache_or_permission_is_rejected(self):
        original=copy.deepcopy(self.value)
        for key,value in [('selected_driver',{}),('deployment_allowed',True),('persistent_caches_disabled_required',False),
                          ('modified_members',[]),('unmodified_members_preserved',704)]:
            self.value={**original,key:value};self.save()
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'contract'):self.validate()

if __name__=='__main__':unittest.main()

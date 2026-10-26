# SPDX-License-Identifier: MIT
"""The fixed status observer must never resubmit an ambiguous CPU operation."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_cpu_status_once as once

class Transport:
    def __init__(self,wrong_nonce=False):
        self.posts=0;self.status_reads=0;self.journal_reads=0;self.wrong_nonce=wrong_nonce
    def allowed(self,_):pass
    def absent(self,_):pass
    def stage_new(self,*_):return {'path':'/data/ai/moss-test.elf','bytes':1,'sha256':'b'*64}
    def save(self,path,value):Path(path).write_text(json.dumps(value))
    def web(self,path,*_):
        if path.startswith('/elfldr?'):
            self.posts+=1;raise RuntimeError('Ambiguous acknowledgement')
        if path.endswith('.status'):
            self.status_reads+=1;nonce=('c'if self.wrong_nonce else'a')*32
            line='PROGRESS nonce='+nonce+' last_completed_files='+str(self.status_reads-1)+'\n'
            if self.status_reads==2:line+='END success=1 nonce='+nonce+'\n'
            return line.encode().ljust(511,b' ')+b'\n'
        self.journal_reads+=1;return b'BEGIN\nEND success=1\n'

class StatusOnceTests(unittest.TestCase):
    def temporary(self):
        root=Path(__file__).resolve().parents[1]/'.test-tmp'
        root.mkdir(exist_ok=True)
        folder=tempfile.TemporaryDirectory(dir=root)
        self.assertTrue(Path(folder.name).resolve().is_relative_to(root.resolve()))
        return folder
    def setUp(self):
        self.manifest={'nonce':'a'*32,'artifact':{'path':'local','sha256':'b'*64},
            'remote_elf':'/data/ai/moss-test.elf','remote_log':'/data/ai/moss-test.log',
            'remote_status':'/data/ai/moss-test.status','sources':[{}]}
    def test_ambiguous_acknowledgement_is_never_resubmitted(self):
        with self.temporary()as folder,patch.object(once.time,'sleep',lambda _:None):
            transport=Transport();result=once.execute(transport,self.manifest,Path(folder)/'probe',2)
            self.assertEqual(result,b'BEGIN\nEND success=1\n')
            self.assertEqual((transport.posts,transport.status_reads,transport.journal_reads),(1,2,1))
            record=json.loads((Path(folder)/'probe/execution.once.private.json').read_text())
            self.assertEqual(record['automatic_retries'],0)
    def test_wrong_status_owner_stops_without_another_submission(self):
        with self.temporary()as folder,patch.object(once.time,'sleep',lambda _:None):
            transport=Transport(wrong_nonce=True)
            with self.assertRaises(ValueError):once.execute(transport,self.manifest,Path(folder)/'probe',2)
            self.assertEqual((transport.posts,transport.journal_reads),(1,0))
    def test_existing_output_cannot_be_used_for_resubmission(self):
        with self.temporary()as folder:
            transport=Transport()
            with self.assertRaises(FileExistsError):once.execute(transport,self.manifest,folder,2)
            self.assertEqual(transport.posts,0)
    def test_timeout_must_be_finite_before_submission(self):
        with self.temporary()as folder:
            transport=Transport()
            with self.assertRaises(ValueError):once.execute(transport,self.manifest,Path(folder)/'probe',361)
            self.assertEqual(transport.posts,0)

if __name__=='__main__':unittest.main()

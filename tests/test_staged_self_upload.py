# SPDX-License-Identifier: MIT
"""Conservation and no-HTTP controls; this never contacts a console."""
import hashlib,json,sys,tempfile,types,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from staged_self_upload import upload


class UploadTests(unittest.TestCase):
    def test_integrity_boundary_and_no_HTTP(self):
        workspace=Path(__file__).resolve().parents[1];parent=(workspace/'.test-tmp').resolve()
        assert parent.is_relative_to(workspace);parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent,prefix='staged-self-')as tmp:
            assert Path(tmp).resolve().is_relative_to(parent)
            root=Path(tmp);payload=b'original-SELF'*60000;path=root/'eboot.bin';path.write_bytes(payload)
            capture=dict(path=str(path),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest());wire=bytearray();events=[]
            class FTP:
                def __enter__(self):return self
                def __exit__(self,*args):events.append('closed')
                def connect(self,*args,**kwargs):pass
                def login(self):pass
                def storbinary(self,command,source,size,callback):
                    while True:
                        block=source.read(size)
                        if not block:break
                        wire.extend(block);callback(block)
                    events.append('226');return '226 Transfer complete'
            def save(p,value):
                with p.open('x')as f:json.dump(value,f)
            lan=types.SimpleNamespace(HOST='unused',ftplib=types.SimpleNamespace(FTP=FTP),
                allowed=lambda p:None,absent=lambda p:None,save=save)
            def verify(capture,remote):
                self.assertEqual(events,['226','closed']);self.assertEqual(bytes(wire),payload)
                events.append('native');return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,
                    bytes=capture['bytes'],sha256=capture['sha256'])
            result=upload(capture,'/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-qwen-plan-1.bin',root/'out',lan,verify)
            self.assertTrue(result['completed']);self.assertEqual(events,['226','closed','native'])
            with self.assertRaises(FileExistsError):upload(capture,'/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-qwen-plan-1.bin',root/'out',lan,verify)
            self.assertEqual(events,['226','closed','native'])
            with self.assertRaises(RuntimeError):upload(capture,'/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-qwen-plan-2.bin',root/'bad-native',lan,lambda *args:{})
            self.assertFalse((root/'bad-native/complete.json').exists())
            wrong=dict(capture,sha256='0'*64)
            with self.assertRaises(ValueError):upload(wrong,'/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-qwen-plan-3.bin',root/'bad-local',lan,verify)
            self.assertFalse((root/'bad-local').exists())


if __name__=='__main__':unittest.main()

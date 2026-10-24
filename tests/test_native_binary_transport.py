# SPDX-License-Identifier: MIT
import hashlib,json,sys,tempfile,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from native_binary_transport import NativeBinaryFTP
REMOTE='/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-test.bin'

class TransportTests(unittest.TestCase):
    def setUp(self):
        root=ROOT/'.test-tmp';root.mkdir(exist_ok=True);self.tmp=tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);assert self.root.resolve().is_relative_to(root.resolve())
        self.files={};self.calls=[];self.HTTP=[];self.fault=None;self.now=0.0
        self.data=bytes(range(256))*8193
        test=self
        class FTP:
            def __init__(self):self.self2elf=True
            def connect(self,*args,**kw):test.calls.append('connect')
            def login(self):test.calls.append('login')
            def sendcmd(self,command):
                test.calls.append(command)
                if test.fault=='SELF_ack':return '226 SELF transfer mode enabled'
                self.self2elf=not self.self2elf
                return '226 SELF transfer mode disabled'
            def quit(self):
                test.calls.append('quit')
                if test.fault=='quit':raise RuntimeError('Synthetic QUIT failure')
            def close(self):test.calls.append('close')
            def retrbinary(self,command,callback,blocksize):
                test.calls.append(command)
                assert not self.self2elf,'Default SELF-to-ELF conversion must be disabled before RETR'
                if test.fault=='network':raise TimeoutError('Synthetic transport loss')
                data=test.files[command[5:]]
                if test.fault=='corrupt':data=bytes([data[0]^1])+data[1:]
                for i in range(0,len(data),blocksize):
                    if test.fault=='deadline':test.now+=31
                    callback(data[i:i+blocksize])
                return '451 incomplete'if test.fault=='reply'else'226 Complete'
            def storbinary(self,command,source,blocksize,callback):
                test.calls.append(command);test.files[command[5:]]=source.read()
                if test.fault=='upload_deadline':test.now+=31
                callback(test.files[command[5:]]);return '226 Complete'
        def web(*args):self.HTTP.append(args);return b'metadata'
        def absent(remote):
            if remote in self.files:raise FileExistsError(remote)
        self.base=types.SimpleNamespace(HOST='example.invalid',web=web,allowed=lambda _:None,absent=absent,
            stage_new=lambda *args:dict(small=True))
        self.transport=NativeBinaryFTP(self.base,self.root/'events',local_root=self.root,ftp_factory=FTP,clock=lambda:self.now)

    def test_exact_large_readback_and_evidence(self):
        self.files[REMOTE]=self.data
        self.assertEqual(self.transport.web('/fs'+REMOTE,4<<20,20),self.data);self.assertFalse(self.HTTP)
        result=json.loads(next((self.root/'events').glob('*.returned.private.json')).read_text())
        self.assertEqual(result['sha256'],hashlib.sha256(self.data).hexdigest())
        self.assertEqual(result['bytes'],len(self.data));self.assertTrue(result['caller_must_verify_exact_expected_bytes'])
        self.assertTrue(result['SELF_to_ELF_conversion_disabled'])

    def test_complete_upload_and_exact_readback(self):
        local=self.root/'self.bin';local.write_bytes(self.data)
        r=self.transport.stage_new(local,REMOTE,hashlib.sha256(self.data).hexdigest())
        self.assertTrue(r['full_raw_readback_verified']);self.assertFalse(self.HTTP)
        self.assertEqual(sum(c.startswith('STOR ')for c in self.calls),1)
        self.assertEqual(sum(c.startswith('RETR ')for c in self.calls),1)

    def test_wrong_frozen_source_never_uploaded(self):
        local=self.root/'self.bin';local.write_bytes(self.data)
        with self.assertRaises(RuntimeError):self.transport.stage_new(local,REMOTE,'a'*64)
        self.assertFalse(self.calls)

    def test_existing_partial_never_overwritten(self):
        local=self.root/'self.bin';local.write_bytes(self.data);self.files[REMOTE]=b'partial'
        with self.assertRaises(FileExistsError):self.transport.stage_new(local,REMOTE,hashlib.sha256(self.data).hexdigest())
        self.assertEqual(self.files[REMOTE],b'partial');self.assertFalse(self.calls)

    def test_corrupt_complete_readback_not_published(self):
        local=self.root/'self.bin';local.write_bytes(self.data);self.fault='corrupt'
        with self.assertRaises(RuntimeError):self.transport.stage_new(local,REMOTE,hashlib.sha256(self.data).hexdigest())
        self.assertEqual(sum(c.startswith('STOR ')for c in self.calls),1)

    def test_overflow_network_deadline_and_negative_reply_no_retry(self):
        for fault in ('overflow','network','deadline','reply'):
            with self.subTest(fault=fault):
                self.files[REMOTE]=self.data;self.calls.clear();self.fault=fault;self.now=0.0
                with self.assertRaises((RuntimeError,TimeoutError)):
                    self.transport.web('/fs'+REMOTE,(1<<20)+1 if fault=='overflow'else 4<<20,20)
                self.assertEqual(sum(c.startswith('RETR ')for c in self.calls),1);self.assertFalse(self.HTTP)

    def test_path_escape_and_command_injection_rejected(self):
        for path in ('/fs/data/other/eboot.bin','/fs'+REMOTE+'?x=1','/fs'+REMOTE.replace('eboot','eboot\r\nDELE x')):
            with self.subTest(path=path),self.assertRaises(ValueError):self.transport.web(path,4<<20,20)
        self.assertFalse(self.calls)

    def test_upload_deadline_retains_new_object_without_retry_or_publication(self):
        local=self.root/'self.bin';local.write_bytes(self.data);self.fault='upload_deadline'
        with self.assertRaises(TimeoutError):self.transport.stage_new(local,REMOTE,hashlib.sha256(self.data).hexdigest())
        self.assertIn(REMOTE,self.files)
        self.assertEqual(sum(c.startswith('STOR ')for c in self.calls),1)
        self.assertEqual(sum(c.startswith('RETR ')for c in self.calls),0)

    def test_small_management_and_helpers_unchanged(self):
        self.assertEqual(self.transport.web('/small-report',1024,3),b'metadata')
        self.assertEqual(len(self.HTTP),1);self.assertFalse(self.calls)
        local=self.root/'helper.elf';local.write_bytes(b'ELF')
        self.assertTrue(self.transport.stage_new(local,'/small-helper','unused')['small'])

    def test_missing_raw_SELF_ack_refuses_before_RETR(self):
        self.files[REMOTE]=self.data;self.fault='SELF_ack'
        with self.assertRaisesRegex(RuntimeError,'not positively disabled'):
            self.transport.web('/fs'+REMOTE,4<<20,20)
        self.assertEqual(self.calls.count('SELF'),1)
        self.assertFalse(any(c.startswith('RETR ')for c in self.calls));self.assertIn('close',self.calls)

    def test_transfer_failure_is_not_masked_by_QUIT(self):
        self.files[REMOTE]=self.data;self.fault='network'
        with self.assertRaisesRegex(TimeoutError,'Synthetic transport loss'):
            self.transport.web('/fs'+REMOTE,4<<20,20)
        self.assertNotIn('quit',self.calls);self.assertIn('close',self.calls)

    def test_QUIT_failure_retains_intent_without_positive_record_or_retry(self):
        self.files[REMOTE]=self.data;self.fault='quit'
        with self.assertRaisesRegex(RuntimeError,'Synthetic QUIT failure'):
            self.transport.web('/fs'+REMOTE,4<<20,20)
        self.assertEqual(sum(c.startswith('RETR ')for c in self.calls),1)
        self.assertFalse(list((self.root/'events').glob('*.returned.private.json')))

if __name__=='__main__':unittest.main()

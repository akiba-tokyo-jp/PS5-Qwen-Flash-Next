#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual publication order and refusal behavior without network access."""
from pathlib import Path
import hashlib,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from static_shader_resource import RESOURCE_DIRECTORY,publish_static_shader_resource,resource_record

class Transport:
    def __init__(self,mode,target,pending,data):
        self.mode,self.target,self.pending,self.data=mode,target,pending,data
        self.files={'original-eboot-sentinel':b'preserved'};self.operations=[];self.target_reads=0
        if mode=='existing':self.files[target]=data
        if mode=='wrong_existing':self.files[target]=b'x'*len(data)
        if mode=='retained_partial':self.files[pending]=b'partial'
    def read_optional(self,path,limit):
        self.operations.append(('read',path));self.assert_bound(limit)
        if path==self.target:
            self.target_reads+=1
            if self.mode=='initial_timeout'and self.target_reads==1:raise TimeoutError('Synthetic initial read timeout')
            if self.mode=='late_target'and self.target_reads==2:self.files[path]=self.data
            if self.mode=='readback_timeout'and self.target_reads==3:raise TimeoutError('Synthetic readback timeout')
        return self.files.get(path)
    def assert_bound(self,limit):
        if limit!=len(self.data)+1:raise AssertionError('Unexpected static resource response bound')
    def stage_new(self,local,pending,digest):
        self.operations.append(('upload',pending))
        if pending in self.files:raise AssertionError('Existing data overwritten')
        data=Path(local).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise AssertionError('Source changed')
        self.files[pending]=data[:7]if self.mode=='upload_timeout'else data
        if self.mode=='upload_timeout':raise TimeoutError('Synthetic upload uncertainty')
    def rename_new(self,pending,target):
        self.operations.append(('rename',target))
        if target in self.files:raise AssertionError('Existing target overwritten')
        self.files[target]=self.files.pop(pending)
        if self.mode=='rename_timeout':raise TimeoutError('Synthetic rename acknowledgement timeout')
        if self.mode=='bad_readback':self.files[target]=b'x'*len(self.data)
        return '200 unexpected'if self.mode=='bad_ack'else'250 Rename completed'

class StaticShaderResourceTests(unittest.TestCase):
    def test_actual_transaction_controls(self):
        parent=ROOT/'.test-tmp';parent.mkdir(exist_ok=True)
        for mode in ('new','existing','wrong_existing','retained_partial','initial_timeout','upload_timeout','late_target',
                     'rename_timeout','bad_ack','bad_readback','readback_timeout'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory(dir=parent)as directory:
                base=Path(directory);self.assertTrue(base.resolve().is_relative_to(parent.resolve()))
                source=base/'original-resource.bin';data=bytes(range(256))*4;source.write_bytes(data)
                local=resource_record(source);target=RESOURCE_DIRECTORY+'/shader-storage-'+local['sha256']+'.bin'
                nonce='a'*32;pending=target+'.pending-'+nonce;transport=Transport(mode,target,pending,data);journal=base/'journal'
                if mode in ('new','existing'):
                    result=publish_static_shader_resource(transport,local,target,nonce,journal)
                    self.assertTrue(result['full_raw_readback_verified']);self.assertEqual(result['existing_exact_bytes_reused'],mode=='existing')
                    self.assertEqual(result['upload_attempts'],0 if mode=='existing'else 1)
                    self.assertEqual(transport.files[target],data)
                else:
                    with self.assertRaises((ValueError,FileExistsError,TimeoutError,RuntimeError)):
                        publish_static_shader_resource(transport,local,target,nonce,journal)
                    self.assertFalse((journal/'ready.private.json').exists())
                    self.assertEqual(json.loads((journal/'failure.private.json').read_text())['automatic_retries'],0)
                self.assertEqual(transport.files['original-eboot-sentinel'],b'preserved')
                operations=list(transport.operations)
                with self.assertRaises(FileExistsError):publish_static_shader_resource(transport,local,target,nonce,journal)
                self.assertEqual(transport.operations,operations,'Consumed publication issued another request')
                self.assertLessEqual(sum(op=='upload'for op,_ in operations),1)
                self.assertLessEqual(sum(op=='rename'for op,_ in operations),1)
                if mode in ('existing','wrong_existing','retained_partial','initial_timeout'):
                    self.assertFalse(any(op in ('upload','rename')for op,_ in operations))
                if mode in ('upload_timeout','late_target'):
                    self.assertIn(pending,transport.files);self.assertFalse(any(op=='rename'for op,_ in operations))
    def test_namespace_and_local_integrity(self):
        parent=ROOT/'.test-tmp';parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent)as directory:
            base=Path(directory);source=base/'data.bin';source.write_bytes(b'original static resource')
            local=resource_record(source);target=RESOURCE_DIRECTORY+'/shader-storage-'+local['sha256']+'.bin'
            for kind in ('wrong_directory','invalid_nonce','changed_source','invalid_size'):
                record=dict(local);destination=target;nonce='a'*32
                if kind=='wrong_directory':destination='/data/ai/eboot.bin'
                if kind=='invalid_nonce':nonce='../invalid'
                if kind=='changed_source':record['sha256']='0'*64;destination=RESOURCE_DIRECTORY+'/shader-storage-'+record['sha256']+'.bin'
                if kind=='invalid_size':record['bytes']=17<<20
                transport=Transport('new',destination,destination+'.pending-'+nonce,source.read_bytes())
                with self.subTest(kind=kind),self.assertRaises(ValueError):
                    publish_static_shader_resource(transport,record,destination,nonce,base/kind)
                self.assertFalse(transport.operations)

if __name__=='__main__':unittest.main()

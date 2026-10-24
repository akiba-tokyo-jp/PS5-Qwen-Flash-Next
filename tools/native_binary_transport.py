#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stream owned native SELF readbacks through the existing FTP service.

This optional controller adapter preserves complete returned bytes and the
caller's existing length/SHA or exact-byte checks. It changes no native code,
source reads, memory predicate, driver policy or small management request.
"""
import ftplib
import hashlib
import json
from pathlib import Path, PurePosixPath
import time
import urllib.parse

MAXIMUM_BINARY_BYTES=128<<20

class NativeBinaryFTP:
    def __init__(self,base,event_root,*,local_root=Path('D:/PS5-AI'),ftp_factory=ftplib.FTP,clock=time.monotonic):
        self.base=base;self.event_root=Path(event_root);self.local_root=Path(local_root).resolve()
        self.ftp_factory=ftp_factory;self.clock=clock;self.sequence=0

    def __getattr__(self,name):return getattr(self.base,name)

    def _remote(self,path):
        self.base.allowed(path)
        name=PurePosixPath(path).name
        if(str(PurePosixPath(path).parent)!='/data/ai/native-moss-image-sft/PPSA99190'or
           not name.startswith('eboot')or not name.endswith('.bin')or len(name)>160 or
           any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-'for c in name)or
           '\r'in path or '\n'in path):
            raise ValueError('Binary streaming is restricted to the owned native SELF paths')
        return path

    def _event(self,operation,remote):
        self.sequence+=1;self.event_root.mkdir(parents=True,exist_ok=True)
        stem=self.event_root/f'{self.sequence:03d}-{operation}'
        with stem.with_suffix('.intent.private.json').open('x',encoding='utf-8')as out:
            json.dump(dict(operation=operation,remote=remote,automatic_retries=0),out,indent=2)
        return stem

    def _finish(self,stem,value):
        with stem.with_suffix('.returned.private.json').open('x',encoding='utf-8')as out:json.dump(value,out,indent=2)

    def _retrieve(self,remote,limit,timeout):
        remote=self._remote(remote)
        if not 0<limit<=MAXIMUM_BINARY_BYTES or not 0<timeout<=60:raise ValueError('Invalid bounded SELF transfer')
        stem=self._event('FTP-RETR',remote);raw=bytearray();hash_state=hashlib.sha256();begun=self.clock()
        def consume(block):
            if self.clock()-begun>timeout:raise TimeoutError('SELF readback exceeded its finite deadline; no retry')
            if not block or len(raw)+len(block)>limit:raise RuntimeError('SELF readback exceeded its complete-byte bound')
            raw.extend(block);hash_state.update(block)
        with self.ftp_factory()as ftp:
            ftp.connect(self.base.HOST,2121,timeout=min(8,timeout));ftp.login()
            reply=ftp.retrbinary('RETR '+remote,consume,blocksize=65536)
        if not reply.startswith('226')or self.clock()-begun>timeout:
            raise RuntimeError('SELF readback lacks positive finite FTP completion')
        self._finish(stem,dict(protocol='FTP RETR',bytes=len(raw),sha256=hash_state.hexdigest(),
            positive_transfer_completion=True,caller_must_verify_exact_expected_bytes=True,automatic_retries=0))
        return raw

    def web(self,path,limit=1<<20,timeout=15):
        parsed=urllib.parse.urlsplit(path)
        if limit>1<<20 and parsed.path.startswith('/fs')and parsed.path.endswith('.bin'):
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:raise ValueError('A local owned SELF path is required')
            return self._retrieve(urllib.parse.unquote(parsed.path[3:]),limit,timeout)
        return self.base.web(path,limit,timeout)

    def stage_new(self,local,remote,expected):
        local=Path(local)
        if local.suffix.lower()!='.bin'or local.stat().st_size<=1<<20:
            return self.base.stage_new(local,remote,expected)
        remote=self._remote(remote)
        if not local.resolve().is_relative_to(self.local_root):raise ValueError('SELF staging escaped its owned local artifact directory')
        if not 0<local.stat().st_size<=MAXIMUM_BINARY_BYTES:raise ValueError('SELF staging exceeds its bounded artifact size')
        raw=local.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:raise RuntimeError('The frozen native SELF changed before staging')
        # Absence uses the existing small metadata request. Never translate an
        # ambiguous FTP 550 into absence or overwrite a retained partial upload.
        self.base.absent(remote);stem=self._event('FTP-STOR',remote);begun=self.clock()
        def sent(_):
            if self.clock()-begun>30:raise TimeoutError('Native SELF upload exceeded its finite deadline; retain the partial without retry')
        with self.ftp_factory()as ftp:
            ftp.connect(self.base.HOST,2121,timeout=8);ftp.login()
            with local.open('rb')as source:reply=ftp.storbinary('STOR '+remote,source,262144,callback=sent)
        if not reply.startswith('226')or self.clock()-begun>30:raise RuntimeError('Native SELF upload completion is unknown; retain it without retry')
        self._finish(stem,dict(protocol='FTP STOR',bytes=len(raw),sha256=expected,positive_transfer_completion=True,automatic_retries=0))
        readback=self._retrieve(remote,len(raw),20)
        if readback!=raw:raise RuntimeError('Complete native SELF raw readback differs; no publication or retry')
        return dict(path=remote,bytes=len(raw),sha256=expected,full_raw_readback_verified=True,readback_protocol='FTP RETR')

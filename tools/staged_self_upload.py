#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Upload one new owned SELF, with native whole integrity before publication.

Transport acknowledgement is not integrity qualification. The mandatory callback
must verify complete native SHA256, stable identity and EOF while the original
executable remains canonical. No raw HTTP payload readback is issued here.
"""
import hashlib,re
from pathlib import Path


def upload(capture,remote,out,lan,native_verify):
    path=Path(capture['path']);out=Path(out)
    owned_pending=r'(?:/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-qwen-plan-[0-9]+|/data/ai/moss-qwen-case-[0-9a-f]{32}-(?:candidate|restore)-SELF)\.bin'
    if (not re.fullmatch(owned_pending,remote)or
        type(capture['bytes'])is not int or not 0<capture['bytes']<=128<<20 or
        not re.fullmatch('[0-9a-f]{64}',capture['sha256'])or not callable(native_verify)):
        raise ValueError('An exact new owned SELF and mandatory native verifier are required')
    before=path.stat();digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if before.st_size!=capture['bytes']or digest!=capture['sha256']:
        raise ValueError('The exact original local SELF changed before upload')
    lan.allowed(remote);lan.absent(remote);out.mkdir(parents=True,exist_ok=False)
    lan.save(out/'intent.json',dict(SELF=capture,remote=remote,automatic_retries=0,
        whole_native_verification_required_before_publication=True,raw_HTTP_payload_readbacks=0))
    sent=0;streamed=hashlib.sha256()
    def transferred(block):
        nonlocal sent
        sent+=len(block);streamed.update(block)
        if sent>capture['bytes']:raise ValueError('SELF upload exceeded its exact source')
    with lan.ftplib.FTP()as ftp:
        ftp.connect(lan.HOST,2121,timeout=30);ftp.login()
        with path.open('rb')as source:response=ftp.storbinary('STOR '+remote,source,262144,transferred)
    after=path.stat()
    identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if (not isinstance(response,str)or not response.startswith('226 ')or sent!=capture['bytes']or
        streamed.hexdigest()!=capture['sha256']or identity(before)!=identity(after)):
        raise RuntimeError('SELF transfer or local identity is incomplete; no native retry or publication')
    lan.save(out/'transfer-returned.json',dict(bytes=sent,sha256=streamed.hexdigest(),FTP_completed=True,
        integrity_qualified=False,raw_HTTP_payload_readbacks=0))
    evidence=native_verify(capture,remote)
    if (not evidence.get('whole_native_SHA256_identity_EOF_verified')or not evidence.get('all_reads_returned')or
        evidence.get('sha256')!=capture['sha256']or evidence.get('bytes')!=capture['bytes']):
        raise RuntimeError('Fresh whole native SELF integrity is required before publication')
    result=dict(completed=True,bytes=sent,sha256=capture['sha256'],raw_HTTP_payload_readbacks=0,
        native_verification=evidence,original_canonical_until_native_verification=True,automatic_retries=0)
    lan.save(out/'complete.json',result);return result

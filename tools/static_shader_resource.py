#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish one immutable original shader resource with no overwrite or retry."""
import hashlib,json,os,re
from pathlib import Path
RESOURCE_DIRECTORY='/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime'
MAXIMUM_STATIC_RESOURCE_BYTES=16<<20

def resource_record(path):
    path=Path(path).resolve();digest=hashlib.sha256()
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1<<20),b''):digest.update(block)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=digest.hexdigest())

def _save(path,value):
    with path.open('x',encoding='utf-8')as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def publish_static_shader_resource(transport,local,target,nonce,journal):
    if not isinstance(local,dict)or set(local)!={'path','bytes','sha256'}:
        raise ValueError('An exact local static resource record is required')
    digest=local['sha256'];size=local['bytes']
    if not isinstance(digest,str)or re.fullmatch('[0-9a-f]{64}',digest)is None or type(size)is not int or not 0<size<=MAXIMUM_STATIC_RESOURCE_BYTES:
        raise ValueError('Static resource bytes or complete SHA256 exceed the qualified bound')
    if re.fullmatch('[0-9a-f]{32}',nonce)is None or target!=RESOURCE_DIRECTORY+'/shader-storage-'+digest+'.bin':
        raise ValueError('Static resources require the exact owned SHA-named application path')
    if resource_record(local['path'])!=local:raise ValueError('The immutable local resource changed')
    journal=Path(journal);journal.mkdir(parents=False,exist_ok=False)
    pending=target+'.pending-'+nonce;phase='initial_target_read';upload_attempts=rename_attempts=0
    _save(journal/'intent.private.json',dict(local=local,target=target,pending=pending,automatic_retries=0,
        overwrite_allowed=False,model_files_modified=False,title_launches=0,GPU_calls=0))
    def verify(raw):
        if not isinstance(raw,bytes)or len(raw)!=size or hashlib.sha256(raw).hexdigest()!=digest:
            raise ValueError('Static resource full raw byte-count/SHA256 verification failed')
    try:
        current=transport.read_optional(target,size+1)
        reused=current is not None
        if reused:verify(current)
        else:
            phase='pending_absence'
            if transport.read_optional(pending,size+1)is not None:
                raise FileExistsError('A retained static resource partial must never be overwritten')
            phase='upload_pending';upload_attempts=1
            _save(journal/'upload.once.private.json',dict(local=local,pending=pending,automatic_retries=0))
            transport.stage_new(local['path'],pending,digest)
            phase='second_target_absence'
            if transport.read_optional(target,size+1)is not None:
                raise FileExistsError('Static target appeared after upload; preserve pending input without replacement')
            phase='rename_new';rename_attempts=1
            _save(journal/'rename.once.private.json',dict(pending=pending,target=target,expected_target_absent=True,automatic_retries=0))
            reply=transport.rename_new(pending,target)
            _save(journal/'rename-response.private.json',dict(reply=reply if isinstance(reply,str)else None))
            # ftpsrv's RNTO implementation returns this exact completion reply.
            # Standard FTP250 completion remains accepted; other226 replies do not.
            if not isinstance(reply,str)or not(reply.startswith('250 ')or reply=='226 Path renamed'):
                raise RuntimeError('Static resource rename lacks a positive FTP completion acknowledgement')
            phase='final_target_read';verify(transport.read_optional(target,size+1))
        if resource_record(local['path'])!=local:raise ValueError('Static source changed during publication')
        result=dict(state='static_original_shader_resource_ready',local=local,target=target,full_raw_readback_verified=True,
            existing_exact_bytes_reused=reused,upload_attempts=upload_attempts,rename_attempts=rename_attempts,
            automatic_retries=0,original_SELF_never_modified=True,model_files_modified=False,
            persistent_compiled_cache=False,title_launches=0,GPU_calls=0)
        _save(journal/'ready.private.json',result);return result
    except BaseException as error:
        _save(journal/'failure.private.json',dict(phase=phase,error_type=type(error).__name__,upload_attempts=upload_attempts,
            rename_attempts=rename_attempts,partials_retained=True,automatic_retries=0,overwrite_allowed=False,
            original_SELF_never_modified=True,title_launches=0,GPU_calls=0))
        raise

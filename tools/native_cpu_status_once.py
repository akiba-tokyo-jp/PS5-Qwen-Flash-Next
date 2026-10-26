#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One CPU submission; poll fixed metadata and retrieve the durable journal once."""
import datetime,re,time,urllib.error,urllib.parse
from pathlib import Path,PurePosixPath

def execute(lan,manifest,out,timeout=360):
    if not 1<=timeout<=360:raise ValueError('Finite CPU status observation required')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    artifact=manifest['artifact'];remote=manifest['remote_elf'];journal=manifest['remote_log'];status=manifest['remote_status']
    for name in (remote,journal,status):lan.allowed(name)
    for name in (journal,status):lan.absent(name)
    transfer=lan.stage_new(artifact['path'],remote,artifact['sha256'])
    request=dict(elf=remote,cwd='/data/ai',args=PurePosixPath(remote).name+' ',pipe='0')
    lan.save(out/'execution.once.private.json',dict(artifact=transfer,request=request,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),automatic_retries=0,
        status_poll_bytes=512,journal_retrieved_once_after_terminal=True,maximum_seconds=timeout))
    try:
        raw=lan.web('/elfldr?'+urllib.parse.urlencode(request),65536,8)
        (out/'elfldr-response.private.txt').write_bytes(raw)
    except Exception as error:
        lan.save(out/'elfldr-ambiguous.private.json',dict(error_type=type(error).__name__,resubmitted=False))
    deadline=time.monotonic()+timeout;last=-1;last_status=b''
    while time.monotonic()<deadline:
        try:
            raw=lan.web('/fs'+urllib.parse.quote(status,safe='/'),512,8)
            if len(raw)!=512 or('nonce='+manifest['nonce']).encode()not in raw:raise ValueError('CPU status binding differs')
            (out/'status.private.log').write_bytes(raw);last_status=raw
            m=re.search(rb'last_completed_files=(\d+)',raw)
            if not m:raise ValueError('CPU completed-boundary status missing')
            count=int(m[1])
            if count<last or count>len(manifest['sources']):raise ValueError('CPU progress regressed or exceeded its bound')
            if count//32!=last//32:
                print('Returned file boundaries: '+str(count)+' / '+str(len(manifest['sources'])),flush=True)
            last=count
            if b'\nEND 'in raw:
                # One complete read after the producer's terminal fsync.
                journal_raw=lan.web('/fs'+urllib.parse.quote(journal,safe='/'),16<<20,25)
                (out/'console.private.log').write_bytes(journal_raw)
                lan.save(out/'terminal.private.json',dict(status_closed=True,journal_fetched_once=True,
                    raw_bytes=len(journal_raw),automatic_retries=0))
                return journal_raw
        except urllib.error.HTTPError as error:
            if error.code!=404:raise
        time.sleep(2)
    lan.save(out/'observation-expired.private.json',dict(last_completed_files=last,automatic_retries=0,
        completion_unknown=True,last_status_bytes=len(last_status)))
    raise RuntimeError('CPU completion unknown; no resubmission or release')

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stage one new 64-Expert fragment over four bounded ordinary raw FTP streams."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import secrets
import time
from build_performance_quantizer import record
from native_VM_observation import query
from start_success_route import load,need,save
from success_case_control import current_files,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','current','mount-plan','layer','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--first-Expert',type=int,default=0);p.add_argument('--execute',action='store_true')
    p.add_argument('--prepared',type=Path,help='Reuse the exact already prepared four local parts without copying or encoding again')
    a=p.parse_args();layer=load(a.layer);need(layer['completed'] and layer['complete_layer'] and
        layer['encoded_Experts']==512 and layer['role'] in ('up','down') and layer['pack']['bytes']==216268800 and
        0<=a.first_Expert<=448 and a.first_Expert%64==0,'One completed real IQ2 layer and new 64-Expert fragment required')
    a.out.mkdir(parents=True,exist_ok=False)
    if a.prepared:
        old=load(a.prepared);rows=old['parts'];fragment=old['fragment']
        need(old['layer']==record(a.layer) and old['parallel_connections']==4 and
             fragment['first_Expert']==a.first_Expert and fragment['Experts']==64 and fragment['bytes']==27033600 and
             len(rows)==4 and all(record(r['local']['path'])==r['local'] for r in rows) and
             not(a.prepared.parent/'upload.once.private.json').exists(),
             'Only the exact unused prepared local fragment may be reused')
    else:
        need(record(layer['pack']['path'])==layer['pack'],'The frozen encoded layer changed')
        rows=[];whole=hashlib.sha256();bytes_per_part=16*422400
        before=Path(layer['pack']['path']).stat()
        with Path(layer['pack']['path']).open('rb') as source:
            source.seek(a.first_Expert*422400)
            for index in range(4):
                path=a.out/f'part-{index}.bin';digest=hashlib.sha256();remaining=bytes_per_part
                with path.open('xb') as target:
                    while remaining:
                        block=source.read(min(262144,remaining));need(bool(block),'Encoded fragment ended early')
                        target.write(block);digest.update(block);whole.update(block);remaining-=len(block)
                rows.append(dict(local=dict(path=str(path.resolve()),bytes=bytes_per_part,sha256=digest.hexdigest()),
                    remote='/data/ai/moss-qwen-case-'+secrets.token_hex(16)+'-candidate-SELF.bin'))
        after=Path(layer['pack']['path']).stat();need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'Encoded source identity changed')
        fragment=dict(bytes=4*bytes_per_part,sha256=whole.hexdigest(),first_Expert=a.first_Expert,Experts=64)
    selected=current_files(a.current);save(a.out/'intent.private.json',dict(layer=record(a.layer),fragment=fragment,
        parts=rows,parallel_connections=4,maximum_host_window_bytes_per_connection=262144,
        deadline_seconds=180,automatic_retries=0,current_seven=selected,source_publication_still_required=True,
        source_offsets_disjoint=True,original_source_writes=0,GPU_calls=0,title_launches=0))
    if not a.execute:print(json.dumps(dict(prepared=True,fragment=fragment,PS5_operations=0)));return
    state=load(a.current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'One positively idle console owner required')
    values=query(a.workspace,a.current,a.mount_plan,a.out/'VM-before')
    required=1154+(fragment['bytes']+16383)//16384+512+21
    need(values['boot_before']==values['boot_after']==state['current_boot'],'The current boot must remain exact')
    save(a.out/'admission.private.json',dict(observations=values,required_pages=required,
        full_upload_bytes_charged=True,selected_FTP_service_allowance_pages=512,
        universal_allocation_bound_claimed=False,may_upload=min(values['free_first'],values['free_last'])>=required))
    need(min(values['free_first'],values['free_last'])>=required,'The entire buffered fragment must fit before any upload')
    lan=lan_module()
    for row in rows:lan.allowed(row['remote']);lan.absent(row['remote'])
    save(a.out/'upload.once.private.json',dict(parts=rows,automatic_retries=0))
    if a.prepared:save(a.prepared.parent/'upload.once.private.json',dict(actual_upload_intent=record(a.out/'upload.once.private.json')))
    started=time.monotonic()
    def send(index,row):
        ftp=lan.ftplib.FTP();begun=time.monotonic();sent=0
        try:
            ftp.connect(lan.HOST,2121,timeout=30);ftp.login()
            need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Ordinary raw FTP mode required')
            def progress(block):
                nonlocal sent
                sent+=len(block);need(time.monotonic()-started<180,'The four-stream scope deadline ended; never retry')
            with Path(row['local']['path']).open('rb') as source:
                reply=ftp.storbinary('STOR '+row['remote'],source,blocksize=262144,callback=progress)
            need(reply.startswith('226 ') and sent==row['local']['bytes'],'A complete positive FTP store is required')
            quit_reply=ftp.quit();need(quit_reply.startswith(('221 ','226 ')),'Positive ordinary FTP session close required')
            result=dict(completed=True,bytes=sent,seconds=time.monotonic()-begun,STOR_reply=reply,QUIT_reply=quit_reply)
        except Exception as error:
            result=dict(completed=False,bytes=sent,seconds=time.monotonic()-begun,error=str(error),automatic_retries=0)
        finally:ftp.close()
        save(a.out/f'part-{index}.result.private.json',result);return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(send,i,row) for i,row in enumerate(rows)]
        results=[future.result() for future in futures]
    elapsed=time.monotonic()-started;done=all(r['completed'] for r in results)
    need(current_files(a.current)==selected,'The seven selected local files changed')
    save(a.out/'result.private.json',dict(completed=done,parts=rows,part_results=results,fragment=fragment,
        all_FTP_calls_returned=True,all_host_file_and_socket_handles_closed=True,elapsed_seconds=elapsed,
        aggregate_MiB_per_second=fragment['bytes']/(1<<20)/elapsed if done else None,
        native_whole_SHA256_and_EOF_still_required=True,immutable_source_publication_still_required=True,
        original_source_writes=0,title_launches=0,GPU_calls=0,automatic_retries=0))
    print(json.dumps(dict(completed=done,bytes=fragment['bytes'],seconds=elapsed,
        aggregate_MiB_per_second=fragment['bytes']/(1<<20)/elapsed if done else None)),flush=True)
    need(done,'Every FTP call returned; retain the actual positive prefix and inspect failures without replay')


if __name__=='__main__':main()

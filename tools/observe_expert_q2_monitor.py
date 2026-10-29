#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe a bound Q2 native owner; issue two finite requests and one finish once."""
import argparse,hashlib,http.client,ipaddress,json,struct,time
from pathlib import Path
from urllib.parse import quote
from expert_q4 import require,record
PROMPT='Count from 1 to 8, separated by commas. Reply with only the sequence.'

def exclusive(path,value):
    import os
    with Path(path).open('x',encoding='utf-8',newline='\n')as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    b=json.loads(a.binding.read_text());host=b['host'];owner=b['native_binding'];run=owner['run_id'];remote=b['report_remote']
    ip=ipaddress.ip_address(host)
    require(ip.version==4 and ip.is_private and not ip.is_loopback and not ip.is_unspecified and not ip.is_multicast,
        'Only the bound private physical console is allowed')
    require(b['schema']=='ps5-qwen-Expert-Q2-monitor-binding-v1' and b['port']==8086 and b['automatic_retries']==0 and
        len(run)==32 and set(run)<=set('0123456789abcdef') and owner['pid']>0 and
        remote=='/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/plan-'+run+'.json', 'Exact Q2 owner and report binding required')
    out=a.out;out.mkdir(parents=True,exist_ok=False)
    exclusive(out/'intent.private.json',dict(binding=record(a.binding),maximum_generation_POSTs=2,maximum_finish_POSTs=1,
        automatic_retries=0,title_launches=0,GPU_submissions=0,host_model_inference=False))
    def get(port,path,limit):
        connection=http.client.HTTPConnection(host,port,timeout=10)
        try:
            connection.request('GET',path,headers={'Connection':'close'});response=connection.getresponse();raw=response.read(limit+1)
            require(len(raw)<=limit,'Observation byte bound exceeded')
            if response.status==404:return None
            require(response.status==200,'Unexpected read-only observation status');return raw
        finally:connection.close()
    def download(suffix,limit=4<<20):
        raw=get(8080,'/fs'+quote(remote+suffix,safe='/'),limit)
        if raw is not None:
            path=out/('native'+suffix+'.private.bin')
            if path.exists():require(path.read_bytes()==raw,'Previously completed native report changed')
            else:path.write_bytes(raw)
        return raw
    def failure():
        for suffix in ('.failure','.fatal'):
            if download(suffix) is not None:
                exclusive(out/'known-native-failure.private.json',dict(native_explicit_failure=True,automatic_retries=0))
                return True
        return False
    started=time.monotonic();next_update=0
    while True:
        raw=download('.demo.ready')
        if raw is not None:break
        if failure():return
        require(time.monotonic()-started<1800,'Q2 ready deadline; retain original ownership without retry')
        if time.monotonic()>=next_update:
            print(json.dumps(dict(Q2_monitor_waiting_for_model_and_warmup=True,elapsed_seconds=round(time.monotonic()-started))),flush=True)
            next_update=time.monotonic()+30
        time.sleep(2)
    ready=json.loads(raw)
    require(ready['pid']==owner['pid'] and ready['run_id']==run and ready['maximum_requests']==2 and
        ready['native_display_started'] and ready['model_loaded'] and ready['listener_bind']=='0.0.0.0','Exact native passive readiness required')
    def status():
        value=json.loads(get(8086,'/api/status',1<<20))
        require(value['process_id']==owner['pid'] and value['run_id']==run and value['model_loaded'] and
            not value['quarantined'] and value['clock']['calibrated'],'Exact healthy Q2 status required')
        return value
    first=status();exclusive(out/'first-status.private.json',first)
    assets=b['monitor_assets'];require(set(assets)=={'/','/app.js','/style.css'},'All original passive assets required')
    for path,digest in assets.items():
        raw=get(8086,path,256<<10);require(raw is not None and hashlib.sha256(raw).hexdigest()==digest,'Passive asset digest differs')
    def post(path,body,stem,streamed):
        exclusive(out/(stem+'.once.private.json'),dict(path=path,body=body,automatic_retries=0))
        connection=http.client.HTTPConnection(host,8086,timeout=10)
        try:
            connection.connect();transport=connection.sock;require(transport is not None,'Once-only connection missing')
            transport.settimeout(3600 if streamed else 10)
            connection.request('POST',path,json.dumps(body),{'Content-Type':'application/json','Connection':'close'})
            response=connection.getresponse();require(response.status==200,'Once-only request refused; never replay it')
            if not streamed:
                raw=response.read(4097);require(len(raw)<=4096 and json.loads(raw)=={'state':'accepted'},'Finish acknowledgement differs')
                return []
            events=[];received=0;request_started=time.monotonic()
            with (out/(stem+'.stream.private.log')).open('xb')as stream:
                while True:
                    remaining=3600-(time.monotonic()-request_started);require(remaining>0,'Once-only stream deadline')
                    transport.settimeout(remaining);line=response.readline((256<<10)+1)
                    require(len(line)<=256<<10,'Stream line bound exceeded')
                    if not line:break
                    received+=len(line);require(received<=8<<20,'Stream byte bound exceeded');stream.write(line);stream.flush()
                    if line.startswith(b'data: '):
                        event=json.loads(line[6:]);events.append(event)
                        require(len(events)<=33 and event['id']==body['id'] and event.get('error')==0,'Failed or mismatched native stream; no retry')
            require(3<=len(events)<=33 and events[-1]['type']=='finished' and events[-1]['state']=='completed' and
                all(e['type']=='token' and e['ordinal']==i for i,e in enumerate(events[:-1],1)),'Complete ordered native stream required')
            exclusive(out/(stem+'.positive.private.json'),dict(events=events,HTTP_status=200));return events
        except BaseException as error:
            exclusive(out/(stem+'.not-retried.private.json'),dict(error=type(error).__name__,automatic_retries=0,ownership_retained=True));raise
        finally:connection.close()
    streams=[];frames=[]
    for ordinal in (1,2):
        streams.append(post('/api/generate',dict(id=run+'-'+str(ordinal),messages=[dict(role='user',content=PROMPT)],
            context_tokens=256,max_output_tokens=32,enable_thinking=False),'request-'+str(ordinal),True))
        deadline=time.monotonic()+30
        while True:
            value=status()
            if not value['busy'] and value['validation']['completed_requests']==ordinal:break
            require(time.monotonic()<deadline,'Native API did not return to positively completed idle');time.sleep(.2)
        exclusive(out/('status-'+str(ordinal)+'.private.json'),value)
        raw=download('.arm'+str(ordinal)+'.result');row=json.loads(raw)
        tokens=streams[-1][:-1]
        require(row['token_ids']==[e['token_id']for e in tokens] and row['output_bytes']==[v for e in tokens for v in e['piece_bytes']] and
            row['counting_quality_passed'] and row['request_reset_completed'] and row['maximum_absolute_logit_error']<=1e-5,
            'Durable Q2 result, stream and same-Q2 logits differ')
        frame=json.loads(download('.arm'+str(ordinal)+'.display.json'))
        bmp=download('.arm'+str(ordinal)+'.display.bmp',9<<20)
        require(frame['pid']==owner['pid'] and frame['id']==run+'-'+str(ordinal) and frame['positive_VideoOut_completion'] and
            frame['clock_calibrated'] and frame['model_loaded'] and frame['generated_tokens']==len(tokens) and
            frame['decode_tokens_per_second']==row['metrics']['decode_tokens_per_second'] and len(bmp)==8294454 and
            bmp[:2]==b'BM' and struct.unpack_from('<ii',bmp,18)==(1920,1080),'Matching positively completed native frame required')
        frames.append(frame)
        print(json.dumps(dict(Q2_passive_API_request_completed=ordinal,decode_tokens_per_second=row['metrics']['decode_tokens_per_second'])),flush=True)
    last=status();require(last['server_epoch_ms']-first['server_epoch_ms']>=1000,'Positive calibrated clock advance required')
    exclusive(out/'last-status.private.json',last)
    post('/api/validation/finish',{'run_id':run},'finish',False)
    deadline=time.monotonic()+60
    while True:
        raw=download('')
        if raw is not None:break
        if failure():return
        require(time.monotonic()<deadline,'Positive model/source retirement result missing');time.sleep(1)
    result=json.loads(raw)
    require(result['completed'] and result['pid']==owner['pid'] and result['run_id']==run and
        result['candidate_SELF_sha256']==owner['candidate_SELF_sha256'] and result['model_receipt_sha256']==owner['model_receipt_sha256'] and
        result['active_cache_slots']==581 and result['HTTP_requests']==2 and result['VideoOut_starts']==1 and
        result['passive_monitor_and_API_completed'] and result['all_model_source_device_owners_positively_retired'] and
        result['device_ledger_live_bytes']==0 and result['full_F32_continuation_and_routes_passed'] and
        result['source_windows']==result['source_completed_windows'],'Exact positive Q2 application completion required')
    exclusive(out/'complete.private.json',dict(completed=True,native_binding=owner,POSTs=3,automatic_retries=0,
        actual_native_frames=frames,passive_assets_verified=True,model_source_GPU_owners_positively_retired=True,
        ordinary_OS_close_and_exact_restore_still_required=True))
    print('Both Q2 API requests, passive frames and positive model/source/GPU retirement passed.',flush=True)
if __name__=='__main__':main()

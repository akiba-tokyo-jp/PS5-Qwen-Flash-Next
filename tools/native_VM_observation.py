#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read all fixed VM counters in one ordinary helper, without shell commands."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import FIELDS,review
from start_success_route import load,need,save
from success_case_control import build,complete,current_files,execute,lan_module


def decode(raw):
    pattern=rb'VM_COUNTER index=(\d+) key=([a-z_]+) rc=(-?\d+) expected_bytes=(\d+) returned_bytes=(\d+) canaries=(\d+) value0=(\d+) value1=(\d+)'
    rows=re.findall(pattern,raw);need(len(rows)==len(FIELDS),'Every fixed native VM observation must return')
    values={}
    for index,((key,_,size),row) in enumerate(zip(FIELDS,rows)):
        i,k,rc,expected,returned,canaries,v0,v1=row
        need(int(i)==index and k.decode()==key and int(rc)==0 and int(expected)==int(returned)==size and int(canaries)==1,
             'One original-size successful guarded native sysctl result is required')
        values[key]=[int(v0),int(v1)] if size==16 else int(v0)
    return values


def query(workspace,current,mount_plan,out,collect=False):
    state=load(current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'Positive idle current deployment required')
    selected=current_files(current);lan=lan_module()
    if collect:
        plan=load(out/'native/plan.private.json');need((out/'native/execution/execution.once.private.json').exists(),'Collect only the same submitted reader')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,out/'native',raw,path)
    else:
        out.mkdir(parents=True,exist_ok=False)
        context='struct VMField{const char*key;const char*name;size_t bytes;};\nstatic const struct VMField fields[]={'+','.join(
            '{'+json.dumps(k)+','+json.dumps(n)+','+str(s)+'u}' for k,n,s in FIELDS)+'};\n'
        context+='''static int case_retire_completed_images(int*calls){
            for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);++i){
                const uint64_t guard=UINT64_C(0x8f437228ad2256b1);
                struct {uint64_t before;unsigned char data[16];uint64_t after;} value={guard,{0},guard};
                size_t bytes=fields[i].bytes;errno=0;
                ++*calls;int rc=sysctlbyname(fields[i].name,value.data,&bytes,NULL,0);
                uint64_t first=0,last=0;uint32_t scalar=0;
                if(fields[i].bytes==16){memcpy(&first,value.data,8);memcpy(&last,value.data+8,8);}
                else {memcpy(&scalar,value.data,4);first=scalar;}
                if(!report("VM_COUNTER index=%u key=%s rc=%d expected_bytes=%zu returned_bytes=%zu canaries=%d value0=%llu value1=%llu",
                    i,fields[i].key,rc,fields[i].bytes,bytes,value.before==guard&&value.after==guard,
                    (unsigned long long)first,(unsigned long long)last))return 0;
            }
            return report("VM_OBSERVATION_COMPLETE queries=13 writes=0 title_launches=0 GPU_calls=0");
        }\n'''
        plan=build(workspace,mount_plan,selected,selected,[],'retire-completed-images',out/'native',completed_images_context=context)
        save(out/'intent.private.json',dict(fields=list(FIELDS),selected=selected,boot=state['current_boot'],
            sysctl_writes=0,shell_commands=0,title_launches=0,GPU_calls=0,initializer_requests=0,automatic_retries=0))
        original=lan.web;expected='/fs'+urllib.parse.quote(plan['log'],safe='/')
        def bounded(path,limit=1<<20,timeout=15):return original(path,64<<20 if path==expected else limit,timeout)
        lan.web=bounded
        try:result=execute(lan,plan,out/'native',60)
        finally:lan.web=original
    need(result['completed'] and result['operation_calls']==len(FIELDS),'All fixed native reads and positive helper exit required')
    raw=Path(result['raw']['path']).read_bytes();values=decode(raw)
    # Reuse the original shape/boot review. This minimum review grants no
    #model launch; each caller must still apply its exact package's own price.
    shape=review(values,state['current_boot'],values['minimum']+max(values['reserved'],256))
    save(out/'result.private.json',dict(completed=True,observations=values,native=record(out/'native/result.private.json'),
        same_original_counter_names_sizes_and_shape_review=True,shape=shape,sysctl_writes=0,shell_commands=0,
        title_launches=0,GPU_calls=0,initializer_requests=0,automatic_retries=0,model_admission_granted=False))
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--collect',action='store_true');a=p.parse_args()
    values=query(a.workspace,a.current,a.mount_plan,a.out,a.collect)
    print(dict(completed=True,free_first=values['free_first'],free_last=values['free_last'],shell_commands=0,model_admission=False))


if __name__=='__main__':main()

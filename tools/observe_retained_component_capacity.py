#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe global Direct capacity after the retained component's ordinary exit."""
import argparse
from pathlib import Path
import re
from build_performance_quantizer import record
from start_success_route import load, need, save
from success_case_control import build, current_files, execute, lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'closed-component', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args(); done = load(a.closed_component)
    state_path = a.current/'active-console.private.json'; state = load(state_path)
    need(done['completed'] and done['native_passed'] and done['ordinary_exit_observed'] and
         done['completed_idle_device_retained_until_ordinary_exit'] and done['fresh_capacity_readmission_required'] and
         done['current_seven_restored_and_native_hashed'] and not done['unknown_completion'] and
         state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and state['GPU_retirement_readmission_pending'] and
         state['retained_component_ordinary_exit']['native'] == done['native'],
         'The exact positively completed and ordinarily exited retained owner is required')
    from retained_component_completion import validate_terminal
    need(record(done['native']['path'])==done['native'], 'Completed component report changed')
    validate_terminal(load(done['native']['path']))
    context = '''extern int64_t sceKernelGetDirectMemorySize(void);
extern int32_t sceKernelAvailableDirectMemorySize(int64_t,int64_t,size_t,int64_t*,size_t*);
static int case_retire_completed_images(int*calls){
 const uint64_t guard=UINT64_C(0x5621a7865621a786);
 struct Capacity {uint64_t pre[2];int64_t start;size_t available;uint64_t post[2];};
 struct Capacity v[2]={{{guard,guard},-1,0,{guard,guard}},{{guard,guard},-1,0,{guard,guard}}};
 const int64_t total=sceKernelGetDirectMemorySize();++*calls;
 if(total!=INT64_C(12280922112))return 0;
 for(unsigned i=0;i<2;++i){
  int rc=sceKernelAvailableDirectMemorySize(0,total,65536,&v[i].start,&v[i].available);++*calls;
  if(rc||v[i].pre[0]!=guard||v[i].pre[1]!=guard||v[i].post[0]!=guard||v[i].post[1]!=guard||
     v[i].start<0||v[i].start>total||v[i].available>(uint64_t)(total-v[i].start)||v[i].available<UINT64_C(12184453120))return 0;
 }
 return report("RETAINED_COMPONENT_CAPACITY total=%lld first=%llu last=%llu baseline=12184453120 canaries_exact=1 allocations=0 mappings=0 GPU_calls=0",
  (long long)total,(unsigned long long)v[0].available,(unsigned long long)v[1].available);
}
'''
    rows=current_files(a.current); a.out.mkdir(parents=True,exist_ok=False)
    plan=build(a.workspace,a.mount_plan,rows,rows,[],'retire-completed-images',a.out/'native',completed_images_context=context)
    save(a.out/'intent.private.json',dict(closed_component=record(a.closed_component),
        individual_old_BO_release_claimed=False,allocations=0,mappings=0,GPU_calls=0,initializer_requests=0))
    if not a.execute:return
    result=execute(lan_module(),plan,a.out/'native',60)
    raw=Path(result['raw']['path']).read_bytes()
    match=re.search(rb'RETAINED_COMPONENT_CAPACITY total=(\d+) first=(\d+) last=(\d+) baseline=12184453120 canaries_exact=1',raw)
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'] and match and
         min(int(match[2]),int(match[3]))>=12184453120,'Fresh positive capacity and retired CPU helper required')
    proof=dict(completed=True,native=result,closed_component=record(a.closed_component),
        Direct_total_bytes=int(match[1]),available_first=int(match[2]),available_last=int(match[3]),baseline_bytes=12184453120,
        canaries_exact=True,individual_old_BO_release_claimed=False,current_seven_unchanged=True,GPU_calls=0,allocations=0,mappings=0)
    save(a.out/'result.private.json',proof)
    state['GPU_retirement_readmission_pending']=False
    state['retained_component_fresh_capacity']=record(a.out/'result.private.json')
    state_path.write_text(__import__('json').dumps(state,indent=2)+'\n')
    print(dict(completed=True,available_first=proof['available_first'],available_last=proof['available_last'],GPU_calls=0))


if __name__=='__main__':main()

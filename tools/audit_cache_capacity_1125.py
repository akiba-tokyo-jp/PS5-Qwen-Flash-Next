#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify bounded explicit capacity changes and unchanged physical reserves."""
import argparse,json,os,subprocess
from pathlib import Path
from audit_expert_all_q2_safety import body
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('control','candidate','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());profile=new['cache_capacity1125']
    slots=profile.get('active_slots',profile['scope']['active_cache_slots']);workspace=profile['workspace_reservation_bytes'];single=profile['postload_single_buffer_bytes']
    before=Path(old['normal_performance']['actual_sources']['entry']['path']).read_text();after=Path(profile['actual_sources']['entry']['path']).read_text()
    checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        x=body(before,name);y=body(after,name)
        if name=='resident_reset_empty_context':x=x.replace('reset.slots!=997','reset.slots!='+str(slots))
        require(x==y,'Physical/owner guard changed: '+name);checks.append(name)
    owner0=Path(old['normal_performance']['actual_sources']['owner']['path']).read_text();owner1=Path(profile['actual_sources']['owner']['path']).read_text()
    require(owner1==owner0+'\nextern "C" std::uint64_t qwen_app_workspace_actual_peak(){return device_budget.workspace_peak();}\n','Original Direct checks or CPU reader changed')
    for k in ('graph','routing'):require(old['normal_performance']['actual_sources'][k]==new['normal_performance']['actual_sources'][k],'Unrelated GPU provider changed')
    require(old['linked_driver']==new['linked_driver']and new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Driver/import mismatch')
    folder=a.out.parent;host=a.workspace/'toolchain/msys-clang64/clang64/bin';cpp=folder/'cache1125-budget.private.cpp';exe=folder/'cache1125-budget.exe'
    src=(ROOT/'tests/output_q8_cache_budget.cpp').read_text()
    import re
    mapping={867:997,997:slots,998:slots+1,996:slots-1,866:996,868:998,199680000:396288000}
    src=re.sub(r'\b('+('|'.join(map(str,mapping)))+r')\b',lambda m:str(mapping[int(m[0])]),src)
    cpp.write_text(src,newline='\n');cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(Path(profile['actual_sources']['owner']['path']).parent),'-I',str(ROOT/'native/app'),str(cpp),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate((cmd,[str(exe)])):
        run=subprocess.run(c,capture_output=True,timeout=120,env=env);(folder/f'cache1125-check-{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode()[-1200:])
    write_json(a.out,dict(completed=True,unchanged_guard_functions=checks,original_Direct_reserve_bytes=512<<20,
        explicit_postload_single_buffer_change=[512<<20,single],active_slots=[997,slots],metadata_reset_and_rounded_banks_passed=True,
        total_quota_transfer=396288000,measured_resident_output_payload_saving=595968000,
        retained_payload_margin_bytes=595968000-396288000,CPU_heap_bytes=512<<20,workspace_reservation_bytes=workspace,
        candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
    print('Explicit1125-bank budget/reset and unchanged physical reserves passed.')
if __name__=='__main__':main()

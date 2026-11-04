#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind a kernel fault backtrace to the actual pre-dispatch node-cap assertion."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess

from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load, need, save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','case','kernel-snapshot','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--record-known-barrier',action='store_true')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    case=load(a.case/'plan.private.json');first=load(a.case/'observed-first.private.json')
    restored=load(a.case/'process-exited-restoration/result.private.json')
    snapshot=load(a.kernel_snapshot);state=load(a.current/'active-console.private.json')
    need(snapshot['completed'] and snapshot['current_boot']==state['current_boot'] and
         record(snapshot['archive']['path'])==snapshot['archive'] and restored['completed'] and
         restored['exited_PID']==first['pid'] and restored['exact_current_seven_restored_and_native_hashed'] and
         first['run_id']==case['run_id'] and first['candidate_SELF_sha256']==case['SELF']['sha256'],
         'The same-boot kernel snapshot and exact exited/restored case are required')
    package=load(case['package']['path']);linked=load(package['relink']['path'])
    need(record(case['package']['path'])==case['package'] and
         record(package['relink']['path'])==package['relink'] and
         record(linked['artifact']['path'])==linked['artifact'] and
         record(linked['source']['path'])==linked['source'],'Actual exited inputs must remain exact')
    e=ELF(Path(linked['artifact']['path']))
    graph='_ZL29ggml_backend_vk_graph_computeP12ggml_backendP11ggml_cgraph'
    f=e.symbol_data(graph);start=e.symbols[graph]['value']
    # The sole call before the conditional assertion is steady_clock::now.
    prefix=bytes.fromhex('554889e54157415641554154534881ecb8020000488975c04889fb448b7604440fb63de17c6e0167e8f3176200410fb6cf488d15085e6e01488985a8fdffff48ff04ca4c0174ca2048898da0fdffff488b8390000000488945c84c8b6818')
    need(f[:94]==prefix and f[94:104]==bytes.fromhex('4183bdf4030000010f85'),
         'The actual graph prefix must contain only clock/counter work before the saved==1 comparison')
    branch=start+108+struct.unpack_from('<i',f,104)[0]
    assertion=f[branch-start:branch-start+34]
    need(assertion[:3]==bytes.fromhex('488d3d') and assertion[7:10]==bytes.fromhex('488d15') and
         assertion[14:17]==bytes.fromhex('488d0d') and assertion[21:26]==bytes.fromhex('be6d380000') and
         assertion[26:30]==bytes.fromhex('31c067e8') and
         branch+34+struct.unpack_from('<i',assertion,30)[0]==e.symbols['ggml_abort']['value'],
         'The failed branch must directly call the actual GGML abort at line14445')
    predicate=branch+21+struct.unpack_from('<i',assertion,17)[0]
    def string(address):
        for s in e.sections:
            if s[1]!=8 and s[3]<=address<s[3]+s[5]:
                return e.data[s[4]+address-s[3]:].split(b'\0',1)[0].decode()
        raise ValueError('File-backed predicate required')
    need(string(predicate)=='saved==1','The exact failed assertion is required')
    kernel=Path(snapshot['archive']['path']).read_bytes().replace(b'\0',b'').decode(errors='replace')
    pid=first['pid'];fault=re.search(r'PPRBUG-22859: the process pid='+str(pid)+r' directly issued a syscall 2 at (0x[0-9a-f]+)(.*?)# dynamic libraries:',kernel,re.S)
    need(fault is not None and '# proc ID: '+str(pid) in fault[2] and
         'SYSTEM_ILLEGAL_FUNCTION_CALL' in fault[2],'Exact PID and forbidden-fork exception required')
    need(e.symbol_data('fork')==bytes.fromhex('48c7c0020000004989ca0f05c3c3'),'Actual forbidden fork stub required')
    bias=int(fault[1],16)-e.symbols['fork']['value']-12
    need(bias==0x400000 and '# rip: '+format(int(fault[1],16),'016x') in fault[2],
         'Kernel RIP must identify the actual fork instruction and application load bias')
    frames=[int(v,16)-bias for v in re.findall(r'^# ([0-9a-f]{16})$',fault[2],re.M)]
    need(len(frames)>=3 and frames[1]==branch+34 and
         e.symbols['ggml_abort']['value']<=frames[0]<e.symbols['ggml_abort']['value']+e.symbols['ggml_abort']['size'] and
         e.symbols['ggml_backend_graph_compute']['value']<=frames[2]<e.symbols['ggml_backend_graph_compute']['value']+e.symbols['ggml_backend_graph_compute']['size'],
         'The live backtrace must pass from the actual graph assertion through abort to fork')
    stages_path=a.case/'observed-stages.private.log';stages=stages_path.read_text().splitlines()
    need(stages[-4:]==['native_driver_before_positive_device_idle','native_driver_device_idle_completed',
        'native_driver_checkpoint_completed_producer_retained','IQ2_Down_GGML_graph_before_native_call'],
        'Positive drained backend/checkpoint immediately before the failed first graph is required')
    source=Path(linked['source']['path']).read_text()
    need('ggml_backend_synchronize(fixture_backend);qwen_native_driver_checkpoint();\n    native_guard(31);qwen_native_stage("IQ2_Down_GGML_graph_before_native_call");' in source and
         'GGML_VK_MAX_NODES_PER_SUBMIT' not in source,'Exact missing-environment first-graph fixture required')
    objdump=a.workspace/'toolchain/fast/llvm-mingw-20261006-ucrt-x86_64/bin/llvm-objdump.exe'
    for name,lo,hi in (('graph-prefix',start,start+108),('assertion',branch,branch+34)):
        raw=subprocess.check_output([str(objdump),'-d','--no-show-raw-insn','--start-address='+hex(lo),
            '--stop-address='+hex(hi),linked['artifact']['path']]);(a.out/(name+'.private.asm')).write_bytes(raw)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         state['unknown_completion'] and state['GPU_retirement_readmission_pending'] and
         state['active_successful_native_case']['run_id']==case['run_id'],'Exact restored pending owner required')
    save(a.out/'result.private.json',dict(completed=True,case=record(a.case/'plan.private.json'),
        kernel_snapshot=record(a.kernel_snapshot),actual_ELF=linked['artifact'],source=linked['source'],
        stages=record(stages_path),restoration=record(a.case/'process-exited-restoration/result.private.json'),
        package=case['package'],current_boot=state['current_boot'],run_id=case['run_id'],PID=pid,
        process_exit_cause_proved=True,failed_assertion='saved==1',source_bound_node_cap_barrier=True,
        actual_CPU_prefix_only_clock_and_counters=True,post_checkpoint_queue_submissions=0,
        prior_backend_synchronization_and_driver_checkpoint_positive=True,
        all_preexisting_submitted_work_completed_at_prior_checkpoint=True,
        only_capacity_CPU_readmission_permitted=True,GPU_execution_permitted=False,
        BO_retirement_claimed=False,ordinary_exit_claimed=False,overall_zero_submissions_claimed=False,
        fresh_changed_CPU_startup_required=True,PS5_operations=0))
    if a.record_known_barrier:
        state.update(state='kernel_bound_node_cap_assertion_current_restored_capacity_pending',unknown_completion=False)
        state['source_classified_node_cap_barrier']=record(a.out/'result.private.json')
        (a.current/'active-console.private.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(dict(completed=True,process_exit_cause='pre-dispatch saved==1 assertion then forbidden fork',CPU_capacity_only=True,PS5_operations=0)))


if __name__=='__main__':main()

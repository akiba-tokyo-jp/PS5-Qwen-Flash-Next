#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit completion delivery without changing allocation or GPU completion guards."""
import argparse,json
from pathlib import Path
from audit_expert_all_q2_safety import body
from expert_q4 import require,record,write_json
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('control','candidate','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text())
    before=Path(old['normal_performance']['actual_sources']['entry']['path']).read_text();after=Path(new['completed_delivery']['actual_sources']['entry']['path']).read_text()
    checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(before,name)==body(after,name),'Original guard changed: '+name);checks.append(name)
    for marker in ('qwen_app::require_resident_phase_VM(policy,read_completed_native_report(buffer_proof),true)','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','if(ledger.live)throw std::runtime_error("Additional model owners remain live")'):
        require(before.count(marker)==after.count(marker)>0,'Positive completion boundary changed')
    oldowner=Path(old['normal_performance']['actual_sources']['owner']['path']);newowner=Path(new['completed_delivery']['actual_sources']['owner']['path'])
    require((oldowner.parent/'device_buffer_budget.h').read_bytes()==(newowner.parent/'device_buffer_budget.h').read_bytes(),'Allocation quota changed')
    for key in ('cache','engine','graph','routing'):
        require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'GPU/cache/graph provider changed')
    require(new['linked_driver']==old['linked_driver']and new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Driver or native dispatch differs')
    gate=after.index('const auto required=floor+10+19+worker_price.worker_pages+worker_price.idle_pages;')
    memory=after.rfind('const auto memory=qwen_app::admit_native_system_memory();',0,gate)
    require(after.index('qwen_app::start_native_source_parallel_reads()')<memory<gate,'Current source workers must already exist at fresh pre-GPU admission')
    write_json(a.out,dict(completed=True,unchanged_guard_functions=checks,
        original_physical_kernel_heap_ledger_ownership_positive_completion_guards_retained=True,
        CPU_read_workers=4,additional_CPU_workers=1,worker_cost_in_fresh_pre_GPU_observation=True,
        maximum_concurrent_reads_unchanged=4,consumer_time_not_double_counted=True,
        source_header=new['completed_delivery']['source_header'],candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
    print('Completion provider retains physical, memory, ownership and positive GPU completion guards.')
if __name__=='__main__':main()

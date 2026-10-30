#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify bounded diagnostic timestamps without shader or model changes."""
import argparse,json
from pathlib import Path
from audit_expert_all_q2_safety import body
from build_gpu_kernel_timing import gpu_source
from expert_q4 import require,record,write_json
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('control','candidate','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());profile=new['GPU_kernel_timing']
    source=Path(profile['original_GPU_source']['path']);actual=Path(profile['actual_sources']['GPU']['path']);require(record(source)==profile['original_GPU_source']and actual.read_text()==gpu_source(source.read_text()),'Only exact bounded diagnostic changes allowed')
    before=Path(old['normal_performance']['actual_sources']['entry']['path']).read_text();after=Path(profile['actual_sources']['entry']['path']).read_text()
    names=('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context')
    for name in names:require(body(before,name)==body(after,name),'Original physical/owner guard changed')
    for key in ('owner','cache','engine','graph','routing'):require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'Unrelated inference provider changed')
    require(old['linked_driver']==new['linked_driver']and new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Driver/import mismatch')
    require(profile['per_graph_fence_timeout_ns']==5000000000 and not profile['query_result_WAIT_flag']and not profile['ordinary_speed_comparison_valid'],'Bounded diagnostic-only scope required')
    write_json(a.out,dict(completed=True,unchanged_guard_functions=list(names),original_shader_math_and_model_precision_retained=True,
        existing_driver_and_completion_ownership_retained=True,additional_timestamp_GPU_operations=True,per_graph_fence_timeout_ns=5000000000,
        unbounded_query_WAIT_disabled=True,ordinary_speed_comparison_valid=False,candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
    print('GPU timestamp diagnostic preserves shader/model/owner guards and replaces diagnostic infinite waits with finite checks.')
if __name__=='__main__':main()

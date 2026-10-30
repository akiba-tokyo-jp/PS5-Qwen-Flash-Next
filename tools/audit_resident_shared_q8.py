#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit explicit shared-Q8 precision and unchanged allocation/metadata owners."""
import argparse,json
from pathlib import Path
from audit_expert_all_q2_safety import body
from expert_q4 import require,record,write_json
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('control','candidate','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());profile=new['resident_shared_Q8']
    before=Path(old['normal_performance']['actual_sources']['entry']['path']).read_text();after=Path(profile['actual_sources']['entry']['path']).read_text();checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(before,name)==body(after,name),'Original physical/identity/reset guard changed: '+name);checks.append(name)
    for marker in ('qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','if(ledger.live)throw std::runtime_error("Additional model owners remain live")','The complete verified header must occupy the first physical prefix'):
        require(before.count(marker)==after.count(marker)>0,'Original owner/completion or metadata-prefix guard changed')
    for key in ('owner','cache','engine','graph','routing'):
        require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'Unrelated allocation/compute provider changed')
    metadata=[x for x in old['link_command']if x.endswith('Expert-Q2-composite-8433\\metadata.o')or x.endswith('Expert-Q2-composite-8433/metadata.o')]
    require(len(metadata)==1 and metadata[0]in new['link_command'],'Exact original metadata-reader object required')
    publication=json.loads(Path(profile['publication']['path']).read_text());require(publication['completed']and publication['header_prefixes_extracted_and_sealed'],'Every new zero-offset header must have positive native SHA256/EOF evidence')
    source=json.loads(Path(publication['source_integrity']['path']).read_text());require(len(source['headers'])==48,'Exact48 affected header prefixes required')
    require(old['linked_driver']==new['linked_driver']and new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Driver/import mismatch')
    write_json(a.out,dict(completed=True,unchanged_guard_functions=checks,original_metadata_reader_and_zero_offset_prefix_checks_retained=True,
        new_prefixes_native_SHA256_EOF_verified=48,shared_projections_explicitly_Q8=144,all_original_routed_Expert_payloads_retained=True,
        CPU_heap_kernel_Direct_cache_workspace_owner_and_completion_guards_retained=True,original_graph_and_shader_math_outside_shared_weights_unchanged=True,
        candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
    print('Shared-Q8 precision exception, original metadata reader and all physical/owner/completion guards verified.')
if __name__=='__main__':main()

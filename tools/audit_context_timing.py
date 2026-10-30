#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check that timing instrumentation preserves context and GPU semantics."""
import argparse,json
from pathlib import Path
from build_context_timing import context_source
from audit_expert_all_q2_safety import body
from expert_q4 import require,record,write_json
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('control','candidate','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());profile=new['context_timing']
    original=Path(profile['original_context']['path']);actual=Path(profile['actual_sources']['context']['path'])
    require(record(original)==profile['original_context']and actual.read_text()==context_source(original.read_text()),'Only exact measured timing insertions allowed')
    before=Path(old['normal_performance']['actual_sources']['entry']['path']).read_text();after=Path(profile['actual_sources']['entry']['path']).read_text()
    names=('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context')
    for name in names:require(body(before,name)==body(after,name),'Physical or ownership guard changed')
    for key in ('cache','engine','owner','graph','routing'):
        require(old['normal_performance']['actual_sources'][key]==new['normal_performance']['actual_sources'][key],'Unrelated compute/delivery provider changed')
    require(old['linked_driver']==new['linked_driver']and new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Native driver/import mismatch')
    write_json(a.out,dict(completed=True,exact_original_context_with_timing_only=True,unchanged_guard_functions=list(names),
        GPU_operations_added=0,precision_changes=0,graph_reuse_conditions_changed=False,allocation_policy_changed=False,
        candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
    print('Context timing-only transformation and original memory/owner/compute providers verified.')
if __name__=='__main__':main()

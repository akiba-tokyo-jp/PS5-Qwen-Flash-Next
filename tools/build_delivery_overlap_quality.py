#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare guarded GPU overlap across four independent fixed-input pairs."""
import json,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
original_link=quality.link


def paired_link(parent,out,variants,inputs):
    command,text=variants['entry'];text='extern "C" void qwen_app_overlap_select(bool);\n'+text
    text=once(text,'            const auto current_hits_before=qwen_app_current_bundle_hits();',
        '            const bool overlap_candidate=(task%2)?!repeat:repeat;qwen_app_overlap_select(overlap_candidate);\n            const auto current_hits_before=qwen_app_current_bundle_hits();')
    text=once(text,'            row["quality_task"]=task;', '            row["overlap_candidate"]=overlap_candidate;\n            row["quality_task"]=task;')
    return original_link(parent,out,dict(entry=(command,text)),[*inputs,Path(__file__)])


def main():
    quality.link=paired_link;quality.main();out=Path(sys.argv[sys.argv.index('--out')+1]);path=out/'receipt.private.json';r=json.loads(path.read_text())
    r['cold_request']['actual_sources']['entry']=r['memory_quality_cohort']['actual_sources']['entry'];r['cold_request']['commands']['entry']=r['memory_quality_cohort']['commands']['entry']
    r['overlap_quality']=dict(requests=8,fixed_tasks=4,order='control/candidate then candidate/control alternating by task',empty_cache_each_request=True,prefix_reuse=False,causal_speculation=False,full_F32_and_ordered_routes_equal_required=True,live_input_or_output_alias_refusal=True,graph_metadata_restored_only_after_positive_completion=True,no_extra_GPU_buffers=True,production_adopted=False)
    write_json(path,r);write_json(out/'core-safety.private.json',dict(completed=True,kind='guarded_GPU_overlap_fixed_pairs',driver_and_original_reserves_unchanged=True,dependent_or_aliased_work_refused=True,positive_completion_required=True,candidate=record(path),PS5_operations=0,CI_runs=0))
    print('Eight independent fixed-input requests will measure guarded shared-Expert overlap and complete F32/routes.')


if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pair four different inputs across streaming arms with complete F32 checks."""
import json,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json

original_link=quality.link
def paired_link(parent,out,variants,inputs):
    command,text=variants['entry'];text='extern "C" void qwen_app_cold_stream_select(bool);\n'+text
    marker='            const auto current_hits_before=qwen_app_current_bundle_hits();'
    text=once(text,marker,'            const bool delivery_candidate=(task%2)?!repeat:repeat;qwen_app_cold_stream_select(delivery_candidate);\n'+marker)
    marker='            row["quality_task"]=task;'
    text=once(text,marker,'            row["streaming_candidate"]=delivery_candidate;row["delivery_pair_F32_scope"]="Same width, precision, routing and empty cache; delivery differs";\n'+marker)
    variants['entry']=(command,text)
    return original_link(parent,out,variants,[*inputs,Path(__file__)])

def main():
    require('--only-task'not in sys.argv,'All four tasks required for the balanced delivery comparison')
    quality.link=paired_link;quality.main()
    out=Path(sys.argv[sys.argv.index('--out')+1]);path=out/'receipt.private.json';r=json.loads(path.read_text());require(r['memory_quality_cohort']['requests']==8,'Eight independent requests required')
    r['cold_request']['actual_sources']['entry']=r['memory_quality_cohort']['actual_sources']['entry'];r['cold_request']['commands']['entry']=r['memory_quality_cohort']['commands']['entry']
    r['cold_quality']=dict(requests=8,fixed_tasks=4,streaming_arms='A/B then B/A alternating by task',prefix_reuse=False,causal_speculation=False,empty_cache_each_request=True,
        complete_vocabulary_F32_and_ordered_routes_equal_required=True,contents_and_raw_format_recorded_separately=True,original_physical_and_completion_guards=True,production_adopted=False)
    write_json(path,r)
    write_json(out/'core-safety.private.json',dict(completed=True,kind='four_input_exact_delivery_comparison',driver_and_original_physical_reserves_preserved=True,CPU_heap_limit_bytes=512<<20,workspace_bytes=48<<20,
        source_selection_only_after_positive_idle=True,candidate=record(path),PS5_operations=0,CI_runs=0))
    print('Four different inputs paired with empty caches, reversed delivery order and complete same-arithmetic F32 checks.')
if __name__=='__main__':main()

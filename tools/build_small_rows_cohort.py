#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare scalar and batched row delivery with exact full F32 and routes."""
import json,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from finite_route_capacity import bind_route_capacity
from expert_q4 import record,write_json
ORIGINAL_LINK=quality.link
REVERSE=False

def cohort_link(parent,out,variants,inputs):
    cmd,text=variants['entry'];text=bind_route_capacity(text,8)
    text=('#include <cstdint>\nextern "C" void qwen_app_small_rows_select(bool);\n'
          'extern "C" void qwen_app_small_rows_stats(std::uint64_t*);\n')+text
    selected='!repeat' if REVERSE else 'repeat'
    text=once(text,'                resident_reset_empty_context(context,model,startup.admission_report);',
        '                qwen_app_small_rows_select('+selected+');\n'
        '                resident_reset_empty_context(context,model,startup.admission_report);')
    text=once(text,'            const auto perf=performance_snapshot(*engine);',
        '            std::uint64_t small_before[5]{};qwen_app_small_rows_stats(small_before);\n'
        '            const auto perf=performance_snapshot(*engine);')
    text=once(text,'            row["quality_task"]=task;',
        '            std::uint64_t small_after[5]{};qwen_app_small_rows_stats(small_after);'
        'Json small_delta=Json::array();for(unsigned i=0;i<5;++i)small_delta.push_back(small_after[i]-small_before[i]);'
        'row["small_rows"]={{"enabled",'+selected+'},{"delta",small_delta},{"existing_workers",4},{"extra_scratch_bytes",0}};\n'
        '            row["quality_task"]=task;')
    variants['entry']=cmd,text
    return ORIGINAL_LINK(parent,out,variants,[*inputs,Path(__file__)])

def main():
    global REVERSE
    if '--reverse' in sys.argv:REVERSE=True;sys.argv.remove('--reverse')
    quality.link=cohort_link;quality.main()
    path=Path(sys.argv[sys.argv.index('--out')+1])/'receipt.private.json'
    r=json.loads(path.read_text());q=r['memory_quality_cohort']
    for key in ('cold_request','resident_all_Q8','resident_small_rows'):
        r[key]['actual_sources'].update(q['actual_sources']);r[key]['commands'].update(q['commands'])
    r['small_rows_cohort']=dict(requests=8,fixed_tasks=4,scalar_then_batch=not REVERSE,
        exact_full_F32_routes_and_tokens_required=True,source=record(Path(__file__)),native_verification_pending=True)
    write_json(path,r)

if __name__=='__main__':main()

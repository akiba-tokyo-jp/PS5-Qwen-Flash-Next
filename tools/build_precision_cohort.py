#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build bounded fixed-task precision comparisons without broad quality claims."""
import json,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from finite_route_capacity import bind_route_capacity
from expert_q4 import require,record,write_json
ORIGINAL_LINK=quality.link

def bounded_link(parent,out,variants,inputs):
    cmd,text=variants['entry'];variants['entry']=cmd,bind_route_capacity(text,8)
    return ORIGINAL_LINK(parent,out,variants,[*inputs,Path(__file__)])

def main():
    require('--only-task'not in sys.argv,'All four fixed tasks required')
    quality.link=bounded_link;quality.main()
    path=Path(sys.argv[sys.argv.index('--out')+1])/'receipt.private.json';r=json.loads(path.read_text())
    q=r['memory_quality_cohort']
    for key in ('cold_request','resident_all_Q8','precision_candidate'):
        r[key]['actual_sources'].update(q['actual_sources']);r[key]['commands'].update(q['commands'])
    r['precision_quality']=dict(mode=r['precision_candidate']['scope']['mode'],requests=8,fixed_tasks=4,
        same_profile_full_F32_and_routes_required=True,cross_precision_logit_equality_required=False,
        raw_format_failures_recorded_without_aborting=True,source=record(Path(__file__)),native_verification_pending=True)
    write_json(path,r)

if __name__=='__main__':main()

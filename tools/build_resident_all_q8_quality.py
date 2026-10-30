#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify four fixed tasks with bounded same-resident-Q8 repeat evidence."""
import json
import sys
from pathlib import Path
import build_memory_quality_cohort as quality
from finite_route_capacity import bind_route_capacity
from expert_q4 import require, record, write_json

original_link=quality.link


def bounded_link(parent,out,variants,inputs):
    command,text=variants['entry']
    variants['entry']=(command,bind_route_capacity(text,8))
    return original_link(parent,out,variants,[*inputs,Path(__file__)])


def main():
    require('--only-task' not in sys.argv,'All four fixed tasks required')
    quality.link=bounded_link;quality.main()
    out=Path(sys.argv[sys.argv.index('--out')+1]);path=out/'receipt.private.json';r=json.loads(path.read_text())
    q=r['memory_quality_cohort'];require(q['requests']==8 and r['resident_all_Q8']['scope']['PLE_convolution_BF16_preserved'],'Exact eight-request Q8/BF16-PLE scope required')
    for key in ('cold_request','resident_all_Q8'):
        r[key]['actual_sources'].update(q['actual_sources']);r[key]['commands'].update(q['commands'])
    r['resident_all_Q8_quality']=dict(requests=8,fixed_tasks=4,same_profile_F32_and_routes_required=True,
        cross_precision_logit_equality_required=False,raw_format_failures_recorded_without_aborting=True,
        PLE_convolution_BF16_preserved=True,Expert_Q2_preserved=True,source=record(Path(__file__)),native_verification_pending=True)
    write_json(path,r)


if __name__=='__main__':main()

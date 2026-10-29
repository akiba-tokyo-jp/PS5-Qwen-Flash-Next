#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile closed same-model ABBA and the two independently counted IO lanes."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record
from analyze_expert_q2_measurements import decode_phase
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 t=json.loads((a.case/'native-model-terminal.private.json').read_text());require(t['completed_policy_comparison']and [r['expert_eviction_policy']for r in t['requests']]==['aged_lfu','aged_lfu','two_touch_probation','two_touch_probation','aged_lfu'],'Complete declared same-model ABBA required')
 control=decode_phase(a.case,{1,4});candidate=decode_phase(a.case,{2,3})
 pooled=lambda value:sum(r['accepted_decode_transitions']for r in value['requests'])/sum(r['decode_s']for r in value['requests'])
 before,after=pooled(control),pooled(candidate);requests=t['requests'];rows=[]
 for q in requests:
  path=a.case/f"native-arm{q['ordinal']}.routes.private.json";r=json.loads(path.read_text());require(r['complete']and r['pid']==t['pid']and r['run_id']==t['run_id'],'Complete matching native routes required')
  rows.append(dict(ordinal=q['ordinal'],policy=q['expert_eviction_policy'],decode_tok_s=q['metrics']['decode_tokens_per_second'],cache_misses=r['cache_misses'],cache_hits=r['cache_hits'],maximum_absolute_logit_error=q['maximum_absolute_logit_error']))
 report=dict(schema='ps5-qwen-Q2-policy-ABBA-result-v1',completed=True,case=int(a.case.name.rsplit('-',1)[1]),requests=rows,
  control=control,candidate=candidate,control_decode_tok_s=before,candidate_decode_tok_s=after,decode_speedup_fraction=after/before-1,
  every_candidate_faster_than_every_control=min(r['decode_tok_s']for r in rows if r['ordinal']in(2,3))>max(r['decode_tok_s']for r in rows if r['ordinal']in(1,4)),
  full_F32_rows_and_routes_identical=t['full_F32_continuation_and_routes_passed']and max(r['maximum_absolute_logit_error']for r in rows)==0,
  actual_cache_slots=t['active_cache_slots'],native_normal_close_and_exact_control_restoration=True,production_adopted=False,
  original_model_format_and_GPU_math_unchanged=True,baseline_exact_Q2_IO_measurement=control,CI_runs=0,
  evidence=[record(a.case/n)for n in ['native-model-terminal.private.json','restored-complete.private.json','IO-token-snapshots/complete.private.json']])
 require(report['full_F32_rows_and_routes_identical']and report['actual_cache_slots']==867,'Same-format arithmetic and fixed capacity required')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items()if k not in ('control','candidate','baseline_exact_Q2_IO_measurement','evidence')},indent=2))
 print(json.dumps(dict(control_IO={k:v for k,v in control.items()if k not in ('requests','individual_read_size_classes')},candidate_IO={k:v for k,v in candidate.items()if k not in ('requests','individual_read_size_classes')}),indent=2))
if __name__=='__main__':main()

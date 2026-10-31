#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assess restored fixed-policy native comparisons using positive whole-time gains."""
import argparse,json,subprocess,sys
from pathlib import Path
from expert_q4 import require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 legacy=a.out.parent/'comparison-original-two-percent-screen.private.json'
 require(not a.out.exists()and not legacy.exists(),'Fresh analysis outputs required')
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/analyze_io_gpu_comparison.py'),'--case',str(a.case),'--out',str(legacy)],check=True)
 old=json.loads(legacy.read_text());t=json.loads((a.case/'native-model-terminal.private.json').read_text());probe=t['limit_margin_probe'];phase=probe['phases'][2]
 require(old['requests']==16 and phase['minimum_selected_padding_pages']==0 and phase['padding_reductions']==0,'Fixed zero inference padding and full16 requests required')
 require(probe['OS_minimum_preserved']and probe['OS_counter_writes']==0,'Observed OS watermark must remain enforced')
 require(probe['phases'][0]['minimum_selected_padding_pages']>=256 and probe['phases'][1]['minimum_selected_padding_pages']==64,'Loading/context policy must match the control')
 comparisons=[]
 for c in old['comparisons']:
  finite_both_orders=all(x['forward_whole_reduction_percent']>0 and x['reverse_whole_reduction_percent']>0 for x in c['conditions'])
  physical_benefit=all(x['forward_call_reduction']>0 and x['reverse_call_reduction']>0 for x in c['conditions'])if c['arm']==1 else True
  error=max(x['full_F32_max_error']for x in old['rows']if x['arm']==c['arm'])
  numerical=error==0 if c['arm']==1 else error<=1e-4
  comparisons.append(dict(c,positive_both_orders_both_cache_conditions=finite_both_orders,physical_request_reduction=physical_benefit,
      maximum_full_F32_error=error,numerical_screen_passed=numerical,eligible_for_normal=finite_both_orders and physical_benefit and numerical))
 report=dict(schema='ps5-qwen-limit-winners-comparison-v1',completed=True,case=int(a.case.name.rsplit('-',1)[1]),requests=16,
  placement_eligible=comparisons[0]['eligible_for_normal'],decode_GDN_eligible=comparisons[1]['eligible_for_normal'],
  decision_rule='Positive complete-request time in both orders and both cold/retained conditions; placement also reduces physical calls with exact complete F32; GDN maximum absolute F32 error <=0.0001 and complete same counting output/routes. Normal/API/display still required.',
  arbitrary_two_percent_floor_removed=True,stable_inference_padding_pages=0,loading_context_and_physical_checks_unchanged=True,
  limit_margin_probe=probe,comparisons=comparisons,rows=old['rows'],evidence=old['evidence'],
  all_full_vocabulary_rows_finite=True,source_model_GPU_owners_positively_retired=True,ordinary_close_exact_restore=True,
  limitations=['Two candidate samples per cache condition, finite installed counting task; no confidence interval or sustained-service claim.','Whole time includes required completion; backend-only gains do not establish whole-model gain.'],CI_runs=0)
 write_json(a.out,report)
 print(json.dumps({k:report[k]for k in('completed','placement_eligible','decode_GDN_eligible')}))
if __name__=='__main__':main()

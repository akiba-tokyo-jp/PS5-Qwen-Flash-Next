#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise adoption refusal controls against a real normal/placement snapshot."""
import argparse,copy,json
from pathlib import Path
from next_five_production import require_next_five_production

def check(installation,context,report):
 require_next_five_production(installation,context,report)
 mutations=[('wrong_SELF',0,('application_SELF','sha256'),'0'*64),('wrong_model',0,('model_receipt_SHA256',),'0'*64),('wrong_cache',0,('active_expert_slots',),3072),('live_owner',1,('native_running',),True),('wrong_GPU_object',2,('application_relink','original_GPU_object_SHA256'),'0'*64),('missing_retirement',2,('normal','source_model_GPU_owners_positively_retired'),False),('over_CPU_budget',2,('normal','CPU_heap_peak_bytes'),536870913),('missing_control',1,('previous_production_SELF','sha256'),'0'*64)]
 if report['next_five_policy'].get('expanded_placement_only_first_request'):mutations.append(('large_layout_during_decode',2,('normal','large_bundle_high_index_decode_hits_total'),1))
 passed=[]
 for name,index,keys,value in mutations:
  parts=copy.deepcopy([installation,context,report]);target=parts[index]
  for key in keys[:-1]:target=target[key]
  target[keys[-1]]=value
  try:require_next_five_production(*parts)
  except ValueError:passed.append(name)
  else:raise AssertionError('Unsafe proposal accepted: '+name)
 return dict(completed=True,positive_selection_passed=True,expected_refusals=len(passed),refusals=passed,PS5_operations=0,CI_runs=0)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('installation','context','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();print(json.dumps(check(*[json.loads(getattr(a,k).read_text())for k in ('installation','context','report')])))
if __name__=='__main__':main()

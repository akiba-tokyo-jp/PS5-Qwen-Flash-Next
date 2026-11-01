#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject invalid program, source, geometry, completion and execution proposals."""
import argparse,copy,json
from pathlib import Path
from load_followup_production import require_load_followup_production
def check(installation,context,report):
 require_load_followup_production(installation,context,report)
 variants=[('wrong_program',0,('application_SELF','sha256'),'0'*64),('wrong_model',0,('model_receipt_SHA256',),'0'*64),('wrong_cache',0,('active_expert_slots',),3072),('lost_control',1,('previous_production_SELF','sha256'),'0'*64),('live_owner',1,('native_running',),True),('missing_finite_proof',2,('normal','all_full_vocabulary_rows_finite'),False),('missing_native_frames',2,('normal','actual_native_frames_viewed'),0),('wrong_GPU_provider',2,('application_relink','GPU_object_SHA256'),'0'*64),('old_node_policy',2,('next_five_policy','submission_node_cap'),16),('missing_seal_reuse',2,('normal','prior_native_pack_seals_reused'),0),('below_OS_minimum',2,('normal','limit_margin_probe','phases',0,'minimum_free_pages'),897),('missing_plan_stage',2,('dispositions',0,'verification_stage_completed'),False),('incomplete_placement',2,('placement','verification_files'),11),('GPU_diagnostics_in_production',2,('next_five_policy','GPU_timestamp_diagnostics_enabled'),True),('missing_CPU_rows',2,('normal','CPU_nested_by_request'),[]),('unretired_query_pool',2,('GPU_range_validation','query_pools_destroyed'),0),('missing_API_publication',2,('normal','CPU_nested_by_request',1,30),0),('inexact_CPU_partition',2,('normal','CPU_nested_by_request',1,40),1)]
 refused=[]
 for name,index,keys,value in variants:
  parts=copy.deepcopy([installation,context,report]);target=parts[index]
  for k in keys[:-1]:target=target[k]
  target[keys[-1]]=value
  try:require_load_followup_production(*parts)
  except ValueError:refused.append(name)
  else:raise AssertionError('Invalid selection accepted: '+name)
 return dict(completed=True,positive_selection_passed=True,expected_refusals=len(refused),refusals=refused,PS5_operations=0,CI_runs=0)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('installation','context','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();print(json.dumps(check(*[json.loads(getattr(a,k).read_text())for k in('installation','context','report')])))
if __name__=='__main__':main()

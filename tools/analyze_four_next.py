#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Grade the four finite native comparisons without conflating their scopes."""
import argparse,json,statistics as st
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
GROUPS={'control_cold':[2,8],'candidate_cold':[4,6],'control_retained':[3,9],'candidate_retained':[5,7]}
def completed(cache,case,model):
 p=cache/f'hardware-first-generation-{case}';r=json.loads((p/'native-model-terminal.private.json').read_text());closed=json.loads((p/'restored-complete.private.json').read_text())
 require(r['completed']and r['device_ledger_live_bytes']==0 and r['all_model_source_device_owners_positively_retired']and closed['completed']and not closed['unknown_completion'],'Positive native completion and ordinary close/exact restoration required')
 if model:
  require(len(r['requests'])==14 and all(v['full_F32_finite']for v in r['requests']),'Fourteen full finite requests required');require(json.loads((p/'candidate-contents-decision.private.json').read_text())['all_contents_passed'],'All actual semantic tasks must pass')
 return p,r
def model_result(p,r):
 rows=r['requests'];groups={}
 for name,ids in GROUPS.items():
  groups[name]=dict(ordinals=ids,metrics={k:st.mean(rows[i]['metrics'][k]for i in ids)for k in ('decode_tokens_per_second','total_ms','TTFT_ms')},source={k:st.mean(rows[i]['completed_performance']['delta'][k]for i in ids)for k in ('source_physical_read_calls','source_physical_read_bytes','source_read_ns')})
 aa=abs(rows[3]['metrics']['decode_tokens_per_second']-rows[9]['metrics']['decode_tokens_per_second']);retained=groups['candidate_retained']['metrics']['decode_tokens_per_second']-groups['control_retained']['metrics']['decode_tokens_per_second']
 both=all(rows[b]['metrics']['decode_tokens_per_second']>rows[a]['metrics']['decode_tokens_per_second']and rows[b]['metrics']['total_ms']<rows[a]['metrics']['total_ms']for a,b in ((3,5),(9,7)))
 cold_spread=abs(rows[2]['metrics']['total_ms']-rows[8]['metrics']['total_ms']);cold_ok=groups['candidate_cold']['metrics']['total_ms']<=groups['control_cold']['metrics']['total_ms']+cold_spread
 return dict(case=int(p.name.rsplit('-',1)[1]),requests=14,groups=groups,retained_decode_gain_percent=100*retained/groups['control_retained']['metrics']['decode_tokens_per_second'],retained_both_temporal_directions_faster=both,retained_control_AA_spread=aa,retained_gain_exceeds_AA_spread=retained>aa,cold_whole_nonregressing_within_AA=cold_ok,eligible=both and retained>aa and cold_ok,
  all_fixed_semantic_tasks_passed=True,compared_counting_top1_agreement=[v.get('quality_distribution',{}).get('top1_agreement')for v in rows[2:10]],maximum_compared_logit_error=max(v['maximum_absolute_logit_error']for v in rows[2:10]),device_ledger_peak_bytes=r['device_ledger_peak_bytes'],positive_retirement_and_exact_restore=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--gate-case',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();proofs=[];out={}
 for name,case in [('placement',17300),('two_token',17700),('rollback',17600)]:
  root,r=completed(a.cache,case,True);out[name]=model_result(root,r);proofs.extend([record(root/'native-model-terminal.private.json'),record(root/'restored-complete.private.json'),record(root/'candidate-contents-decision.private.json')])
  if name=='placement':require(all(v['maximum_absolute_logit_error']==0 and v['complete_model_checkpoint']['ordered_routes_exact']for v in r['requests'][2:10]),'Placement must preserve every compared F32 byte and ordered route')
  if name=='two_token':require(all((v['two_token_pipeline_selections']>0 if v['candidate_arm']==1 else v['two_token_pipeline_selections']==0)for v in r['requests']),'Actual two-token fusion selection required')
  if name=='rollback':
   last=r['requests'][-1]['compact_rollback'];out[name]['complete_captures_elided']=last['complete_captures_elided'];out[name]['all_memory_rollbacks']=last['all_memory_rollbacks'];out[name]['additional_application_state_allowance_bytes']=124<<20
   require(last['all_memory_rollbacks']==15 and last['complete_captures_elided']==35,'All declared compact accepted/rejected paths required');require(all(not any(v['complete_model_checkpoint']['counter_delta'])for v in r['requests']if v['candidate_arm']==1),'No candidate complete-state copies permitted')
 root,g=completed(a.cache,a.gate_case,False);require(g['GPU_graphs']==108 and g['all_F64_outputs_passed']and len(g['cases'])==3,'Complete actual-Q2 F64 Gate/Up fixture required');gate=[]
 for row in g['cases']:
  arms=row['arms'];control=st.mean(arms[i]['backend_samples_us'][j]for i in (0,3)for j in range(8));candidate=st.mean(arms[i]['backend_samples_us'][j]for i in (1,2)for j in range(8));aa=abs(st.mean(arms[0]['backend_samples_us'])-st.mean(arms[3]['backend_samples_us']))
  gate.append(dict(tokens=row['tokens'],control_backend_us=control,candidate_backend_us=candidate,control_AA_spread_us=aa,backend_gain_percent=100*(control-candidate)/control,both_temporal_directions_faster=all(st.mean(arms[b]['backend_samples_us'])<st.mean(arms[c]['backend_samples_us'])for c,b in((0,1),(3,2))),candidate_pipeline_selections=row['candidate_pipeline_selections'],maximum_F64_error=row['maximum_absolute_error']))
 gate_eligible=all(x['both_temporal_directions_faster']and x['control_backend_us']-x['candidate_backend_us']>x['control_AA_spread_us']for x in gate[:2]);out['gate_up']=dict(case=a.gate_case,GPU_graphs=108,cases=gate,all_F64_outputs_and_canaries_passed=True,actual_encoded_Expert_samples=3,selected_IDs=6,sample_IDs_repeat=True,whole_model_speedup_measured=False,kernel_eligible=gate_eligible,disposition='requires_actual_model_comparison'if gate_eligible else'tested_prototype_not_adopted_no_reproducible_kernel_gain')
 proofs.extend([record(root/'native-model-terminal.private.json'),record(root/'restored-complete.private.json')]);out.update(schema='ps5-qwen-four-next-candidates-v1',candidate_comparisons_completed=not gate_eligible,normal_qualification_pending=True,production_placement_pending=True,source_wait_is_not_raw_SSD_service=True,whole_request_bytes_are_not_decode_GB_per_token=True,no_unlike_model_comparisons=True,no_arbitrary_percentage_floor=True,source_evidence=proofs,CI_runs=0,reboots=0,agents=0)
 write_json(a.out,out);print(json.dumps({k:out[k].get('eligible',out[k].get('disposition'))for k in ('placement','two_token','rollback','gate_up')}))
if __name__=='__main__':main()

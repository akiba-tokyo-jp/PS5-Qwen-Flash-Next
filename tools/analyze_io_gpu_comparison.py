#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile the finite I/O/GDN comparison without new console operations."""
import argparse,json,hashlib,math
from pathlib import Path
def load(p):return json.loads(Path(p).read_text())
def need(v,m):
 if not v:raise ValueError(m)
def evidence(p):
 p=Path(p);return dict(label=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();t=load(a.case/'native-model-terminal.private.json');closed=load(a.case/'restored-complete.private.json')
 count=len(t.get('requests',[]));protocols={10:([0,0,1,1,0],[('bundles',1,1,2,3,4)]),16:([0,0,1,1,0,2,2,0],[('bundles',1,1,2,3,4),('GDN',2,4,5,6,7)])}
 need(count in protocols,'Only the declared ten- or sixteen-request protocol is supported')
 order,arms=protocols[count]
 need(t['completed']and t['all_model_source_device_owners_positively_retired']and t['device_ledger_live_bytes']==0,'All declared requests and positive resource retirement required')
 need(closed['completed']and not closed['unknown_completion']and closed['CPU_title_normally_closed'],'Ordinary close and exact restoration required')
 rows=[]
 for i,r in enumerate(t['requests']):
  trace=load(a.case/f'native-arm{i}.routes.private.json');d=r['completed_performance']['delta'];reads=r['cold_request_timing']['read_latency_delta'];m=r['metrics'];arm=r['candidate_arm'];selections=r['GDN_candidate_pipeline_selections']
  need(arm==order[i//2],'The actual arm order must match the predeclared comparison')
  need(r['full_F32_finite']and r['request_reset_completed']and r['counting_quality_passed']and r['same_tokens_as_independent']and m['generated_tokens']==22,'Exact counting output and complete finite request required')
  need(trace['complete']and trace['uploaded_bytes']==trace['cache_misses']*1536000 and trace['layers_per_process']==48,'Complete actual routes and original Q2 byte geometry required')
  need(reads[0]==d['source_physical_read_calls']and reads[1]==d['source_physical_read_bytes']and reads[3]==0,'All physical reads must reconcile without errors')
  need((selections>0)==(arm==2),'GDN candidate must actually execute only in its declared arm')
  need(arm==2 or r['maximum_absolute_logit_error']==0,'Unchanged weight-byte placement requires exact full-vocabulary rows')
  rows.append(dict(ordinal=i,pair=i//2,arm=arm,weights_retained=bool(i%2),metrics=m,physical_calls=reads[0],physical_bytes=reads[1],Expert_misses=trace['cache_misses'],source_wait_s=d['source_read_ns']/1e9,model_other_s=(d['process_ns']-d['source_read_ns'])/1e9,request_other_s=m['total_ms']/1e3-d['process_ns']/1e9,GDN_pipeline_selections=selections,full_F32_max_error=r['maximum_absolute_logit_error']))
 comparisons=[]
 for name,arm,left,first,second,right in arms:
  conditions=[]
  for retained in (False,True):
   k=int(retained);before=rows[left*2+k];b=rows[first*2+k];c=rows[second*2+k];after=rows[right*2+k]
   conditions.append(dict(weights_retained=retained,forward_whole_reduction_percent=100*(1-b['metrics']['total_ms']/before['metrics']['total_ms']),reverse_whole_reduction_percent=100*(1-c['metrics']['total_ms']/after['metrics']['total_ms']),forward_call_reduction=before['physical_calls']-b['physical_calls'],reverse_call_reduction=after['physical_calls']-c['physical_calls'],forward_byte_reduction=before['physical_bytes']-b['physical_bytes'],reverse_byte_reduction=after['physical_bytes']-c['physical_bytes'],forward_source_wait_reduction_s=before['source_wait_s']-b['source_wait_s'],reverse_source_wait_reduction_s=after['source_wait_s']-c['source_wait_s'],control_mean_total_ms=(before['metrics']['total_ms']+after['metrics']['total_ms'])/2,candidate_mean_total_ms=(b['metrics']['total_ms']+c['metrics']['total_ms'])/2,candidate_mean_decode_tok_s=(b['metrics']['decode_tokens_per_second']+c['metrics']['decode_tokens_per_second'])/2))
  cold,retained=conditions;eligible=min(retained['forward_whole_reduction_percent'],retained['reverse_whole_reduction_percent'])>=2 and min(cold['forward_whole_reduction_percent'],cold['reverse_whole_reduction_percent'])>=-2
  comparisons.append(dict(candidate=name,arm=arm,conditions=conditions,performance_screen_passed=eligible,normal_API_display_and_production_pending=eligible,GPU_operator_and_four_input_quality_pending=eligible and arm==2))
 report=dict(schema='ps5-qwen-io-gpu-comparison-v1',case=int(a.case.name.rsplit('-',1)[1]),completed=True,requests=count,warmup_pairs_excluded=[0],all_exact_counting_tokens_and_bytes=True,all_full_vocabulary_rows_finite=True,original_weight_precisions_driver_and_reserves_preserved=True,source_model_GPU_owners_positively_retired=True,ordinary_close_exact_restore=True,CPU_heap_peak_bytes=t['CPU_heap_peak_bytes'],device_ledger_peak_bytes=t['device_ledger_peak_bytes'],rows=rows,comparisons=comparisons,limitations=['Finite compiled counting task; no broad quality or sustained-service qualification.','Both arms share the newly sealed pack; physical placement versus the previous28-key pack is not held identical.','Whole request includes prefill/EOS; decode throughput is a separate metric.','Source read wall is not raw NAND time; wall residuals do not isolate pure GPU time.'],evidence=[evidence(a.case/'native-model-terminal.private.json'),evidence(a.case/'restored-complete.private.json')],CI_runs=0)
 need(not a.out.exists(),'Preserve previous analyses');a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(dict(completed=True,comparisons=comparisons)))
if __name__=='__main__':main()

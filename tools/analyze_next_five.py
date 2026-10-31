#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize completed native comparisons without treating failures as timings."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import require,record,write_json

def analyze(case):
    case=Path(case);r=json.loads((case/'native-model-terminal.private.json').read_text())
    require(r.get('completed') and len(r['requests'])==14 and r['all_model_source_device_owners_positively_retired'] and r['device_ledger_live_bytes']==0,'Complete positive native comparison required')
    rows=r['requests'];groups={}
    for label,ids in [('control_cold',[2,8]),('candidate_cold',[4,6]),('control_retained',[3,9]),('candidate_retained',[5,7])]:
        group=[rows[i]for i in ids];m={k:statistics.mean(x['metrics'][k]for x in group)for k in ('decode_tokens_per_second','total_ms','TTFT_ms')}
        groups[label]=dict(ordinals=ids,metrics=m,outputs_equal_to_control=all(x['same_tokens_as_independent']for x in group),
            physical_read_bytes=statistics.mean(x['completed_performance']['delta']['source_physical_read_bytes']for x in group),
            physical_read_calls=statistics.mean(x['completed_performance']['delta']['source_physical_read_calls']for x in group))
    cr=groups['control_retained']['metrics'];br=groups['candidate_retained']['metrics']
    before=rows[5]['metrics']['decode_tokens_per_second']-rows[3]['metrics']['decode_tokens_per_second']
    after=rows[7]['metrics']['decode_tokens_per_second']-rows[9]['metrics']['decode_tokens_per_second']
    spread=abs(rows[9]['metrics']['decode_tokens_per_second']-rows[3]['metrics']['decode_tokens_per_second'])
    grades=json.loads((case/'quality-content-and-format.private.json').read_text())['rows']
    semantic=[x['semantic']for x in grades if x['ordinal']>=10]
    same_counting=all(x['same_tokens_as_independent']for x in rows[4:8])
    eligible=before>0 and after>0 and br['decode_tokens_per_second']-cr['decode_tokens_per_second']>spread and br['total_ms']<cr['total_ms'] and same_counting and all(semantic)
    return dict(completed=True,case=str(case),source=record(case/'native-model-terminal.private.json'),groups=groups,
        retained_decode_gain_percent=100*(br['decode_tokens_per_second']/cr['decode_tokens_per_second']-1),retained_whole_time_reduction_percent=100*(1-br['total_ms']/cr['total_ms']),
        temporal_decode_differences=[before,after],control_AA_decode_spread=spread,all_fixed_semantic_tasks_passed=all(semantic),quality_grades=semantic,
        same_counting_output=same_counting,speed_and_finite_quality_eligible=eligible,application_device_peak_bytes=r['device_ledger_peak_bytes'],
        retired=True,normal_and_placement_required_before_production=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();result=analyze(a.case);write_json(a.out,result);print(json.dumps({k:result[k]for k in ('completed','retained_decode_gain_percent','retained_whole_time_reduction_percent','quality_grades','same_counting_output','speed_and_finite_quality_eligible')}))
if __name__=='__main__':main()

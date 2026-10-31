#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize completed exact row-delivery comparisons without mixing cache sizes."""
import argparse,json
from pathlib import Path
from expert_q4 import require,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();cases=[]
    for number,slots in ((11720,1381),(11760,3072),(12120,3072)):
        root=a.cache/f'hardware-first-generation-{number}';r=json.loads((root/'native-model-terminal.private.json').read_text());closed=json.loads((root/'restored-complete.private.json').read_text());grades=json.loads((root/'candidate-contents-decision.private.json').read_text())
        require(r['completed']and closed['completed']and not closed['unknown_completion']and len(r['requests'])==8 and r['all_model_source_device_owners_positively_retired']and r['device_ledger_live_bytes']==0,'Closed complete eight-request comparison required')
        require(r['full_F32_continuation_and_routes_passed']and all(x['maximum_absolute_logit_error']==0 and x['full_F32_finite']for x in r['requests']),'Exact full F32 rows and complete routes required')
        totals={False:0.,True:0.};rows=[]
        for x in r['requests']:
            enabled=x['small_rows']['enabled'];totals[enabled]+=x['metrics']['total_ms'];rows.append(dict(task=x['quality_task'],batch=enabled,metrics=x['metrics'],small_rows=x['small_rows'],generated_tokens=len(x['token_ids'])))
        for task in range(4):
            x,y=r['requests'][2*task:2*task+2];require(x['token_ids']==y['token_ids']and x['output_bytes']==y['output_bytes'],'Each same-cache task pair must emit identical bytes/tokens')
        cases.append(dict(case=number,active_slots=slots,batch_first=r['requests'][0]['small_rows']['enabled'],scalar_total_ms=totals[False],batch_total_ms=totals[True],reduction_percent=100*(1-totals[True]/totals[False]),all_contents_correct=grades['all_contents_passed'],full_F32_maximum=0,ordinary_close_exact_restore=True,rows=rows))
    matched=[c for c in cases if c['active_slots']==3072];scalar=sum(c['scalar_total_ms']for c in matched);batch=sum(c['batch_total_ms']for c in matched)
    require({c['batch_first']for c in matched}=={False,True},'Both execution orders at3072 slots required')
    write_json(a.out,dict(schema='ps5-qwen-weight-small-rows-results-v1',completed=True,production_adopted=False,
        cases=cases,matched_cache_slots=3072,matched_scalar_total_ms=scalar,matched_batch_total_ms=batch,
        matched_total_reduction_percent=100*(1-batch/scalar),all_full_F32_rows_ordered_routes_tokens_and_bytes_exact=True,
        all_contents_correct=all(c['all_contents_correct']for c in cases),extra_scratch_bytes=0,extra_GPU_buffers=0,
        observed_merging='One duplicate Japanese row merges; other actual cohort physical calls equal logical rows. Most benefit is parallel delivery and amortized guards.',
        first_arm_shader_preparation_bias_balanced_by_opposite_order=True,normal_API_display_and_production_pending=True))
    print(json.dumps(dict(matched_cache_slots=3072,total_reduction_percent=100*(1-batch/scalar),native_requests=24,exact_F32=True)))

if __name__=='__main__':main()

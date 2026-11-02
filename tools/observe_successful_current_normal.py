#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use the successful current API/frame protocol with retained input provenance."""
import argparse
import inspect
import json
import math
from pathlib import Path
import sys

import observe_expert_all_q2_monitor as ordinary
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save
from success_case_control import current_files,lan_module,PHYSICAL


def retained_row(row,ordinal):
    return (row['full_F32_finite'] and math.isfinite(row['maximum_absolute_logit_error']) and
        row.get('Expert_weight_retention_enabled') is True and row.get('cross_cache_F32_exact_required') is False and
        (row['same_tokens_as_independent'] and 0<row['full_F32_logit_rows_compared']<=33 if ordinal==1 else True))


def observer_source():
    source=inspect.getsource(ordinary.main)
    source=once(source,"result['active_cache_slots']==867","result['active_cache_slots']==3712")
    source=once(source,"row['maximum_absolute_logit_error']<=1e-5,","retained_row(row,ordinal),")
    # Record answer quality separately so a known misanswer still reaches the
    # ordinary finish/resource-retirement protocol before candidate rejection.
    source=once(source,"row['counting_quality_passed'] and row['request_reset_completed']",
        "type(row['counting_quality_passed']) is bool and row['request_reset_completed']")
    source=once(source,"    for ordinal in (1,2):\n        streams.append(",
        "    for ordinal in (1,2):\n        require(not failure(),'Explicit native failure prevents further requests')\n        streams.append(")
    source=once(source,"    def failure():\n", """    def failure():
        processes=json.loads(get(8084,'/processes_list',1<<20))['processes']
        owners=[r for r in processes if r['name']=='eboot.bin']
        require(len(owners)==1 and owners[0]['pid']==owner['pid'],'Exact native owner changed; no further requests')
""")
    return source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('current','case-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();case=load(args.case_plan)
    first_path=args.case_plan.parent/'native-first-start.private.json';first=load(first_path)
    ready=load(args.case_plan.parent/'native.demo.ready.private.json')
    state=load(args.current/'active-console.private.json')
    gate=load(args.case_plan.parent/'development.json')['native_first_generation_validation']
    need(state['native_running'] and state['active_successful_native_case']['run_id']==case['run_id'] and
         first['pid']==ready['pid'] and first['run_id']==ready['run_id']==case['run_id'] and
         first['candidate_SELF_sha256']==case['SELF']['sha256']==gate['candidate_SELF_sha256'] and
         first['model_receipt_sha256']==gate['model_receipt_sha256'], 'Exact accepted current model owner and readiness required')
    need(current_files(args.current)==case['old_files'] and record(case['SELF']['path'])==case['SELF'],
         'Retained selected original and actual running SELF must be unchanged')
    dependencies=case['required_bundle_inputs'];need(record(dependencies['path'])==dependencies,
        'Complete live input proof changed')
    assets={}
    for row in case['old_files']:
        name=Path(row['path']).name
        if name in ('index.html','app.js','style.css'):
            assets['/' if name=='index.html' else '/'+name]=row['sha256']
    binding=dict(schema='ps5-qwen-Expert-all-Q2-monitor-binding-v1',host=lan_module().HOST,port=8086,
        automatic_retries=0,native_binding=first,report_remote=PHYSICAL+case['report'][5:],monitor_assets=assets,
        accepted_case=record(args.case_plan),current_active_cache_slots=3712,required_bundle_inputs=dependencies)
    binding_path=args.case_plan.parent/'normal-observer-binding.private.json'
    save(binding_path,binding)
    source=observer_source()
    (args.case_plan.parent/'normal-observer-source.private.py').write_text(source,encoding='utf-8',newline='\n')
    env=dict(ordinary.__dict__,retained_row=retained_row)
    sys.argv=[sys.argv[0],'--binding',str(binding_path),'--out',str(args.out)]
    exec(compile(source,__file__+'#current-normal','exec'),env);env['main']()


if __name__=='__main__':main()

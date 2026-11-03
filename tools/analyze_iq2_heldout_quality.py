#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the established held-out answers without changing the decode speed metric."""
import argparse
import json
from pathlib import Path
from build_expert_quality_cohort import PROMPTS
from build_iq2_heldout_quality import CASES
from build_performance_quantizer import record
from iq2_up_model_scope import require_cache_layout
from start_success_route import load,need,save


def answer(task,raw):
    try:value=bytes(raw).decode('utf-8').strip(' \t\r\n')
    except (UnicodeError,ValueError):return False,None
    if task==0:return value in ('猫','ねこ','ネコ'),value
    if task==1:return value=='42',value
    need(task==2,'One original semantic task is required')
    try:
        parsed=json.loads(value)
        passed=isinstance(parsed,dict) and set(parsed)=={'city','count'} and parsed['city']=='Tokyo' and type(parsed['count']) is int and parsed['count']==3
    except (ValueError,TypeError):passed=False
    return passed,value


def completed(root,arm):
    result=load(root/'result.private.json');plan=load(root/'case/plan.private.json')
    def exact(row):need(record(row['path'])==row,'Completed quality evidence changed');return load(row['path'])
    terminal=exact(result['terminal']);closed=exact(result['closure']);package=exact(plan['package'])
    profile=exact(package['effective_application_policy']['profile']);scope=profile['overrides']['native_headless_model_audit']
    require_cache_layout(profile)
    heldout=scope.get('heldout_functional_quality',{})
    need(result['completed'] and terminal['completed'] and len(terminal['requests'])==3 and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and profile['heldout_quality_only'] and scope['arm']==arm and
         not terminal['timings_usable_for_performance'] and not profile['performance_timings_usable'] and
         not scope['original_cold_retained_exact_prefix_sequence'] and heldout['prompts']==PROMPTS and
         heldout['cases']==CASES and heldout['independent_context_per_prompt'] and
         terminal['candidate_SELF_sha256']==package['SELF']['sha256'],
         'Exact completed quality-only requests, source retirement and ordinary restoration are required')
    manifest=profile['quality_production_manifest'];exact(manifest)
    rows=[]
    for index,row in enumerate(terminal['requests']):
        need(row['heldout_quality_task']==index and row['heldout_prompt']==PROMPTS[index] and
             row['counting_quality_applicable'] is False and row['full_F32_finite'] and row['request_reset_completed'] and
             row['full_F32_logit_rows_compared']==0 and row['full_F32_logit_rows_checked_finite']>0 and
             row['token_ledger_closed_before_request_result'] and row['prefix']['enabled'] is False and
             row['prefix']['request_hit'] is False,'Every independent semantic request must finish and remain finite')
        passed,text=answer(index,row['output_bytes'])
        rows.append(dict(case=CASES[index],passed=passed,output=text,token_ids=row['token_ids'],
            generated_tokens=row['metrics']['generated_tokens'],full_F32_rows_finite=row['full_F32_logit_rows_checked_finite']))
    return dict(rows=rows,profile=profile,terminal=terminal,manifest=manifest,
        evidence=[record(root/'result.private.json'),result['terminal'],result['closure'],record(root/'case/plan.private.json'),
                  plan['package'],package['effective_application_policy']['profile'],manifest])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('control','candidate','decode-analysis','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();control,candidate=completed(a.control,'control'),completed(a.candidate,'candidate')
    need(all(control['manifest'][k]==candidate['manifest'][k] for k in ('bytes','sha256')) and
         'model_layer' not in control['profile'] and
         control['terminal']['model_receipt_sha256']==candidate['profile']['model_layer']['parent_recipe_sha256'] and
         candidate['terminal']['model_receipt_sha256']==candidate['profile']['model_layer']['model_receipt']['sha256'],
         'The reusable normal P1 quality control must be the same selected parent of this candidate')
    speed=load(a.decode_analysis)
    need(speed['completed'] and speed['lossy_precision_comparison'] and speed['all_twelve_requests_positively_completed'] and
         speed['all_ordinary_closes_and_exact_restores'] and speed['primary_metric']=='(generated_tokens-1)/decode_seconds' and
         candidate['profile']['quality_parent_package'] in speed['evidence'],
         'The exact candidate must already have completed the original decode cohort')
    rows=[dict(case=before['case'],control=before,candidate=after,retains_control_correct_answer=not before['passed'] or after['passed'])
          for before,after in zip(control['rows'],candidate['rows'])]
    retained=all(row['retains_control_correct_answer'] for row in rows)
    gain=any(row['decode_tokens_per_second']['both_paired_gains_exceed_control_spread'] for row in speed['groups'])
    regression=any(row['decode_tokens_per_second']['both_paired_regressions_exceed_control_spread'] for row in speed['groups'])
    save(a.out,dict(completed=True,decode_analysis=record(a.decode_analysis),cases=rows,
        control_correct=sum(r['passed'] for r in control['rows']),candidate_correct=sum(r['passed'] for r in candidate['rows']),
        retains_every_current_P1_correct_semantic_answer=retained,original_counting_quality_passed=True,
        primary_metric_unchanged=True,measured_speed_screen_passed=gain and not regression,
        finite_four_task_quality_screen_passed=retained and any(r['passed'] for r in control['rows']),
        general_reasoning_or_arbitrary_prompt_equivalence_claimed=False,production_adopted=False,PS5_operations=0,
        evidence=control['evidence']+candidate['evidence']+[record(a.decode_analysis)]))
    print(json.dumps(dict(completed=True,retains_every_P1_correct_answer=retained,
        control_correct=sum(r['passed'] for r in control['rows']),candidate_correct=sum(r['passed'] for r in candidate['rows']),
        measured_speed_screen_passed=gain and not regression,production_adopted=False)),flush=True)


if __name__=='__main__':main()

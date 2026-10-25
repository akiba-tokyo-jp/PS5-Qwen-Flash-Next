#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare completed saved cases without inference or console access."""
import argparse,json,math,statistics
from pathlib import Path

def read(path):return json.loads(Path(path).read_text())
def validate_fixture(fixture,require_non_dyadic=False):
    version=fixture.get('schema')
    if version not in ('ps5-qwen-BF16-indexed-vector-fixture-v1','ps5-qwen-BF16-indexed-vector-fixture-v2'):
        raise ValueError('The original-shape fixture schema is unknown')
    modern=version.endswith('v2')
    if require_non_dyadic and not modern:
        raise ValueError('Non-BF16-exact F32 activation evidence is required')
    if (fixture.get('model_loaded')is not False or fixture.get('positive_completion_and_retirement')is not True or
        fixture.get('graphs_per_strategy')!=3 or fixture.get('selected_experts')!=10 or
        fixture.get('repeated_and_boundary_IDs')is not True or fixture.get('maximum_BF16_bank_bytes')!=32768000):
        raise ValueError('Completed bounded original-shape fixture provenance is required')
    if modern and (fixture.get('additional_non_dyadic_vector_graphs_per_layout')!=1 or
                   fixture.get('timed_strategy_inputs_identical')is not True or
                   fixture.get('reference_accumulation')!='F64' or fixture.get('maximum_absolute_error_limit')!=1e-6):
        raise ValueError('The additional F32 numerical scope differs')
    cases=fixture.get('cases',[])
    if len(cases)!=4:raise ValueError('Four completed original-shape cases are required')
    finite=lambda x:type(x)in (int,float)and math.isfinite(x)
    for row,(columns,rows,vectors)in zip(cases,((2560,640,1),(2560,640,10),(640,2560,1),(640,2560,10))):
        if (row.get('columns'),row.get('rows'),row.get('input_vectors'))!=(columns,rows,vectors):
            raise ValueError('The fixture shape differs')
        error=row.get('max_absolute_error')
        if row.get('passed')is not True or not finite(error)or not 0<=error<=1e-6:
            raise ValueError('Finite original-shape numerical admission is required')
        for name in ('first_ms','warm_mean_ms'):
            values=row.get(name,[])
            if len(values)!=2 or not all(finite(x)and x>0 for x in values):
                raise ValueError('Both completed timing strategies are required')
        if modern:
            count=sum((c*11+v)%13!=6 for v in range(vectors)for c in range(columns))
            if row.get('non_BF16_exact_F32_inputs')!=count:
                raise ValueError('The F32 input population does not match the actual fixture helper')
    paths=fixture.get('path_counters',{})
    if paths.get('BF16_indexed_matrix_calls',0)<12 or paths.get('BF16_indexed_vector_calls',0)<(16 if modern else 12):
        raise ValueError('Completed matrix/vector graph execution evidence is required')
    return dict(schema=version,non_dyadic_F32_inputs_qualified=modern)
def compare(candidate,control):
    candidate,control=Path(candidate),Path(control)
    for case in (candidate,control):
        complete=read(case/'complete.private.json')
        if not (complete['full_plan_completed'] and complete['original_restored'] and
                complete['native_owners']==0 and not complete['model_loaded'] and
                complete['original_numerical_re_admission']=='passed'):
            raise ValueError('Only fully completed and restored cases may be compared')
    fixture=read(candidate/'completed-indexed-vector.private.json')
    fixture_scope=validate_fixture(fixture)
    rows=[]
    for ordinal in (1,2):
        suffix='.demo'+str(ordinal)
        root=candidate/'native-plan-observation/native-result.private.json'
        oldroot=control/'native-plan-observation/native-result.private.json'
        result=read(str(root)+suffix+'.result');old=read(str(oldroot)+suffix+'.result')
        for key in ('token_ids','output_bytes','stop_reason'):
            if result[key]!=old[key]:raise ValueError('Control output differs: '+key)
        for key in ('prompt_tokens','generated_tokens'):
            if result['metrics'][key]!=old['metrics'][key]:raise ValueError('Benchmark workload differs')
        total=result['metrics']['generated_tokens'];first=read(str(root)+suffix+'.token-1');last=read(str(root)+suffix+'.token-'+str(total))
        def delta(key):
            a,b=first[key],last[key]
            if a.keys()!=b.keys() or any(type(x)is not int or x<0 for x in [*a.values(),*b.values()]):
                raise ValueError('Invalid completed interval counters')
            result={k:b[k]-a[k]for k in a}
            if any(v<0 for v in result.values()):raise ValueError('Counters moved backwards')
            return result
        process=delta('completed_performance');paths=delta('completed_path_counters')
        if process['process_calls']!=total-1 or not paths['BF16_indexed_vector_calls']:
            raise ValueError('Decode interval did not execute the candidate')
        if process['source_chunks']!=process['source_completed_windows']:
            raise ValueError('A decode source lease is incomplete')
        rate=result['metrics']['decode_tokens_per_second'];oldrate=old['metrics']['decode_tokens_per_second']
        if not all(isinstance(v,(int,float))and math.isfinite(v)and v>0 for v in (rate,oldrate)):
            raise ValueError('Finite completed rates are required')
        rows.append(dict(ordinal=ordinal,candidate_tok_s=rate,control_tok_s=oldrate,
            observed_gain_percent=100*(rate/oldrate-1),candidate_TTFT_ms=result['metrics']['ttft_ms'],
            control_TTFT_ms=old['metrics']['ttft_ms'],decode_interval=process,decode_paths=paths,
            decode_read_wait_fraction=process['source_read_ns']/process['process_ns']))
    gain=100*(statistics.mean(r['candidate_tok_s']for r in rows)/statistics.mean(r['control_tok_s']for r in rows)-1)
    return dict(schema='ps5-qwen-indexed-vector-comparison-v1',completed_cases=True,
        output_tokens_and_bytes_equal=True,requests=rows,observed_mean_gain_percent=gain,
        original_shape_fixture=fixture['cases'],fixture_scope=fixture_scope,independent_repeated_cases_required_for_small_gains=True,
        production_adopted=False,console_requests=0)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','control','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=compare(a.candidate,a.control)
    with a.out.open('x')as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('observed_mean_gain_percent','output_tokens_and_bytes_equal','production_adopted')}))
if __name__=='__main__':main()

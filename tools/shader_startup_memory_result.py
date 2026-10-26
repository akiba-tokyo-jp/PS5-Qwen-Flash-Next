#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review returned CPU shader startup observations without claiming a leak or reclaimability."""
def validate(result,pid,run_id):
    def require(ok):
        if not ok:raise ValueError('Incomplete or inconsistent CPU shader startup evidence')
    def integer(value,minimum=0):return type(value)is int and value>=minimum
    require(result.get('schema')=='ps5-qwen-shader-startup-memory-result-v1'and type(result.get('pid'))is int and result['pid']==pid and result.get('run_id')==run_id)
    for key in('all_shader_input_calls_returned','CPU_only','ordinary_OS_close_required'):require(result.get(key)is True)
    for key in('GPU_calls','source_workers','model_metadata_files'):require(type(result.get(key))is int and result[key]==0)
    require(result.get('model_loaded')is False and result.get('matched_idle_ns')==2000000)
    calls=result.get('shader_read_calls');require(integer(calls,1)and calls<=16384)
    require(integer(result.get('shader_file_bytes'),1)and result['shader_file_bytes']<=128<<20)
    require(result.get('shader_returned_bytes')==result['shader_file_bytes']and type(result['shader_returned_bytes'])is int)
    window=result.get('shader_input_window_bytes');require(integer(window,16384)and window<=1<<20 and window%16384==0)
    require(calls==(result['shader_file_bytes']+window-1)//window)
    samples=result.get('samples');require(isinstance(samples,list)and 2*calls<=len(samples)<=2048)
    sums=dict(matched_idle_pages=0,journal_write_pages=0,journal_fsync_pages=0,read_marker_gap_pages=0)
    read_pairs=0;pending=None;previous=None
    for s in samples:
        require(isinstance(s,dict)and s.get('valid')is True and isinstance(s.get('phase'),str))
        for key in('idle_before_ns','before_ns','write_after_ns','after_ns'):require(integer(s.get(key),1))
        require(s['idle_before_ns']+2000000<=s['before_ns']<=s['write_after_ns']<=s['after_ns'])
        for key in('free_idle_before','free_before','free_after_write','free_after'):require(integer(s.get(key)))
        if previous:require(s['idle_before_ns']>=previous['after_ns'])
        sums['matched_idle_pages']+=s['free_before']-s['free_idle_before']
        sums['journal_write_pages']+=s['free_after_write']-s['free_before']
        sums['journal_fsync_pages']+=s['free_after']-s['free_after_write']
        if s['phase']=='shader_asset_read_before_native_call':require(pending is None);pending=s
        elif s['phase']=='shader_asset_read_native_call_returned':
            require(pending is not None and previous is pending)
            sums['read_marker_gap_pages']+=s['free_idle_before']-pending['free_after'];read_pairs+=1;pending=None
        previous=s
    require(pending is None and read_pairs==calls)
    boundaries=result.get('operation_boundaries');require(isinstance(boundaries,dict)and boundaries.get('enabled')is True and boundaries.get('invalid_observation')is False)
    rows=boundaries.get('rows');require(isinstance(rows,list)and 0<len(rows)<=64 and boundaries.get('total_observations')==len(rows))
    required={'shader_CPU_admission_begin','shader_file_initialization_before','shader_file_initialization_returned',
        'shader_registry_initialization_before','shader_registry_initialization_returned','shader_prior_proof_before',
        'shader_prior_proof_returned','shader_CPU_admission_returned'}
    require(required<={r.get('phase')for r in rows})
    for i,row in enumerate(rows):
        require(row.get('valid')is True and row.get('sequence')==i+1 and integer(row.get('kernel_free_pages'))and integer(row.get('monotonic_ns'),1))
        if i:require(row['monotonic_ns']>=rows[i-1]['monotonic_ns'])
    return dict(CPU_observations_complete=True,shader_read_pairs=read_pairs,samples=len(samples),
        signed_page_changes=sums,page_change_sign='positive_is_more_free_pages',
        intervals_are_sequential_not_atomic=True,read_gap_includes_CPU_and_background_work=True,
        matched_idle_is_not_a_causal_subtraction=True,proprietary_cause_identified=False,
        GPU_execution_qualified=False,full_model_or_production_adopted=False)

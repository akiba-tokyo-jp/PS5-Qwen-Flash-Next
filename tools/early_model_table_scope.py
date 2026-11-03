# SPDX-License-Identifier: MIT
"""Bind model adoption to the exact positively completed CPU table prelude."""
from build_performance_quantizer import record
from start_success_route import load,need


def require(package_or_link):
    early=package_or_link['early_model_CPU_tables']
    for key in ('source','header','manifest','control_native','original_CPU_package','original_CPU_completion',
                'CPU_host_controls','adoption_header','adoption_test'):
        need(record(early[key]['path'])==early[key],'A frozen early model table input changed')
    CPU=load(early['original_CPU_package']['path']);done=load(early['original_CPU_completion']['path'])
    controls=load(early['CPU_host_controls']['path']);original=CPU['early_CPU_tables']
    need(done['completed'] and done['kind']=='CPU-startup-staging-memory' and done['native_requests']==0 and
         load(done['terminal']['path'])['candidate_SELF_sha256']==CPU['SELF']['sha256'] and
         load(done['closure']['path'])['ordinary_exit_observed'] and
         load(done['closure']['path'])['current_seven_restored_and_native_hashed'] and not done['unknown_completion'] and
         load(done['early_CPU_tables_completion']['path'])['whole_zero_SHA256_and_subsequent_FNV_passed'] and
         all(early[k]==original[k] for k in ('source','header','manifest')) and
         controls['completed'] and controls['package']==early['original_CPU_package'] and
         controls['native_body_positive']==1 and controls['native_body_refusals']==16 and
         controls['close_boundary_positive']==2 and controls['close_boundary_refusals']==9 and
         early['adoption_controls']==dict(positive_controls=1,negative_controls=16,CPU_mapping_API_calls=0) and
         early['mapped_CPU_Direct_bytes']==9502720 and early['original_table_bytes']==9486336 and
         early['strict_failure_park_before_original_application_CXX'] and early['model_reuses_exact_early_backing'] and
         early['prelude_GPU_and_source_operations']==0 and early['private_libc_heap_bytes']==8<<20 and
         early['private_libc_heap_extension'] is False,
         'Exact completed CPU-only primitive and explicit model adoption with no second allocation required')
    profile=load(package_or_link['effective_application_policy']['profile']['path'])
    need(profile['headless_model_audit'] and profile['headless_requests']==3 and
         profile['model_and_GPU_guards_preserved'] and profile['early_model_CPU_tables']=={
             k:v for k,v in early.items() if k!='converted_zero_hole_proof'},
         'The actual finite model entry must explicitly bind this CPU table adoption')
    return early

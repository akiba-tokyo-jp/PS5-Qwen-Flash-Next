#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply a qualified performance fragment to an existing private case offline.

This does not create an execution admission, change an existing case binding,
contact a console, deploy an application or start CI. Fresh-case, ownership,
memory, source integrity and ordinary restoration gates remain mandatory.
"""
import argparse
import copy
import json
from pathlib import Path

FEATURE_KEYS={'native_bf16_indexed_vector','native_indexed_vector_fixture',
              'native_padded_expert_cache','native_mapped_streaming_copy'}

def apply_profile(policy,profile,package):
    if profile.get('schema')!='ps5-qwen-qualified-performance-profile-v1':
        raise ValueError('Unknown qualified performance profile')
    artifact=profile['application_SELF']
    if (package.get('integrity_verified')is not True or package.get('roundtrip_segments_verified')!=6 or
            package.get('real_module_import_audit',{}).get('missing')!=[] or
            package['SELF']['sha256']!=artifact['sha256'] or package['SELF']['bytes']!=artifact['bytes'] or
            package['linked_driver']['archive_sha256']!=profile['driver']['archive_sha256']):
        raise ValueError('The exact qualified application and driver are required')
    if (profile['precision']!={'weights':'original BF16/F32','KV_cache':'F32','quantization':False} or
            profile['driver']['persistent_shader_cache']is not False or
            profile['driver']['persistent_pipeline_cache']is not False):
        raise ValueError('Precision and persistent-cache policy must remain qualified')
    selected=profile['selected_native_policy'];disabled=profile['disabled_native_policy']
    if (not isinstance(selected,dict)or not isinstance(disabled,list)or
            not set(selected)<=FEATURE_KEYS or not set(disabled)<=FEATURE_KEYS or
            set(selected)&set(disabled)or set(selected)|set(disabled)!=FEATURE_KEYS or
            'native_mapped_streaming_copy'not in disabled):
        raise ValueError('Only the explicitly qualified performance switches may change')
    if selected.get('native_padded_expert_cache',{}).get('active_slots')==128:
        # A switch fragment cannot manufacture the complete layout, memory and
        # matched-production qualification required by this application image.
        required=profile.get('required_runtime_scope',{})
        keys={'native_matched_cache_production','native_resident_OS_reserve',
              'native_resident_CPU_table_pricing','native_prefix_delivery_combination'}
        layout=policy.get('native_large_cache_scope',{})
        proof=layout.get('layout_qualification',{})
        cache=selected['native_padded_expert_cache']
        exact=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'))
        if(set(required)!=keys or any(exact(policy.get(k))!=exact(required[k])for k in keys)or
           layout.get('stage')!='model' or type(layout.get('active_slots'))is not int or layout['active_slots']!=128 or
           layout.get('physical_planes')!=129 or layout.get('cache_request_bytes')!=1274462208 or
           proof.get('SELF_sha256')!=cache.get('layout_qualification_SELF_SHA256')or
           proof.get('report_sha256')!=cache.get('layout_qualification_result_SHA256')):
            raise ValueError('Prepare the exact qualified 128-slot prefix/delivery runtime before applying its feature fragment')
    if (policy.get('allowed_modes')!=['first-generation-validation'] or
            policy.get('deployment_enabled')is not False or
            'native_first_generation_validation'not in policy or
            policy.get('native_prefill',{}).get('tokens')!=4 or
            policy.get('native_source_schedule',{}).get('source_window_bytes')!=8388608 or
            policy.get('native_source_schedule',{}).get('maximum_outstanding_reads')!=2):
        raise ValueError('An existing bounded original-precision case is required')
    result=copy.deepcopy(policy)
    for key in disabled:result.pop(key,None)
    result.update(copy.deepcopy(selected))
    if {k:v for k,v in result.items()if k not in FEATURE_KEYS}!={k:v for k,v in policy.items()if k not in FEATURE_KEYS}:
        raise ValueError('Performance application changed another case field')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('policy','profile','package'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--out',type=Path,help='New private policy path; omission verifies an already selected policy')
    a=p.parse_args();read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    policy,profile,package=read(a.policy),read(a.profile),read(a.package)
    before={path:path.read_bytes()for path in (a.policy,a.profile,a.package)}
    result=apply_profile(policy,profile,package)
    if a.out:
        with a.out.open('x',encoding='utf-8',newline='\n')as f:f.write(json.dumps(result,indent=2)+'\n')
    elif result!=policy:raise ValueError('The supplied policy has not selected the qualified profile')
    if any(path.read_bytes()!=data for path,data in before.items()):raise ValueError('A bound input changed')
    print(json.dumps(dict(exact_qualified_profile_applied=True,application_SELF_sha256=profile['application_SELF']['sha256'],
        unchanged_case_binding=True,console_connections=0,GPU_calls=0,CI_runs=0)))

if __name__=='__main__':main()

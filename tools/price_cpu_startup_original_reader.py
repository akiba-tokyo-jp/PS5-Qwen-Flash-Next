#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price a CPU-only original-reader measurement from completed native observations."""
import argparse
import json
from pathlib import Path
import re
import struct

from build_performance_quantizer import record
from start_success_route import load,need,save


def exact(row):
    need(record(row['path'])==row,'An immutable CPU startup input changed')
    return load(row['path'])


def load_pages(package):
    linked=exact(package['relink']);elf=linked['artifact'];need(record(elf['path'])==elf,'Actual linked ELF changed')
    raw=Path(elf['path']).read_bytes();need(raw[:6]==b'\x7fELF\x02\x01','Little-endian ELF64 required')
    offset=struct.unpack_from('<Q',raw,32)[0];size,count=struct.unpack_from('<HH',raw,54)
    need(size==56 and count>0,'Complete ELF64 program headers required')
    return sum((struct.unpack_from('<Q',raw,offset+i*size+40)[0]+16383)//16384
               for i in range(count) if struct.unpack_from('<I',raw,offset+i*size)[0]==1)


def require_CPU_profile(package_path):
    from build_cpu_startup_memory import BLOCK
    from build_speculative_batch_probe import once
    package=load(package_path);need(package['completed'] and package['normalized_SELF_roundtrip_equal'],'Complete host SELF package required')
    profile=exact(package['effective_application_policy']['profile']);scope=profile['overrides']['native_headless_model_audit']
    need(profile['headless_audit_kind']=='CPU-startup-staging-memory' and profile['unloaded_CPU_fixture'] and profile['headless_requests']==0 and
         scope.get('original_selected_64KiB_reader_after_identical_publication') is True and scope['passive_before_SELF_settle'] is False and
         scope['model_loads']==scope['GPU_calls']==scope['source_workers_created']==scope['source_payload_reads']==0 and
         scope['early_return_before_model_source_initialization'] and scope['full_original_model_path_linked'] and
         scope['original_reader_floor_and_30_second_total_deadline_unchanged'],'Exact original-reader CPU-only scope required')
    for key in ('source','entry_artifact','CPU_startup_gate_source','CPU_startup_gate_provider','CPU_startup_original_entry'):
        need(record(profile[key]['path'])==profile[key],'Fixed CPU-only entry/provider changed')
    original=Path(profile['CPU_startup_original_entry']['path']).read_text(encoding='utf-8')
    marker='        qwen_app::require_first_generation_policy(policy,false);'
    expected='extern "C" int qwen_cpu_startup_memory_only();\n'+once(original,marker,marker+BLOCK.replace('SCOPE',json.dumps(json.dumps(scope,separators=(',',':')))))
    need(Path(profile['source']['path']).read_text(encoding='utf-8')==expected and
         Path(profile['CPU_startup_gate_source']['path']).read_text(encoding='utf-8').count('int qwen_cpu_startup_memory_only(void) { return 1; }')==1,
         'Entire original entry plus exact CPU block and unconditional gate required')
    linked=exact(package['relink'])
    need(profile['entry_artifact'] in linked['new_inputs'] and profile['CPU_startup_gate_provider'] in linked['new_inputs'],
         'Actual package must link the exact CPU-only providers')
    reader=profile['CPU_SELF_provider']
    need(not reader.get('startup_settle') and reader['window_bytes']==65536 and reader['OS_minimum_plus_21_unchanged'] and
         reader['source']['sha256']=='9b64505c3506324fa584a03b269ebc3a8dd6530efc79b922bf9277b4846e754e' and
         reader['artifact']['sha256']=='f829b16763ad10993e30bee660140dc5bb03fa5e50a61685ed13ad090ceb6b84' and
         record(reader['source']['path'])==reader['source'] and record(reader['artifact']['path'])==reader['artifact'] and
         linked['link_command'].count(reader['artifact']['path'])==1,'Unmodified selected64KiB reader required')
    publication=exact(profile['CPU_startup_identical_publication'])
    need(publication['completed'] and publication['all_current_seven_payloads_identical_and_natively_hashed'] and
         publication['all108_PC_whole_SHA_values_unchanged'] and publication['title_launches']==publication['GPU_calls']==0,
         'Complete byte-identical selected-file publication required')
    return package,profile


def make(package_path,prior_CPU,successful):
    package,profile=require_CPU_profile(package_path)
    closed=load(prior_CPU/'closed/result.private.json');need(closed['completed'] and closed['ordinary_exit_observed'] and
         closed['current_seven_restored_and_native_hashed'] and not closed['unknown_completion'],'Prior CPU refusal must be positively closed')
    vm=load(prior_CPU/'VM-before/result.private.json')['observations'];stages=prior_CPU/'case/early-boot-stages.private.log';text=stages.read_text()
    need('CXX_initializers_completed\n' in text and 'completed_reads=0\nfatal_operation=main_SELF_Direct_integrity_returned_refusal' in text and
         'early_SELF_Direct_read_before_native_call' not in text and 'main_entered' not in text,'Only the observed completed constructor phase may price this CPU scope')
    free=re.findall(r'CPU_startup_passive_settle done=0 polls=0 free=(\d+) minimum=898 reserved=206 target=2974 ',text)
    need(len(free)==1 and vm['page_bytes']==16384 and vm['minimum']==898,'Exact measured CPU constructor/VM geometry required')
    constructor=min(vm['free_first'],vm['free_last'])-int(free[0]);need(constructor>0,'Positive observed constructor reduction required')
    case=load(prior_CPU/'case/plan.private.json');old=exact(case['package'])
    extra=max(0,load_pages(package)-load_pages(old))
    complete=load(successful/'result.private.json');closure=exact(complete['closure'])
    need(complete['completed'] and complete['all_counting_and_finite_checks'] and closure['ordinary_exit_observed'] and
         closure['current_seven_restored_and_native_hashed'] and not closure['unknown_completion'],'Positively completed native model control required')
    history=successful/'case/native-stages.private.log';sample=re.findall(r'main_SELF_CPU_observation free_before=(\d+) free_last=(\d+) minimum_sampled=(\d+) selected_CPU_floor=919 completed_reads=(\d+)',history.read_text())
    need(len(sample)==1 and int(sample[0][3])>0,'One successful original SELF reader observation required')
    transient=int(sample[0][0])-int(sample[0][2]);need(transient>=0,'Nonnegative observed SELF transient required')
    floor=vm['minimum']+21;slack=256;screen=constructor+extra+transient+floor+slack
    return dict(completed=True,calculation_source=record(Path(__file__)),compiled_CPU_package=record(package_path),profile=record(package['effective_application_policy']['profile']['path']),
        prior_CPU_case=record(prior_CPU/'case/plan.private.json'),prior_CPU_closure=record(prior_CPU/'closed/result.private.json'),
        prior_CPU_VM=record(prior_CPU/'VM-before/result.private.json'),prior_CPU_stages=record(stages),
        successful_control=record(successful/'result.private.json'),successful_reader_stages=record(history),
        observed_Direct_constructor_global_reduction_pages=constructor,extra_static_pages_priced=extra,
        observed_successful_SELF_transient_pages=transient,original_CPU_floor=floor,additional_slack_pages=slack,
        selected_CPU_only_prelaunch_screen_pages=screen,global_observations_are_not_exclusive_allocation_bounds=True,
        no_RAM_gain_subtracted_for_a_transport_hypothesis=True,original_per_read_floor_SHA_identity_EOF_and_deadline_unchanged=True,
        model_GPU_or_source_operations=0,model_screen_pages_unchanged=7374,model_launch_admission_granted=False,PS5_operations=0)


def require_pricing(path,package):
    need(path is not None,'Explicit CPU-only original-reader pricing required');price=load(path)
    expected=make(package,Path(price['prior_CPU_case']['path']).parents[1],Path(price['successful_control']['path']).parent)
    need(price==expected,'CPU pricing must exactly reproduce from immutable measured inputs')
    return price


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','prior-CPU','successful','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=make(a.package,a.prior_CPU,a.successful);a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'result.private.json',result)
    print(json.dumps({k:result[k] for k in ('completed','selected_CPU_only_prelaunch_screen_pages','original_CPU_floor','PS5_operations')}))


if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit the linked indirect provider and remaining application prerequisites."""
import argparse
import json
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION,load

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    retained=load(args.cache/'current/provenance/retained-relink-inputs.private.json')
    rows=[r for r in retained if Path(r['original_path']).name=='libvulkan-cold-tables.a'];assert len(rows)==1
    driver=rows[0];actual=record(driver['path'])
    assert actual=={k:driver[k] for k in ('path','bytes','sha256')}
    assert actual['sha256']=='a325dcd4584b1f1fccc6b46e90faa081ca86d18544aca610efea9e3ca3774f32'
    nm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/llvm-nm.exe'
    symbols=subprocess.check_output([str(nm),'--defined-only',driver['path']],text=True,stderr=subprocess.PIPE,timeout=60)
    (args.out/'driver-symbols.private.txt').write_text(symbols,encoding='utf-8')
    names={line.split()[-1] for line in symbols.splitlines() if line.split()}
    assert {'radv_CmdDispatchIndirect','radv_CmdDispatchIndirect2KHR'}<=names
    assert 'ps5vk_CmdDispatchIndirect' not in names
    bridge=ROOT/'native/app/vulkan_bridge.cpp';bridge_text=bridge.read_text()
    assert record(bridge)['sha256']=='377e9447b41b9d36dadf575efe765e03ac86d15e0e57bd62a39cdc2fc3c80467'
    assert 'return vk_common_GetDeviceProcAddr(device, name);' in bridge_text
    assert 'DispatchIndirect' not in bridge_text
    mesa=args.workspace/'vendor/PS5_Mesa'
    revision=subprocess.check_output(['git','-C',str(mesa),'rev-parse','HEAD'],text=True).strip()
    assert revision=='1ba9874f478657ccf6da72ce55f0260164cc0bd0'
    subprocess.run(['git','-C',str(mesa),'diff','--exit-code','HEAD','--','src/amd/vulkan/radv_cmd_buffer.c'],check=True,capture_output=True)
    dispatch=mesa/'src/amd/vulkan/radv_cmd_buffer.c';text=dispatch.read_text()
    body=text.split('radv_CmdDispatchIndirect(VkCommandBuffer',1)[1].split('\n}',1)[0]
    assert 'vk_device_address_range(' in body and 'radv_CmdDispatchIndirect2KHR(' in body
    body2=text.split('radv_CmdDispatchIndirect2KHR(VkCommandBuffer',1)[1].split('\n}',1)[0]
    assert '.indirect_va = pInfo->addressRange.address' in body2 and 'radv_compute_dispatch(' in body2
    assert 'PKT3(PKT3_DISPATCH_INDIRECT' in text
    up=args.cache/('upstream/llama.cpp-'+REVISION)
    moecache=up/'src/llama-moe-cache.cpp';cache=moecache.read_text()
    at=cache.index('ggml_backend_synchronize(backend);',cache.index('ggml_backend_tensor_get_async'))
    assert at>0
    predictor=ROOT/'native/app/predictive_model_geometry.h'
    assert 'selected==10' in predictor.read_text()
    old_mtp=ROOT/'tools/build_post_top2_mtp.py'
    assert 'llama_memory_clear(llama_get_memory(post_mtp.aux),true);' in old_mtp.read_text()
    result=dict(completed=True,driver_archive=actual,bridge=record(bridge),mesa_revision=revision,
                indirect=dict(actual_link_provider='RADV',RADV_dispatch_symbols_present=True,
                              lightweight_ps5vk_dispatch_not_linked=True,bridge_forwards_unwrapped_entry=True,
                              source_uses_GPU_address_and_indirect_packets=True,
                              previous_lightweight_driver_screen_applies_to_current_link=False,
                              native_GPU_generated_arguments_tested=False,
                              disposition='source-feasible-native-capability-unqualified'),
                G1=dict(authoritative_ID_readback_and_CPU_wait_still_present=True,
                        scheduler_owned_map_reuse_already_adopted=True,
                        live_tensor_address_rebinding_allowed=False,
                        required='GPU ranking/lookup, immutable event snapshot, first-miss stop/resume with no recurrent replay',
                        implementation_complete=False,native_speed_measured=False),
                I1=dict(old_predictor_selected_Experts=10,current_decode_selected_Experts=2,
                        old_predictor_current_model_compatible=False,
                        required='Separate Q2 staging leases, demand-only residency publication, measured useful/wasted bytes and wait',
                        implementation_complete=False,native_speed_measured=False),
                S1=dict(old_auxiliary_state_cleared_each_proposal=True,
                        old_stateless_native_whole_time_regression_percent=26.33546,
                        required='Persistent prefix-aligned auxiliary state, catch-up across accepted bonus tokens, rejection reset/rollback, complete setup cost',
                        stateful_prewarmed_implementation_complete=False,native_speed_measured=False),
                sources=[record(p) for p in (Path(__file__),dispatch,moecache,predictor,old_mtp)],
                PS5_operations=0,production_adopted=False)
    (args.out/'result.private.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=True,actual_indirect_provider='RADV',old_screen_current_link_applicable=False,
                         native_indirect_tested=False,I1_old_predictor_incompatible=True,
                         S1_stateful_candidate_unimplemented=True,PS5_operations=0,production_adopted=False)))


if __name__=='__main__':main()

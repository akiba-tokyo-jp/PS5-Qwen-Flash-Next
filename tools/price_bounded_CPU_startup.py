#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price a separate bounded-private-heap CPU startup experiment, never a model."""
import argparse
from pathlib import Path
import struct

from bounded_CPU_startup_parameters import bind
from build_performance_quantizer import record
from price_cpu_startup_original_reader import require_CPU_profile
from price_unloaded_iq2_startup import initializer_count
from start_success_route import load,need,save


def make(package_path,original_case,current):
    package,profile=require_CPU_profile(package_path);parameters=package['CPU_startup_libc_parameter_policy']
    control=load(parameters['control_package']['path']);original=Path(parameters['control_converted_ELF']['path'])
    need(record(parameters['control_package']['path'])==parameters['control_package'] and record(original)==parameters['control_converted_ELF'],
         'The complete original CPU fixture and converted control must remain exact')
    heap=parameters['heap_bytes'];converted=Path(package_path).parent/'eboot.elf';expected,checked=bind(original.read_bytes(),heap)
    need(converted.read_bytes()==expected and heap in (4<<20,8<<20) and not parameters['extended_allocation'] and
         not parameters['model_launch_admission_granted'] and package['relink']==control['relink'] and initializer_count(package)==30,
         'Only the same full-link CPU code with a4/8MiB non-extending private heap is admitted')
    result=load(original_case/'result.private.json');terminal=load(result['terminal']['path']);closed=load(result['closure']['path']);audit=terminal['audit']
    need(result['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and audit['model_loads']==audit['GPU_calls']==0 and
         audit['CPU_heap_peak_bytes']==16<<20 and audit['CPU_libc_fallbacks']==0,
         'The unchanged constructor path must have completed with16MiB tracked Direct backing and zero fallback')
    raw=converted.read_bytes();offset=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
    need(stride==56 and count>0,'The actual converted ELF64 geometry is required')
    pages=sum((struct.unpack_from('<Q',raw,offset+i*stride+40)[0]+16383)//16384 for i in range(count)
              if struct.unpack_from('<I',raw,offset+i*stride)[0]==1)
    # This is an independent CPU-only operational estimate. The additional
    #24MiB allows process/import bootstrap and metadata for the measured16MiB
    #Direct constructor heap. It is not a measured maximum for proprietary OS
    #allocations. The native919-page per-read floor remains mandatory.
    CPU_floor=919;libc_pages=heap//16384;bootstrap_allowance=1536;slack=256
    screen=CPU_floor+pages+libc_pages+bootstrap_allowance+slack
    inputs=[record(package_path),parameters['control_package'],parameters['control_converted_ELF'],record(converted),
        record(original_case/'result.private.json'),result['terminal'],result['closure'],profile['source'],profile['entry_artifact'],
        profile['CPU_startup_gate_source'],profile['CPU_startup_gate_provider'],record(Path(__file__)),record(Path(__file__).with_name('bounded_CPU_startup_parameters.py'))]
    return dict(completed=True,scope='bounded-private-heap-full-link-CPU-startup',compiled_CPU_package=record(package_path),
        current_boot=load(current/'active-console.private.json')['current_boot'],inputs=inputs,actual_converted_ELF_LOAD_pages=pages,
        private_libc_heap_bytes=heap,private_libc_extension=False,private_libc_heap_pages=libc_pages,
        original_direct_constructor_heap_peak_bytes=16<<20,CPU_bootstrap_and_Direct_metadata_allowance_pages=bootstrap_allowance,
        original_CPU_floor_pages=CPU_floor,additional_CPU_slack_pages=slack,constructors=30,
        selected_CPU_only_prelaunch_screen_pages=screen,original_native_identity_SHA_EOF_deadline_and_floor_preserved=True,
        model_GPU_or_source_operations=0,model_screen_pages_unchanged=7374,model_launch_admission_granted=False,
        measured_RAM_gain_subtracted=0,inactive_pages_counted=0,universal_kernel_allocation_bound_claimed=False,
        CPU_only_price_does_not_qualify_model_or_GPU_startup=True,PS5_operations=0)


def require_pricing(path,package_path,current):
    value=load(path);old=next(r for r in value['inputs'] if r['path'].endswith('CPU-original-reader-native-64800\\result.private.json'))
    expected=make(package_path,Path(old['path']).parent,current)
    need(value==expected,'The exact independent CPU scope and explicit allocation estimate must reproduce');return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','original-case','current','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();value=make(a.package,a.original_case,a.current);save(a.out,value)
    print(dict(completed=True,CPU_only_screen_pages=value['selected_CPU_only_prelaunch_screen_pages'],model_admission=False,RAM_gain_claimed=False))


if __name__=='__main__':main()

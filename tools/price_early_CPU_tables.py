#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price only the source-bound early-table CPU fixture from its completed control."""
import argparse
from pathlib import Path
import struct
from build_performance_quantizer import record
from price_cpu_startup_original_reader import require_CPU_profile
from start_success_route import load,need,save


def pages(path):
    raw=Path(path).read_bytes();at=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
    need(stride==56 and count>0,'Complete converted ELF64 geometry required')
    return sum((struct.unpack_from('<Q',raw,at+i*stride+40)[0]+16383)//16384 for i in range(count)
        if struct.unpack_from('<I',raw,at+i*stride)[0]==1)


def make(package_path,current,controls_path):
    package,profile=require_CPU_profile(package_path);early=package['early_CPU_tables']
    controls=load(controls_path)
    need(controls['completed'] and controls['package']==record(package_path) and controls['native_body_positive']==1 and
        controls['native_body_refusals']==16 and controls['converted_layout_refusals']==7 and controls['close_boundary_positive']==2 and
        controls['close_boundary_refusals']==9 and controls['source']==early['source'] and
        record(controls['completion_parser']['path'])==controls['completion_parser'],
        'All new actual-C, converted-boundary and source-bound close controls must be positive before launch')
    need(early['layout']['zero_hole_applied_after_PS5_conversion_only'] and
        early['converted_zero_hole_proof']['only_converted_RW_memsz_changed'] and
        early['mapped_CPU_Direct_bytes']==9502720 and early['original_table_bytes']==9486336 and
        early['source_payload_IO']==early['model_GPU_operations']==0 and early['additional_CPU_constructors']==2,
        'Only the exclusive original-table zero range and source-free CPU prelude are admitted')
    for key in ('source','header','manifest','control_native','original_CPU_package','original_CPU_completion','pre_CXX_primitive_proof'):
        need(record(early[key]['path'])==early[key],'A bound CPU proof changed')
    control=load(early['original_CPU_package']['path']);done=load(early['original_CPU_completion']['path'])
    native=load(done['terminal']['path']);closed=load(done['closure']['path'])
    need(done['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
        native['completed'] and native['model_loads']==native['GPU_calls']==0 and
        control['effective_application_policy']==package['effective_application_policy'], 'The exact original eight-MiB CPU path must be positively complete')
    before=Path(early['original_CPU_completion']['path']).parent/'VM-before/result.private.json'
    vm=load(before)['observations'];SELF=native['audit']['main_SELF']
    need(SELF['completed'] and SELF['selected_CPU_floor']==919 and SELF['minimum_sampled_free']>=919 and
        vm['boot_before']==vm['boot_after']==load(current/'active-console.private.json')['current_boot'],'Exact current-boot successful CPU geometry required')
    old_converted=Path(early['original_CPU_package']['path']).parent/'eboot.elf';converted=Path(package_path).parent/'eboot.elf'
    old_pages,new_pages=pages(old_converted),pages(converted);removed=old_pages-new_pages
    need(0<removed<=580,'Only actual excluded ELF LOAD pages may be priced')
    observed_drop=min(vm['free_first'],vm['free_last'])-SELF['minimum_sampled_free']
    # The old original table mapper and CPU-only Direct reader use21 pages
    #of metadata/idle margin. Preserve the old256-page CPU slack and select
    #32 additional pages for this earlier mapping/zero/check phase. These
    #empirical operational screens are not exclusive or universal OS bounds.
    additional=32;screen=observed_drop+919+256-removed+additional
    inputs=[record(package_path),record(converted),early['original_CPU_package'],early['original_CPU_completion'],
        done['terminal'],done['closure'],record(before),record(old_converted),early['pre_CXX_primitive_proof'],early['source'],early['header'],early['manifest']]
    return dict(completed=True,scope='early-owned-zero-table-CPU-startup',compiled_CPU_package=record(package_path),inputs=inputs,
        host_controls=record(controls_path),
        current_boot=vm['boot_before'],original_converted_LOAD_pages=old_pages,new_converted_LOAD_pages=new_pages,
        actual_excluded_LOAD_page_difference=removed,observed_control_global_CPU_drop_pages=observed_drop,
        additional_early_mapping_metadata_allowance_pages=additional,CPU_slack_pages=256,original_CPU_floor_pages=919,
        selected_CPU_only_prelaunch_screen_pages=screen,private_heap_bytes=8<<20,private_heap_extension=False,
        model_GPU_or_source_operations=0,model_screen_pages_unchanged=7374,model_launch_admission_granted=False,
        inactive_pages_counted_as_free=False,exclusive_or_causal_RAM_saving_claimed=False,
        universal_kernel_allocation_bound_claimed=False,PS5_operations=0)


def require_pricing(path,package_path,current):
    value=load(path);need(record(value['host_controls']['path'])==value['host_controls'] and
        value==make(package_path,current,Path(value['host_controls']['path'])),'Exact source-bound CPU price must reproduce');return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','current','controls','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();value=make(a.package,a.current,a.controls);save(a.out,value)
    print(dict(completed=True,CPU_only_screen_pages=value['selected_CPU_only_prelaunch_screen_pages'],model_admission=False))


if __name__=='__main__':main()

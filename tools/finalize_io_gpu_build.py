#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Repair new diagnostic labels and bind the actual replacement Vulkan object."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,write_json,require
from scoped_native_variant import link,seal
from build_model_io import validate_overrides
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];text=Path(ec[ec.index('-c')+1]).read_text()
 text=once(text,'{"cache_reset_before_request",i%4==0}','{"cache_reset_before_request",i%2==0}');text=once(text,'{"enabled",arm>0}','{"enabled",true}')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,text)),[Path(__file__)])
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 m=json.loads(Path(r['bounded_model_source_manifest']['path']).read_text());item=next(x for x in m['objects']if x['source'].endswith('ggml-vulkan.cpp'));old=item['object']['path'];gc=r['io_gpu_comparison']['GPU_command'];obj=Path(gc[gc.index('-o')+1])
 require(old not in r['link_command']and r['link_command'].count(str(obj))==1,'Actual Vulkan replacement must be the explicit linked object')
 item.update(object=record(obj),command=gc);m['sources'][item['source']]['patched_sha256']=r['io_gpu_comparison']['GPU_source']['sha256'];mp=a.out/'model-io.private.json';write_json(mp,m)
 r['bounded_model_source_manifest']=record(mp);r['bounded_model_source_overrides']=validate_overrides(mp,Path(r['engine_receipt']['path']));r['lossless_shader_storage']['vulkan_object']=item['object'];r['inputs_before'].append(record(mp))
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_io_gpu_comparison',original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,actual_Vulkan_object_and_source_manifest_bound=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

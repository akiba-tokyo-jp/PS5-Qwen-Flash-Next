#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose measured row delivery with the expanded cache using exact providers."""
import argparse,copy,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','rows','control','workspace','cache','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());rows=json.loads(a.rows.read_text());control=json.loads(a.control.read_text())
    require(prior['resident_cache3072']['active_slots']==3072 and rows['resident_small_rows']['maximum_logical_rows']==8,
            'Exact measured cache and bounded row profiles required')
    require(prior['linked_driver']==rows['linked_driver'] and
            prior['resident_all_Q8']['additional_weight_saved_bytes']==3163852800,
            'One original driver and resident model required')
    a.out.mkdir(parents=True,exist_ok=False)
    old_ops=next(r['object']['path']for r in prior['bounded_model_source_overrides']['objects']if r['source']=='ggml/src/ggml-cpu/ops.cpp')
    new_ops=next(r for r in rows['bounded_model_source_overrides']['objects']if r['source']=='ggml/src/ggml-cpu/ops.cpp')
    require(prior['link_command'].count(old_ops)==1 and record(new_ops['object']['path'])==new_ops['object'],'One exact CPU row provider required')
    seed=copy.deepcopy(prior);seed['link_command'][seed['link_command'].index(old_ops)]=new_ops['object']['path']
    for key in ('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):
        seed[key]=copy.deepcopy(rows[key])
    seed['inputs_before'] +=[record(a.rows),new_ops['object'],new_ops['actual_source'],
                            rows['bounded_model_source_manifest'],rows['shader_resource_manifest']]
    seed_path=a.out/'seed.private.json';write_json(seed_path,seed)
    # Retain the expanded ledger in the newly compiled source owner.
    old_owner=prior['all_Q2_optimized_monitor']['commands'][1]
    budget=Path(old_owner[old_owner.index('-c')+1]).parent/'device_buffer_budget.h'
    (a.out/'device_buffer_budget.h').write_bytes(budget.read_bytes())
    row_owner=rows['all_Q2_optimized_monitor']['commands'][1]
    row_owner_path=Path(row_owner[row_owner.index('-c')+1])
    reader=row_owner_path.parent/'resident-mapped-source.private.h'
    (a.out/'resident-mapped-source.private.h').write_bytes(reader.read_bytes())
    ec=prior['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
    if literal(control['cold_request']['scope'])in entry:
        entry=once(entry,literal(control['cold_request']['scope']),literal(prior['cold_request']['scope']))
    else:require(literal(prior['cold_request']['scope'])in entry,'Expanded-cache cold-request scope must already be exact')
    result,jobs,sources=link(seed_path,a.out,dict(entry=(ec,entry),owner=(old_owner,row_owner_path.read_text())),
        [Path(__file__),a.parent,a.rows,a.control,seed_path,reader,budget,
         a.out/'device_buffer_budget.h',a.out/'resident-mapped-source.private.h',ROOT/'native/app/resident_small_rows.inc'])
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor'].update(actual_entry=sources['entry'],actual_owner=sources['owner'])
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['all_Q2_optimized_monitor']['commands'][1]=jobs['owner']
    result['routing_winners_normal']['actual_entry']=sources['entry']
    result['resident_small_rows']=copy.deepcopy(rows['resident_small_rows'])
    result['resident_small_rows']['actual_sources'].update(sources);result['resident_small_rows']['commands'].update(jobs)
    result['cold_request']['source_header']=record(a.out/'resident-mapped-source.private.h')
    result['cache_small_rows_composition']=dict(actual_sources=sources,commands=jobs,
        active_slots=3072,original_Cache_Expert_and_resident_payloads_preserved=True,
        physical_reserves_and_kernel_owner_completion_guards_preserved=True,native_verification_pending=True)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='expanded_cache_and_small_rows_composition',
        original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,
        cache_slots=3072,driver_unchanged=True,all_weight_payloads_unchanged=True,
        candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Combine qualified 134-slot geometry with the bounded adaptive passive profiles."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from build_speculative_batch_probe import once
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','cache-native','cache-review','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());cache=json.loads(a.cache_native.read_text());review=json.loads(a.cache_review.read_text())
    if not review['completed']or not review['both_candidate_lifetimes_faster_than_both_controls']or not review['all_8_timed_native_requests_and_routes_exact']or not review['all_normal_close_and_exact_restore']:
        raise ValueError('Closed actual 128/134 ABBA is required before the combined application qualification')
    frozen=list({r['path']:r for d in(prior,cache)for r in d['inputs_before']+[d['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen cache/adaptive source changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();old_scope=prior['adaptive_monitor']['scope'];scope=dict(old_scope,active_cache_slots=134,cache_capacity_review_SHA256=record(a.cache_review)['sha256'])
    old_qualification=prior['matched_cache_monitor']['qualification']
    qualification=dict(schema='ps5-qwen-additional-cache-production-v1',review_SHA256=record(a.cache_review)['sha256'],cases=[6460,6760,6780,6820],
        active_cache_slots=134,within_capacity_F32_rows=184,cross_capacity_full_row_hashes_required_before_adoption=True,
        original_precision_preserved=True,original_passive_monitor_and_two_API_requests=True,sustained_service_qualified=False,automatic_retries=0,
        prefix_reuse_enabled=True,six_demand_enabled=True,baseline_128_combination_review_SHA256=old_qualification['combination_review_SHA256'])
    old_combination=prior['prefix_cache128_combination']['scope']
    combination=dict(schema='ps5-qwen-prefix-cache134-delivery-v1',active_cache_slots=134,physical_planes=135,six_demand_enabled=True,
        baseline_128_prefix_review_SHA256=old_combination['prefix_review_SHA256'],baseline_128_refill_review_SHA256=old_combination['refill_review_SHA256'],
        complete_F32_and_routes_required=True,cache_review_SHA256=record(a.cache_review)['sha256'],automatic_retries=0)
    commands=[];objects=[];replacement={}
    overlay=cache['additional_cache_geometry']['overlay'];overlay_path=overlay['path']
    for i,key in enumerate(('actual_engine','actual_entry')):
        original=Path(prior['adaptive_monitor'][key]['path']);source=a.out/('cache134-'+key+'.private.cpp');text=original.read_text()
        if i==1:
            text=once(text,json.dumps(json.dumps(old_scope,separators=(',',':'))),json.dumps(json.dumps(scope,separators=(',',':'))))
            text=once(text,json.dumps(json.dumps(old_qualification,separators=(',',':'))),json.dumps(json.dumps(qualification,separators=(',',':'))))
            text=once(text,json.dumps(json.dumps(old_combination,separators=(',',':'))),json.dumps(json.dumps(combination,separators=(',',':'))))
            text=once(text,'policy.at("native_large_cache_scope").at("active_slots")!=128','policy.at("native_large_cache_scope").at("active_slots")!=134')
            text=text.replace('{"active_slots",128},{"physical_planes",129}','{"active_slots",134},{"physical_planes",135}')
            text=once(text,'{"completed",true},{"active_cache_slots",128},{"full_F32_rows_compared",monitor_compared_rows}',
                '{"completed",true},{"active_cache_slots",134},{"full_F32_rows_compared",monitor_compared_rows}')
        source.write_text(text,newline='\n');c=prior['adaptive_monitor']['commands'][i].copy();old=c[c.index('-o')+1];obj=a.out/f'{i}.o'
        c[c.index('-c')+1]=str(source);c[c.index('-o')+1]=str(obj);c+=['-ivfsoverlay',overlay_path,'-I',str(original.parent)]
        commands.append(c);objects.append(obj);replacement[old]=str(obj)
    reused=[]
    for row in cache['additional_cache_geometry']['compiled'][2:]:
        old=row['original_object'];new=row['object']['path']
        if prior['link_command'].count(old)!=1:raise ValueError('One actual geometry-dependent application object required: '+old)
        replacement[old]=new;reused.append(row)
    if len(reused)!=12:raise ValueError('Exactly twelve completed non-entry/non-engine geometry objects are required')
    link=[replacement.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,a.cache_native,a.cache_review,Path(__file__),overlay_path,*[Path(c[c.index('-c')+1])for c in commands])]
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5500:])
        print(json.dumps(dict(cache134_monitor_build_step=i+1,total=3,reused_geometry_objects=12)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen combined cache/adaptive input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[1]],link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in objects],
        bounded_model_source_manifest=copy.deepcopy(cache['bounded_model_source_manifest']),bounded_model_source_overrides=copy.deepcopy(cache['bounded_model_source_overrides']),
        shader_resource_manifest=copy.deepcopy(cache['shader_resource_manifest']),lossless_shader_storage=copy.deepcopy(cache['lossless_shader_storage']),
        additional_cache_geometry=copy.deepcopy(cache['additional_cache_geometry']),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['adaptive_monitor'].update(scope=scope,actual_entry=record(Path(commands[1][commands[1].index('-c')+1])),actual_engine=record(Path(commands[0][commands[0].index('-c')+1])),commands=commands,
        active_slots=134,whole_model_capacity_ABBA_qualified=True,cross_capacity_full_F32_adoption_gate_pending=True)
    receipt['matched_cache_monitor']['qualification']=qualification;receipt['prefix_cache128_combination']['scope']=combination
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Combined 134-slot monitor native audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(cache134_adaptive_monitor_built=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()

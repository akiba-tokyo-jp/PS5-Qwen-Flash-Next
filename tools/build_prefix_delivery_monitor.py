#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the passive UI/API application from closed matched combination evidence."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
from audit_native_imports import audit
from build_matched_cache_monitor import generate as cache_monitor, require_winner
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def generate(qualified, original, proof):
    # The prior cache UI builder removes its older context-reuse helpers. Keep
    # the newer table diagnostics and upload-release declaration used at startup.
    begin=qualified.index('extern "C" std::uint64_t qwen_app_release_completed_upload_staging();')
    end=qualified.index('int main(int argc, char ** argv)',begin)
    diagnostics=qualified[begin:end]
    source=qualified.replace('qwen_app::require_resident_additional_policy(policy,"prefix");',
        'qwen_app::require_resident_additional_policy(policy,"cache");')
    source=cache_monitor(source,original,proof)
    main=source.index('int main(int argc, char ** argv)')
    source=source[:main]+diagnostics+source[main:]
    source=source.replace('monitor_reference_logits(33*','monitor_reference_logits(23*').replace('monitor_rows>=33','monitor_rows>=23')
    needle='            std::size_t monitor_reference_rows=0,monitor_compared_rows=0;'
    source=source.replace(needle,needle+'''
            std::array<qwen_app::PrefixReuseStats,2> monitor_prefix_stats{};
            std::array<qwen_six_bank_refill_stats,2> monitor_delivery_stats{};
''')
    enabled='true'if proof['six_demand_enabled']else 'false'
    needle='            const auto demo = qwen_app::serve_bounded_demo('
    source=source.replace(needle,'            qwen_app::configure_native_six_bank_refill('+enabled+');\n'+needle)
    needle='                    qwen_app::FirstGeneration attempt(*engine);'
    source=source.replace(needle,'''                    if(ordinal==1)engine->enable_prefix_reuse(admit_complete_checkpoint);
                    qwen_six_bank_refill_stats monitor_delivery_before{};qwen_app_six_bank_refill_counters(&monitor_delivery_before);
'''+needle)
    needle='                    if(monitor_rows!=23||monitor_geometry_error||monitor_value_error)'
    source=source.replace(needle,'''                    monitor_prefix_stats.at(ordinal-1)=engine->prefix_reuse_stats();
                    qwen_six_bank_refill_stats monitor_delivery_after{};qwen_app_six_bank_refill_counters(&monitor_delivery_after);
                    auto &delivery=monitor_delivery_stats.at(ordinal-1);
                    delivery.batches=monitor_delivery_after.batches-monitor_delivery_before.batches;
                    delivery.reads=monitor_delivery_after.reads-monitor_delivery_before.reads;
                    delivery.logical_bytes=monitor_delivery_after.logical_bytes-monitor_delivery_before.logical_bytes;
                    if(qwen_app_six_bank_refill_enabled()!=DELIVERY_ENABLED||
                       (DELIVERY_ENABLED?(!delivery.batches||delivery.reads!=6*delivery.batches||!delivery.logical_bytes):
                           (delivery.batches||delivery.reads||delivery.logical_bytes)))
                        throw std::runtime_error("Passive monitor six-demand ownership accounting differs");
'''.replace('DELIVERY_ENABLED',enabled)+needle)
    old='monitor_first.rows.size()!=monitor_second.rows.size()'
    source=source.replace(old,'monitor_first.rows.size()!=8*48+monitor_second.rows.size()')
    old='for(std::size_t i=0;i<monitor_first.rows.size();++i){const auto &a=monitor_first.rows[i],&b=monitor_second.rows[i];'
    if source.count(old)!=1:raise ValueError('One original full-route UI comparison required')
    source=source.replace(old,'for(std::size_t i=0;i<monitor_second.rows.size();++i){const auto &a=monitor_first.rows[i+8*48],&b=monitor_second.rows[i];')
    needle='            write_fresh_report(startup.admission_report+".cache128-monitor",'
    check='''            const auto &prefix_first=monitor_prefix_stats[0],&prefix_second=monitor_prefix_stats[1];
            if(!prefix_first.enabled||prefix_first.request_hit||prefix_first.captures!=1||prefix_first.restores||
               !prefix_second.enabled||!prefix_second.request_hit||prefix_second.captures!=1||
               prefix_second.restores!=1||prefix_second.last_reused_prompt_tokens!=30)
                throw std::runtime_error("Passive monitor exact complete prefix capture/restore differs");
'''
    source=source.replace(needle,check+needle)
    needle='{"completed",true},{"active_cache_slots",128},{"full_F32_rows_compared",monitor_compared_rows},'
    source=source.replace(needle,needle+'''
                {"prefix_reuse_enabled",true},{"second_request_reused_prompt_tokens",30},
                {"six_demand_enabled",DELIVERY_ENABLED},{"delivery_batches",Json::array({monitor_delivery_stats[0].batches,monitor_delivery_stats[1].batches})},
'''.replace('DELIVERY_ENABLED',enabled))
    if source.count('engine->enable_prefix_reuse(admit_complete_checkpoint);')!=2:
        # One is the disabled historical validation branch; the other is the
        # qualified production branch before the first of the two API requests.
        raise ValueError('Exact prefix production activation and historical branch required')
    return source


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','cache-review','combination-review','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());cache=json.loads(a.cache_review.read_text());require_winner(cache)
    combination=json.loads(a.combination_review.read_text())
    bound=combination.get('native_build_receipt',{});actual=record(a.parent)
    if any(bound.get(k)!=actual[k]for k in('bytes','sha256')):
        raise ValueError('Use the actual native parent bound by the completed combination review')
    if not(combination['kind']=='prefix' and combination['case']==5680 and combination['full_F32_rows_compared']==184 and
           combination['prefix_pair_total']['reproducible_in_this_finite_cohort'] and combination['only_closed_completed_native_evidence_used']):
        raise ValueError('Complete closed reverse-order 128-slot prefix/delivery win required')
    scope=prior['prefix_cache128_combination']['scope']
    proof=dict(schema='ps5-qwen-matched-cache-production-v1',review_SHA256=record(a.cache_review)['sha256'],
        cases=cache['cases'],active_cache_slots=128,cross_cache_F32_rows=92,original_precision_preserved=True,
        original_passive_monitor_and_two_API_requests=True,sustained_service_qualified=False,automatic_retries=0,
        prefix_reuse_enabled=True,six_demand_enabled=scope['six_demand_enabled'],
        combination_case=combination['case'],combination_review_SHA256=record(a.combination_review)['sha256'])
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Qualified actual dependency changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    command=prior['compile_commands'][0].copy();template=Path(command[command.index('-c')+1]);original=ROOT/'native/app/native_main.cpp'
    source=a.out/'resident-comparison-prefix-delivery-monitor.private.cpp'
    source.write_text(generate(template.read_text(),original.read_text(),proof),newline='\n')
    obj=a.out/'prefix-delivery-monitor.o';old=command[command.index('-o')+1]
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command+=['-I',str(template.parent)]
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen=prior['inputs_before']+[record(x)for x in(a.parent,a.cache_review,a.combination_review,Path(__file__),
        ROOT/'tools/build_matched_cache_monitor.py',template,original,source)]
    for i,c in enumerate((command,link)):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-6000:])
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen passive monitor dependency changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[command],link_command=link,
        inputs_before=frozen+[record(obj)],source_parent=record(a.parent),
        matched_cache_monitor=dict(qualification=proof,combination_review=record(a.combination_review),
            original_UI_API_tail=record(original),one_entry_recompiled=True,original_precision_preserved=True,
            postload_GPU_pricing_explicitly_changed=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Native audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(prefix_delivery_monitor_built=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()

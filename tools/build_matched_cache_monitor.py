#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the original bounded passive monitor only after a complete cache win."""
import argparse
import copy
import json
import os
import subprocess
from pathlib import Path
from audit_native_imports import audit
from build_retained_comparison_entry import main_recipe
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from review_resident_results import paired
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def require_winner(review):
    if not (review['kind']=='cache' and review['cases']==[4780,4880,4900,4920] and
            review['native_requests']==12 and review['cross_cache_F32_rows']==92 and
            review['all_expert_selections_exact'] and review['only_completed_native_evidence_used'] and
            review['decode']['reproducible_in_this_finite_cohort'] and
            review['total']['reproducible_in_this_finite_cohort']):
        raise ValueError('A complete numerically correct, retired, restored and reproducible cache win is required')
    for metric in ('decode','total'):
        checked=paired(review[metric]['control'],review[metric]['candidate'],metric=='decode')
        if not checked['reproducible_in_this_finite_cohort']:
            raise ValueError('Promotion flags disagree with actual matched measurements')


def generate(qualified, original, proof):
    main=qualified.index('int main(int argc, char ** argv)')
    frontier=qualified.index('        const bool prefix_comparison=',main)
    prefix=qualified[:frontier]
    begin=prefix.index('static const llama_context *resident_reused_context=')
    end=prefix.index('int main(int argc, char ** argv)',begin)
    prefix=prefix[:begin]+prefix[end:]
    begin=prefix.index('        const Json reuse_scope=')
    end=prefix.index('        const Json CPU_scope=',begin)
    prefix=prefix[:begin]+prefix[end:]
    old='qwen_app::require_resident_additional_policy(policy,"cache");'
    assert prefix.count(old)==1
    gate='''qwen_app::require_native_validation_policy(policy,mode,false);
        const Json production_scope=PRODUCTION_SCOPE;
        if(policy.at("native_matched_cache_production")!=production_scope||
           policy.at("native_large_cache_scope").at("active_slots")!=128||
           policy.contains("native_resident_comparison")||policy.contains("native_resident_context_reuse"))
            throw std::runtime_error("Exact matched 128-slot bounded monitor production scope required");
        for(const char *key:{"native_model_free_speculation","native_prefix_validation","native_predictive_cache",
                             "native_model_checkpoint_validation","native_padded_bank_layout_probe"})
            if(policy.contains(key))throw std::runtime_error("The matched cache monitor cannot combine unqualified candidate modes");'''
    gate=gate.replace('PRODUCTION_SCOPE',json.dumps(proof,separators=(',',':')))
    # Parse an immutable JSON literal instead of treating JSON object syntax as C++.
    literal=json.dumps(json.dumps(proof,separators=(',',':')))
    gate=gate.replace('const Json production_scope='+json.dumps(proof,separators=(',',':'))+';',
                      'const Json production_scope=Json::parse('+literal+');')
    prefix=prefix.replace(old,gate)
    old='        const bool resident_CPU_calibration=policy.at("native_resident_comparison").at("CPU_startup_calibration").get<bool>();'
    assert prefix.count(old)==1;prefix=prefix.replace(old,'        const bool resident_CPU_calibration=false;')
    old='''        const auto &checkpoint_proof=policy.at("native_resident_checkpoint");
        qwen_app::require_model_free_checkpoint_report(read_completed_native_report(checkpoint_proof),checkpoint_proof);'''
    assert prefix.count(old)==1;prefix=prefix.replace(old,'')
    old='        const bool direct_frame_candidate=false;'
    assert prefix.count(old)==1;prefix=prefix.replace(old,'        const bool direct_frame_candidate=policy.contains("native_direct_frame_evidence");')
    at=original.index('        const auto * chat_template',original.index('int main(int argc, char ** argv)'))
    tail=original[at:]
    needle='            const auto demo = qwen_app::serve_bounded_demo('
    assert tail.count(needle)==1
    setup='''            const auto monitor_columns=std::size_t(llama_vocab_n_tokens(llama_model_get_vocab(model)));
            if(!monitor_columns||monitor_columns>262144)throw std::runtime_error("Bounded original vocabulary required");
            std::vector<float> monitor_reference_logits(33*monitor_columns);
            std::size_t monitor_reference_rows=0,monitor_compared_rows=0;
            double monitor_maximum_F32_error=0;
'''
    tail=tail.replace(needle,setup+needle)
    needle='''                    require_unchanged_model();
                    qwen_app::FirstGeneration attempt(*engine);'''
    assert tail.count(needle)==1
    observer='''                    require_unchanged_model();
                    std::size_t monitor_rows=0;bool monitor_geometry_error=false,monitor_value_error=false;
                    engine->set_logits_observer([&](const float *values,std::size_t count) noexcept {
                        if(!values||count!=monitor_columns||monitor_rows>=33){monitor_geometry_error=true;return;}
                        if(ordinal==1){std::copy(values,values+count,monitor_reference_logits.data()+monitor_rows*monitor_columns);++monitor_reference_rows;}
                        else if(monitor_rows>=monitor_reference_rows){monitor_geometry_error=true;return;}
                        else {for(std::size_t i=0;i<count;++i){const double a=values[i],b=monitor_reference_logits[monitor_rows*monitor_columns+i],e=std::abs(a-b);
                            if(!std::isfinite(a)||!std::isfinite(b)||e>1e-5+1e-5*std::abs(b))monitor_value_error=true;
                            monitor_maximum_F32_error=std::max(monitor_maximum_F32_error,e);}++monitor_compared_rows;}
                        ++monitor_rows;
                    });
                    qwen_app::FirstGeneration attempt(*engine);'''
    tail=tail.replace(needle,observer)
    needle='''                    engine->set_work_guard({});
                    if(speculative_model_candidate)'''
    assert tail.count(needle)==1
    tail=tail.replace(needle,'''                    engine->set_work_guard({});engine->set_logits_observer({});
                    if(monitor_rows!=23||monitor_geometry_error||monitor_value_error)
                        throw std::runtime_error("Bounded monitor full original F32 continuation differs");
                    if(speculative_model_candidate)''')
    needle='''            qwen_app::stop_native_model_sources();
            if(prefix_model_validation)'''
    assert tail.count(needle)==1
    completion='''            qwen_app::stop_native_model_sources();
            if(device_stats.live||source_stats.chunks!=source_stats.completed_windows||
               monitor_reference_rows!=23||monitor_compared_rows!=23)
                throw std::runtime_error("Bounded monitor numerical or ownership completion missing");
            const auto &monitor_first=completed_expert_reports[1],&monitor_second=completed_expert_reports[2];
            if(!monitor_first.complete||!monitor_second.complete||monitor_first.rows.size()!=monitor_second.rows.size())
                throw std::runtime_error("Bounded monitor original expert routes missing");
            for(std::size_t i=0;i<monitor_first.rows.size();++i){const auto &a=monitor_first.rows[i],&b=monitor_second.rows[i];
                if(a.layer!=b.layer||a.tokens!=b.tokens||!std::equal(a.ids.begin(),a.ids.begin()+10*a.tokens,b.ids.begin()))
                    throw std::runtime_error("Bounded monitor original expert selections differ");}
            write_fresh_report(startup.admission_report+".cache128-monitor",{{"schema","ps5-qwen-matched-cache-monitor-result-v1"},
                {"completed",true},{"active_cache_slots",128},{"full_F32_rows_compared",monitor_compared_rows},
                {"maximum_absolute_F32_error",monitor_maximum_F32_error},{"all_original_expert_selections_exact",true},
                {"all_model_source_device_owners_retired",true},{"device_ledger_live_bytes",0},
                {"original_passive_VideoOut_and_two_API_requests_preserved",true},{"persistent_caches_enabled",false}});
            if(prefix_model_validation)'''
    tail=tail.replace(needle,completion)
    return prefix+tail


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','review','workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();review=json.loads(a.review.read_text());require_winner(review)
    prior=json.loads(a.parent.read_text())
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Qualified monitor input changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    proof=dict(schema='ps5-qwen-matched-cache-production-v1',review_SHA256=record(a.review)['sha256'],
        cases=review['cases'],active_cache_slots=128,cross_cache_F32_rows=92,original_precision_preserved=True,
        original_passive_monitor_and_two_API_requests=True,sustained_service_qualified=False,automatic_retries=0)
    recipe=main_recipe(prior).copy();template=Path(recipe[recipe.index('-c')+1]);original=ROOT/'native/app/native_main.cpp'
    source=a.out/'resident-comparison-matched-cache-monitor.private.cpp'
    source.write_text(generate(template.read_text(),original.read_text(),proof),newline='\n')
    obj=a.out/'matched-cache-monitor.o';old=recipe[recipe.index('-o')+1]
    recipe[recipe.index('-c')+1]=str(source);recipe[recipe.index('-o')+1]=str(obj);recipe+=['-I',str(template.parent)]
    assert prior['link_command'].count(old)==1
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen=prior['inputs_before']+[record(x)for x in (Path(__file__),ROOT/'tools/build_retained_comparison_entry.py',
        ROOT/'tools/review_resident_results.py',ROOT/'tools/resident_route_review.py',a.parent,a.review,template,original,source)]
    for i,command in enumerate((recipe,link)):
        result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen monitor input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[recipe],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(obj)],
        matched_cache_monitor=dict(qualification=proof,review=record(a.review),original_UI_API_tail=record(original),
            original_completed_context_recreation_preserved=True,only_entry_recompiled=True,GPU_floor_unchanged=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt.pop('resident_context_reuse',None)
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(matched_cache_monitor_linked=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()

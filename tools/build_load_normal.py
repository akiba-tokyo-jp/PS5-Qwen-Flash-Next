#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the exact tail winner into the real normal controller with lightweight CPU observations."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('normal','candidate','proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.normal.read_text());candidate=json.loads(a.candidate.read_text());proof=json.loads(a.proof.read_text());require(proof['completed']and proof['retired']and min(proof['temporal_whole_time_reductions_ms'])>proof['control_AA_whole_time_spread_ms']and proof['same_counting_output'],'Repeated whole-time improvement and exact returned work required')
 require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit exact implementation before relink');revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();a.out.mkdir(parents=True,exist_ok=False)
 seed=copy.deepcopy(n);g0=n['lossless_shader_storage']['vulkan_object'];g1=candidate['lossless_shader_storage']['vulkan_object'];seed['link_command']=[g1['path']if x==g0['path']else x for x in seed['link_command']]
 for key in('lossless_shader_storage','shader_resource_manifest','io_gpu_comparison'):seed[key]=copy.deepcopy(candidate[key])
 merged={r['path']:r for r in seed['inputs_before']};merged.update({r['path']:r for r in active_link_inputs(candidate)});seed['inputs_before']=list(merged.values())
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='''#include "load_followup_timing.h"
extern "C" void qwen_load_tail_select(bool);
extern "C" void qwen_load_gpu_stats(std::uint64_t*);
static std::array<std::uint64_t,16>load_queue_report(){std::array<std::uint64_t,16>v{};qwen_load_gpu_stats(v.data());return v;}
'''+entry
 old=n['next_five_normal']['scope'];scope=dict(old,selected_GPU_object_SHA256=g1['sha256'],serialized_almost_ready_tail_disabled=True,nested_CPU_measurement_enabled=True,GPU_timestamp_diagnostics_enabled=False)
 require(entry.count(literal(old))==3,'All three normal policy/report scope copies required');entry=entry.replace(literal(old),literal(scope));seed['next_five_normal']['scope']=scope
 old=n['four_next_normal']['scope'];updated=dict(old,selected_GPU_object_SHA256=g1['sha256']);require(entry.count(literal(old))==2,'Both four-next policy/report copies required');entry=entry.replace(literal(old),literal(updated));seed['four_next_normal']['scope']=updated
 entry=once(entry,'qwen_next_select(2);qwen_post_submit_select(true);','qwen_next_select(2);qwen_post_submit_select(true);qwen_load_tail_select(true);qwen_load::enabled=true;')
 entry=once(entry,'static void observed_inference_stage(const char *phase) {','static void observed_inference_stage(const char *phase) {qwen_load::CpuSpan measured(qwen_load::stage);')
 marker='engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{';entry=once(entry,marker,marker+'qwen_load::CpuSpan measured(qwen_load::full_validation);')
 marker='            const auto perf=performance_snapshot(*engine);';entry=once(entry,marker,'            const auto cpu_before=qwen_load::snapshot();\n'+marker)
 marker='            const auto &result=trial.run(request,';entry=once(entry,marker,'            qwen_load::CpuSpan measured_run(qwen_load::request_run);\n'+marker)
 marker='            },[&](const auto &token,const auto &m){';entry=once(entry,marker,marker+'qwen_load::CpuSpan measured_persistence(qwen_load::token_persistence);')
 entry=once(entry,'                    publish(event);','                    {qwen_load::CpuSpan measured(qwen_load::publication);publish(event);}')
 marker='            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();';entry=once(entry,marker,'            measured_run.end();\n'+marker)
 marker='            row["full_F32_finite"]=true;';entry=once(entry,marker,'            const auto cpu_after=qwen_load::snapshot();Json cpu_delta=Json::array();for(unsigned i=0;i<cpu_after.size();++i)cpu_delta.push_back(cpu_after[i]-cpu_before[i]);row["CPU_nested_calls_inclusive_exclusive_ns"]=cpu_delta;row["actual_queue_and_serial_wait_totals"]=load_queue_report();\n'+marker)
 en=candidate['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text();sig='const float *LlamaEngine::effective_logits()const {';engine=once(engine,sig,sig+'qwen_load::CpuSpan measured(qwen_load::logit_access);')
 scan='''        for (int i = 0; i < count; ++i) {
            if (!std::isfinite(logits[i])) throw std::runtime_error("Non-finite model logits");
        }''';engine=once(engine,scan,'        {qwen_load::CpuSpan measured(qwen_load::finite_scan);\n'+scan+'}')
 engine=once(engine,"        std::string piece(256, '\\0');","        qwen_load::CpuSpan rendered(qwen_load::token_render);std::string piece(256, '\\0');");engine=once(engine,'        boundary.complete();stage("inference_token_ready");','        rendered.end();boundary.complete();stage("inference_token_ready");')
 # Replace the actual original engine object, not only a historical recipe.
 original=n['routing_sharing']['commands'][2];en=en.copy();en[en.index('-o')+1]=original[original.index('-o')+1]
 raw=a.out/'normal-seed.private.json';write_json(raw,seed);r,jobs,sources=link(raw,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry),engine=(en,engine)),[Path(__file__),a.normal,a.candidate,a.proof,ROOT/'native/app/load_followup_timing.h'])
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','precision_candidate'):
  r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['limit_defaults']['actual_sources']['entry']=sources['entry'];r['limit_defaults']['commands']['entry']=jobs['entry']
 for key in('four_next_normal','next_five_normal'):r[key].update(actual_sources=sources,commands=jobs,source_revision=revision,normal_qualification_pending=True,production_adopted=False)
 r['strata_followup_normal'].update(actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision);r['post_top2_normal'].update(scope=scope,source_revision=revision,actual_sources=sources,commands=jobs,GPU_object=g1);r['load_followup_normal']=dict(scope=scope,source_revision=revision,actual_sources=sources,commands=jobs,matched_proof=record(a.proof),CPU_categories=candidate['load_followup']['CPU_categories'],GPU_timestamp_operations=False)
 raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(raw),'--out',str(a.out/'GPU-provenance')],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,normal_controller_and_sealed_pack_preserved=True,no_GPU_timestamp_diagnostics=True,matched_whole_time_proof=record(a.proof),source_revision=revision,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

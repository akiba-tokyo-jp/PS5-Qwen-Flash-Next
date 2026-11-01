#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose qualified submission/output/startup winners with the real normal title."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal,recipes
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('normal','submission','output','submission-proof','format-proof','loading-proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();base=json.loads(a.normal.read_text());sub=json.loads(a.submission.read_text());outq=json.loads(a.output.read_text());sp=json.loads(a.submission_proof.read_text());fp=json.loads(a.format_proof.read_text());lp=json.loads(a.loading_proof.read_text())
 require(sp['completed']and sp['retired']and sp['speed_and_finite_quality_eligible']and min(sp['temporal_whole_time_reductions_ms'])>0 and fp['completed']and fp['eligible_for_combination_validation']and fp['resident_output_bytes_saved']==317849600,'Completed qualified submission/format evidence required')
 require(lp['completed']and lp['boundary_cases']==27,'Complete loading boundary proof required');require(sub['post_top2_submission']['scope']['candidate_node_cap']==256 and sub['post_top2_submission']['scope']['candidate_flop_divisor']==40,'Selected actual node256/divisor40 required')
 require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit exact implementation before normal relink');revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();a.out.mkdir(parents=True,exist_ok=False)
 seed=copy.deepcopy(base);ec=base['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();g0=base['lossless_shader_storage']['vulkan_object'];g1=sub['lossless_shader_storage']['vulkan_object'];require(seed['link_command'].count(g0['path'])==1,'One actual original GPU object required');seed['link_command']=[g1['path']if v==g0['path']else v for v in seed['link_command']]
 for k in('lossless_shader_storage','shader_resource_manifest','io_gpu_comparison'):seed[k]=copy.deepcopy(sub[k])
 merged={r['path']:r for r in seed['inputs_before']};merged.update({r['path']:r for r in active_link_inputs(sub)});seed['inputs_before']=list(merged.values())
 for key in('precision_plan','exact_typed_receipt'):
  r=outq['post_top2_output_Q4'][key];require(record(r['path'])==r,'Exact qualified output plan/header required');target=a.out/Path(r['path']).name;target.write_bytes(Path(r['path']).read_bytes())
 typed=a.out/Path(outq['post_top2_output_Q4']['exact_typed_receipt']['path']).name;entry=once(entry,'#include "precision_overlay_receipt.h"','#include '+json.dumps(typed.as_posix()))
 for key in('precision_candidate','resident_all_Q8'):
  old=base[key]['scope'];new=outq[key]['scope'];require(literal(old)in entry,'Actual normal precision scope required');entry=entry.replace(literal(old),literal(new));seed[key]['scope']=new
 seed['precision_candidate'].update({k:v for k,v in outq['precision_candidate'].items()if k not in('actual_sources','commands')})
 entry=once(entry,'const auto header=qwen_app::receipt_integer(file,"header_bytes");','''const auto header=file.contains("header_bytes")?qwen_app::receipt_integer(file,"header_bytes"):
                        (file_index==76&&file.at("path")=="qwen-flash-next-bf16-00076-of-00076.gguf"&&
                         !plan->segments.empty()&&plan->segments.front().bytes==160?160ull:
                         throw std::runtime_error("Exact isolated output header boundary required"));''')
 for old,new in [('row["output_weight_type"]="Q8_0"','row["output_weight_type"]="Q4_0"'),('{"output_weight_type","Q8_0"}','{"output_weight_type","Q4_0"}')]:entry=entry.replace(old,new)
 old=base['next_five_normal']['scope'];scope=dict(old,original_GPU_object=False,selected_GPU_object_SHA256=g1['sha256'],resident_precision='109 large matrices including output Q4_0;remaining resident Q8_0 except original PLE BF16 and F32',output_weight_type='Q4_0',submission_node_cap=256,submission_flop_divisor=40,steady_CPU_heap_limit_bytes=536870912,obsolete_synchronized_metadata_released_before_replacement=True)
 entry=entry.replace(literal(old),literal(scope));seed['next_five_normal']['scope']=scope
 old=base['four_next_normal']['scope'];new=dict(old,original_GPU_object=False,loading_application_padding='qualified206',selected_GPU_object_SHA256=g1['sha256']);entry=entry.replace(literal(old),literal(new));seed['four_next_normal']['scope']=new
 selected={c[c.index('-o')+1]:c for c in recipes(base)if '-c'in c and '-o'in c and c[c.index('-o')+1]in base['link_command']}
 cs=[c for c in selected.values()if 'void llama_context::sched_new(size_t max_nodes, bool parallel)'in Path(c[c.index('-c')+1]).read_text()];require(len(cs)==1,'One actual normal checkpoint/context provider required');cc=cs[0];context=once(Path(cc[cc.index('-c')+1]).read_text(),'void llama_context::sched_new(size_t max_nodes, bool parallel) {','void llama_context::sched_new(size_t max_nodes, bool parallel) {\n    sched.reset();')
 context=once(context,'    gf_res_reserve.reset(new llm_graph_result(max_nodes));\n    gf_res_prev_active = nullptr;','    gf_res_prev_active=nullptr;gf_res_reserve.reset();\n    gf_res_reserve.reset(new llm_graph_result(max_nodes));')
 ms=[c for c in selected.values()if 'return limit_probe.required(free,minimum,reserved,legacy)-minimum;'in Path(c[c.index('-c')+1]).read_text()];require(len(ms)==1,'Actual normal loading provider required');mc=ms[0]
 memory='''#include <algorithm>
#include "post_top2_loading_reserve.h"
namespace {qwen_app::PostTop2LoadingReserve post_loading;}
extern "C" void qwen_post_loading_reserve_select(bool v){post_loading.select(v);}
extern "C" void qwen_post_loading_reserve_stats(std::uint64_t*out){const auto v=post_loading.stats();std::copy(v.begin(),v.end(),out);}
'''+Path(mc[mc.index('-c')+1]).read_text();memory=once(memory,'return limit_probe.required(free,minimum,reserved,legacy)-minimum;','return limit_probe.required(free,minimum,reserved,post_loading.extra(free,minimum,reserved,legacy))-minimum;')
 loading=dict(schema='ps5-qwen-post-top2-loading-reservation-v1',legacy_application_padding_pages=256,selected_loading_application_padding_pages=206,expected_OS_minimum_pages=898,expected_OS_reserved_pages=206,OS_counter_writes=0,physical_CPU_heap_device_ledger_workspace_and_GPU_completion_unchanged=True,once_only_between_loading_phase1_and2=True,no_unchanged_refused_launch_repeated=True,automatic_retries=0)
 entry='''#include "native_failure_journal.h"
#include <cstdint>
#include <array>
extern "C" void qwen_post_submit_select(bool);
extern "C" void qwen_post_submit_stats(std::uint64_t*);
extern "C" void qwen_post_loading_reserve_select(bool);
extern "C" void qwen_post_loading_reserve_stats(std::uint64_t*);
static std::array<std::uint64_t,22>post_submit_report(){std::array<std::uint64_t,22>v{};qwen_post_submit_stats(v.data());return v;}
static std::array<std::uint64_t,6>post_loading_report(){std::array<std::uint64_t,6>v{};qwen_post_loading_reserve_stats(v.data());return v;}
'''+entry
 entry=once(entry,'        const auto policy = Json::parse(policy_file);','        qwen_app::install_native_assertion_journal();\n        const auto policy = Json::parse(policy_file);')
 entry=once(entry,'        qwen_limit_probe_stage(1);','        if(policy.at("native_post_top2_loading_reserved")!=Json::parse('+literal(loading)+'))throw std::runtime_error("Exact qualified loading206 scope required");\n        qwen_limit_probe_stage(1);qwen_post_loading_reserve_select(true);')
 entry=once(entry,'        qwen_limit_probe_stage(2);','        qwen_post_loading_reserve_select(false);qwen_limit_probe_stage(2);')
 entry=once(entry,'        qwen_next_select(2);','        qwen_next_select(2);qwen_post_submit_select(true);')
 marker='{"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0}'
 entry=once(entry,marker,marker+',{ "prior_native_pack_seals_reused",qwen_post_pack_seals_reused()},{"post_top2_submission_counters",post_submit_report()},{"post_top2_loading_reservation",post_loading_report()}')
 seedpath=a.out/'normal-seed.private.json';write_json(seedpath,seed);r,jobs,sources=link(seedpath,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry),context=(cc,context),memory=(mc+['-I',str(ROOT/'native/app')],memory)),[Path(__file__),a.normal,a.submission,a.output,a.submission_proof,a.format_proof,a.loading_proof,typed,a.out/Path(outq['post_top2_output_Q4']['precision_plan']['path']).name,ROOT/'native/app/output_plain_segments.h',ROOT/'native/app/post_top2_loading_reserve.h',ROOT/'native/app/native_failure_journal.h'])
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['precision_candidate']['actual_sources'].update(sources);r['precision_candidate']['commands'].update(jobs);r['limit_defaults']['actual_sources']['entry']=sources['entry'];r['limit_defaults']['commands']['entry']=jobs['entry']
 for row in r['CPU_metadata_scope']['changed_sources']:
  if row['object_path']==mc[mc.index('-o')+1]:row.update(source=sources['memory'],object_path=jobs['memory'][jobs['memory'].index('-o')+1],command=jobs['memory'])
 for key in('four_next_normal','next_five_normal'):r[key].update(actual_sources=sources,commands=jobs,source_revision=revision,normal_qualification_pending=True,production_adopted=False)
 r['strata_followup_normal'].update(actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision);r['post_top2_loading_reserved']=dict(scope=loading,boundary_proof=record(a.loading_proof),actual_sources=sources,commands=jobs)
 r['post_top2_normal']=dict(scope=scope,source_revision=revision,actual_sources=sources,commands=jobs,submission_proof=record(a.submission_proof),format_proof=record(a.format_proof),GPU_object=g1,normal_qualification_pending=True,production_adopted=False)
 unsealed=a.out/'linked-seed.private.json';write_json(unsealed,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),source_revision=revision,scope=scope,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

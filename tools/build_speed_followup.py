#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded A/B/C/C/B/A native comparison from the installed providers."""
import argparse,copy,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from build_expert_quality_cohort import PROMPTS
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--confirmation',action='store_true',help='Finish both-order comparisons with B/C/B/A after the preserved initial A/B/C evidence')
 a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);requests=16 if a.confirmation else 24
 require(prior['resident_weight_normal']['active_slots']==3072,'Installed retained3072-slot normal provider required')
 ec=prior['compile_commands'][0];cc=prior['routing_sharing']['commands'][1];oc=prior['all_Q2_optimized_monitor']['commands'][1]
 entry=Path(ec[ec.index('-c')+1]).read_text();cache=Path(cc[cc.index('-c')+1]).read_text();owner=Path(oc[oc.index('-c')+1]).read_text()
 # Resolve the selected header according to the original command include order.
 folders=[Path(oc[oc.index('-c')+1]).parent]+[Path(oc[i+1])for i,x in enumerate(oc[:-1])if x=='-I']
 reader=next(f/'resident-mapped-source.private.h'for f in folders if(f/'resident-mapped-source.private.h').is_file())
 header=reader.read_text();header=once(header,'#include "mapped_source.h"','#include "mapped_source.h"\n#include "immutable_row_cache.h"\n#define QWEN_IMMUTABLE_ROW_CACHE 1')
 header=once(header,'#include "resident_small_rows.inc"','qwen_app::ImmutableRowCache row_cache_;bool row_cache_selected_=false;\nvoid select_row_cache(bool enabled,bool clear){require_completed_window();if(clear)row_cache_.clear();row_cache_selected_=enabled;}\nstd::array<std::uint64_t,2>row_cache_stats()const{return row_cache_.stats();}\n#include "resident_small_rows.inc"')
 hp=a.out/'speed-resident-source.private.h';hp.write_text(header,newline='\n')
 owner=once(owner,'#include "resident-mapped-source.private.h"','#include "speed-resident-source.private.h"')
 owner=once(owner,'    void cold_timing(', '    void delivery(std::uint64_t*out){if(!quad_)throw std::runtime_error("Live source pool required");auto s=quad_->delivery_timing();std::copy(s.begin(),s.end(),out);}\n    void cold_timing(')
 owner+='''
extern "C" void qwen_app_row_cache_select(bool enabled,bool clear){required().require_completed_window();ops.require_metadata_idle();required().select_row_cache(enabled,clear);}
extern "C" void qwen_app_row_cache_stats(std::uint64_t*out){auto s=required().row_cache_stats();std::copy(s.begin(),s.end(),out);}
extern "C" void qwen_app_delivery_timing(std::uint64_t*out){ops.delivery(out);}
'''
 # Unique include names prevent an old build directory shadowing a new header.
 owner=once(owner,'#include <streaming_read_pool.h>','#include "speed-streaming.private.h"')
 (a.out/'speed-streaming.private.h').write_bytes((ROOT/'native/app/streaming_read_pool.h').read_bytes())
 cache='#include "decode_prefill_protection.h"\nextern "C" bool qwen_app_route_is_decode();\nnamespace {qwen_app::DecodePrefillProtection speed_history;}\n'+cache
 cache=once(cache,'policy.victim(key_of, il, uniq)','policy.victim_avoiding(key_of, il, uniq, speed_history.keys(qwen_app_route_is_decode()))')
 cache=once(cache,'        if (adaptive) policy.observe(il, uniq);','        if (adaptive) policy.observe(il, uniq);\n        speed_history.observe(il,uniq,qwen_app_route_is_decode());')
 cache+='\nextern "C" void qwen_app_protection_begin(bool enabled,bool clear){speed_history.begin(enabled,clear);}\nextern "C" void qwen_app_protection_commit(){speed_history.commit();}\n'
 # Couple every route array and access to this exact finite request scope.
 scopes=[]
 for original in (prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']):
  new=dict(original,maximum_requests=requests,HTTP_requests=0,VideoOut_starts=0,headless_fixed_quality=True,quality_failures_recorded_without_aborting=True)
  entry=once(entry,literal(original),literal(new));scopes.append(new)
 scope,model,probation=scopes
 entry=once(entry,'const bool prefix_comparison=true;','const bool prefix_comparison=false;')
 entry=once(entry,'const unsigned request_count=3;','')
 entry=once(entry,'std::array<CompletedRouteEvidence,9> routes;','constexpr unsigned request_count='+str(requests)+';\n        std::array<CompletedRouteEvidence,request_count> routes;')
 sample_limit=requests*5+8
 entry=once(entry,'resident_reuse_VM[96]','resident_reuse_VM['+str(sample_limit)+']')
 entry=once(entry,'resident_reuse_VM_count>=96','resident_reuse_VM_count>='+str(sample_limit))
 entry=once(entry,'std::vector<float> reference_logits(resident_reference_rows*columns);','std::array<std::array<std::vector<std::string>,4>,2>speed_hashes;\n        std::array<std::array<std::vector<llama_token>,4>,2>speed_ids;\n        std::array<std::array<std::vector<unsigned char>,4>,2>speed_bytes;')
 declarations='''#include <cstdint>
extern "C" void qwen_app_select_weight_retention(bool);
extern "C" void qwen_app_row_cache_select(bool,bool);
extern "C" void qwen_app_row_cache_stats(std::uint64_t*);
extern "C" void qwen_app_delivery_timing(std::uint64_t*);
extern "C" void qwen_app_protection_begin(bool,bool);
extern "C" void qwen_app_protection_commit();
'''
 entry=declarations+entry
 prompt_header=a.out/'speed-prompts.private.h'
 prompt_header.write_text('inline const std::array<const char*,3>speed_prompts={'+','.join(json.dumps(x,ensure_ascii=False)for x in PROMPTS)+'};\n',encoding='utf-8',newline='\n')
 entry=once(entry,'using Json = nlohmann::json;','using Json = nlohmann::json;\n#include "speed-prompts.private.h"')
 start=entry.index('        const auto run_all_Q2_request=');end=entry.index('        run_all_Q2_request(0,',start);part=entry[start:end]
 part=once(part,'            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;','            const bool second=false;const unsigned phase=ordinal/4,task=ordinal%4;const unsigned arm=phase<3?phase:5-phase;const unsigned hash_arm=arm==2?1:0;const bool compare=phase>=(arm==2?3u:1u);const bool keep=task>0;')
 if a.confirmation:
  part=once(part,'const unsigned arm=phase<3?phase:5-phase;','const unsigned arm=phase==1?2:phase==3?0:1;')
  part=once(part,'const bool compare=phase>=(arm==2?3u:1u);','const bool compare=phase>=2;')
 part=once(part,'            const bool reuse=ordinal>0;','            const bool reuse=false;')
 part=once(part,'            const char *arm=ordinal==0?"ordinary-warmup":(second?"exact-prefix-and-causal-Expert-sharing":"ordinary-prefix-capture");','            const char *arm_name=arm==0?"control":arm==1?"owned-row-cache":"row-cache-and-decode-protection";')
 part=part.replace('{"arm",arm}', '{"arm",arm_name}')
 part=once(part,'                resident_reset_empty_context(context,model,startup.admission_report);','                qwen_app_select_weight_retention(keep);qwen_app_row_cache_select(arm>0,!keep);qwen_app_protection_begin(arm==2,!keep);\n                resident_reset_empty_context(context,model,startup.admission_report);')
 begin=part.index('            engine->set_logits_observer(');finish=part.index('            qwen_app::CausalExpertSharingEngine causal',begin)
 part=part[:begin]+'''            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                if(!v||count!=columns||rows>=resident_reference_rows){geometry_error=true;return;}
                for(std::size_t i=0;i<count;++i)if(!std::isfinite(v[i]))value_error=true;
                try{const auto hash=qwen_app::sha256_metadata_bytes(std::string(reinterpret_cast<const char*>(v),count*sizeof(float)));
                    auto&ref=speed_hashes[hash_arm][task];if(!compare)ref.push_back(hash);else if(rows>=ref.size()||ref[rows]!=hash)value_error=true;
                }catch(...){geometry_error=true;}++rows;
            });
'''+part[finish:]
 part=once(part,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t delivery_before[16]{},rows_before[2]{};qwen_app_delivery_timing(delivery_before);qwen_app_row_cache_stats(rows_before);\n            const auto perf=performance_snapshot(*engine);')
 part=once(part,'            const auto &result=trial.run(request,','            Json token_physical=Json::array();\n            const auto &result=trial.run(request,')
 part=once(part,'qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,32','qwen_app::render_bounded_user_prompt(chat_template,task?speed_prompts[task-1]:qwen_app::demo_prompt),256,32')
 part=once(part,'            },[&](const auto &token,const auto &m){','            },[&](const auto &token,const auto &m){\n                qwen_app_protection_commit();qwen_app::SourceReadLatency::Snapshot point{};qwen_app_source_read_latency(point.data(),point.size());token_physical.push_back({{"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms},{"physical_calls",point[0]-cold_reads_before[0]},{"physical_bytes",point[1]-cold_reads_before[1]}});')
 part=part.replace('(ordinal==1&&rows!=reference_rows)','(compare&&rows!=speed_hashes[hash_arm][task].size())')
 begin=part.index('            if(!ordinal){reference_ids=');end2=part.index('            routes[ordinal]=',begin)
 part=part[:begin]+'''            if(!compare){speed_ids[hash_arm][task]=result.token_ids;speed_bytes[hash_arm][task]=result.output_bytes;}
            else if(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task])
                throw std::runtime_error("Same-arm speed cohort output differs");
'''+part[end2:]
 part=once(part,'            if(ordinal==1)qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,result.request_reset_completed);','')
 part=part.replace('{"cache_initially_empty",ordinal==0}','{"cache_initially_empty",!keep}')
 part=part.replace('{"full_F32_logit_rows_compared",ordinal?rows:0}','{"full_F32_logit_rows_compared",compare?rows:0}')
 part=once(part,'row["same_tokens_as_independent"]=result.token_ids==reference_ids&&result.output_bytes==reference_bytes;','row["same_tokens_as_independent"]=result.token_ids==speed_ids[hash_arm][task]&&result.output_bytes==speed_bytes[hash_arm][task];')
 part=once(part,'            row["counting_quality_passed"]=counting_quality;','''            std::uint64_t delivery_after[16]{},rows_after[2]{};qwen_app_delivery_timing(delivery_after);qwen_app_row_cache_stats(rows_after);
            Json delta=Json::array();for(unsigned i=0;i<16;++i)delta.push_back(delivery_after[i]-delivery_before[i]);
            row["token_physical_snapshots"]=token_physical;row["delivery_timing_delta"]=delta;row["owned_row_cache"]={{"enabled",arm>0},{"hits",rows_after[0]-rows_before[0]},{"misses",rows_after[1]-rows_before[1]},{"payload_bytes",491520},{"owned_allocation_bytes",525344}};
            row["phase"]=phase;row["candidate_arm"]=arm;row["quality_task"]=task;row["independent_repeat"]=compare;row["weights_retained"]=keep;
            row["counting_quality_passed"]=counting_quality;''')
 part=once(part,'            if(!counting_quality)throw std::runtime_error("Completed all-Expert Q2 counting response failed normal-app quality");','            // Raw task formatting is graded after a positively completed trial.')
 at=part.index('            if(ordinal){\n                if(!result.metrics.decode_tokens_per_second');finish=part.index('            return row;',at);part=part[:at]+part[finish:]
 entry=entry[:start]+part+entry[end:]
 start=entry.index('        run_all_Q2_request(0,');end=entry.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',start)
 entry=entry[:start]+'        for(unsigned i=0;i<request_count;++i)run_all_Q2_request(i,[]{return true;},[](const Json&){});\n        const Json demo={{"headless_fixed_quality",true}};\n'+entry[end:]
 entry=once(entry,'{"HTTP_requests",2},{"VideoOut_starts",1},{"passive_monitor_and_API_completed",true},{"optimized_delivery_and_final_prefix_handoff_completed",true}','{"HTTP_requests",0},{"VideoOut_starts",0},{"headless_fixed_quality_completed",true},{"optimized_delivery_and_final_prefix_handoff_completed",false}')
 entry=once(entry,'{"cache_slots",867}','{"cache_slots",3072}')
 entry=once(entry,'{"cache_reset_before_request",!prefix_comparison||!i||i%2!=0}','{"cache_reset_before_request",i%4==0}')
 entry=entry.replace('Same-policy independent full F32 and ordered routes','Exact full-row SHA256 within matched cache state; protection arm has a separate reference')
 for expr in ('ordinal','i'):entry=entry.replace('routes['+expr+']','routes.at('+expr+')')
 require('routes['not in entry,'Every route access must be bounded')
 result,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),cache=(cc,cache),owner=(oc,owner)),[Path(__file__),reader,hp,prompt_header,*[ROOT/'native/app'/n for n in ('decode_prefill_protection.h','indexed_probation_policy.h','immutable_row_cache.h','resident_small_rows.inc','streaming_read_pool.h')]])
 for key in ('normal_performance','output_Q8_normal'):result[key].update(scope=scope,model_scope=model)
 result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model
 for key in ('routing_sharing','routing_winners_normal'):result[key].update(scope=scope,model_scope=model)
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry'],actual_owner=sources['owner']);result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['all_Q2_optimized_monitor']['commands'][1]=jobs['owner'];result['routing_winners_normal']['actual_entry']=sources['entry']
 result['memory_quality_cohort']=dict(scope=scope,model_scope=model,requests=requests,independent_pairs=requests//2,actual_sources=sources,commands=jobs,HTTP_requests=0,VideoOut_starts=0)
 result['small_rows_cohort']=dict(requests=requests,fixed_tasks=4,scalar_then_batch=False)
 result['speed_followup']=dict(schema='ps5-qwen-speed-followup-v1',requests=requests,phases=['B','C','B','A']if a.confirmation else['A','B','C','C','B','A'],fixed_tasks=4,protection_cap=1536,VM_sample_capacity=sample_limit,original_reserves_preserved=True,production_adopted=False,reader=record(hp))
 result['cold_request']['source_header']=record(hp)
 seal(result,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_speed_followup',original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose qualified Q2 delivery wins and a bounded final-prefix handoff."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from build_expert_q2_probation_monitor import SCOPE as PROBATION_SCOPE
from expert_all_q2_monitor_source import MONITOR_SCOPE as OLD_MODEL_SCOPE
from expert_q2_reader_candidates import candidate_header
from build_expert_q2_reader_comparison import owner_source as reader_owner
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-Q2-optimized-monitor-v1',enabled=True,maximum_requests=3,HTTP_requests=2,VideoOut_starts=1,
 expert_eviction_policy='two_touch_probation',active_cache_slots=867,cache_budget_bytes=1333739520,
 immutable_range_hint=True,partial_bundles=336,first_API='ordinary_and_complete_prefix_capture',
 final_API='exact_prefix_restore_then_one_causal_Expert_sharing_attempt',maximum_speculative_attempts=1,
 final_consumer_handoff_only=True,ordinary_full_F32_exact_required=True,unlike_width_full_vocab_finite_and_top1_equal_required=True,
 original_weight_precision_and_driver_preserved=True,persistent_caches_enabled=False,automatic_retries=0)
MODEL_SCOPE=dict(OLD_MODEL_SCOPE,schema='ps5-qwen-Q2-optimized-monitor-model-v1',
 full_same_Q2_F32_rows_and_routes_required=False,same_width_full_F32_and_routes_required=True,
 final_unlike_width_full_vocabulary_finite_top1_and_same_tokens_required=True)
def literal(v):return json.dumps(json.dumps(v,separators=(',',':')))
def engine_source(text):
 text='#include <prefix_speculative_handoff.h>\n'+text
 marker='void LlamaEngine::enable_speculative_step_prototype(std::function<void(std::uint64_t)> admit) {\n    require_healthy();'
 return once(text,marker,marker+'''
    if(final_prefix_handoff.pending(this,context_)){
        if(producer_!=std::this_thread::get_id()||failed_||!checkpoint_||!checkpoint_->saved()||!ready_||position_!=30||
           pending_!=LLAMA_TOKEN_NULL||!prefix_stats_.enabled||!prefix_stats_.request_hit||prefix_stats_.captures!=1||
           prefix_stats_.restores!=1||prefix_stats_.last_reused_prompt_tokens!=30||checkpoint_stats_.enabled||speculative_stats_.enabled||
           !admit||!gpu_begin_||!gpu_complete_||!gpu_retain_||!gpu_checkpoint_)
            throw std::runtime_error("Final Q2 prefix handoff requires its exact positively restored complete state");
        final_prefix_handoff.consume(this,context_,checkpoint_->payload_bytes(),position_);
        checkpoint_admit_=std::move(admit);speculative_stats_.enabled=true;return;
    }
''')
def entry_source(text):
 text='''#include <expert_q2_speculative.h>
#include <prefix_speculative_handoff.h>
extern "C" void qwen_app_select_Q2_bundle(bool);
extern "C" std::uint64_t qwen_app_Q2_bundle_hits();
extern "C" void qwen_app_select_Q2_reader(unsigned);
extern "C" void qwen_app_Q2_reader_stats(std::uint64_t*);
'''+text
 text=once(text,literal(OLD_MODEL_SCOPE),literal(MODEL_SCOPE))
 text=once(text,'        const bool prefix_comparison=false;','        const bool prefix_comparison=true;')
 text=once(text,'        const unsigned request_count=3;','        if(policy.at("native_Expert_Q2_optimized_monitor")!=Json::parse('+literal(SCOPE)+'))throw std::runtime_error("Exact optimized Q2 monitor scope required");\n        const unsigned request_count=3;')
 text=once(text,'            const bool reuse=prefix_comparison&&ordinal>0&&(group==1||group==2);','            const bool reuse=ordinal>0;')
 text=once(text,'            const char *arm=ordinal==0?"warmup":(refill?"six-demand":"ordinary");','            const char *arm=ordinal==0?"ordinary-warmup":(second?"exact-prefix-and-causal-Expert-sharing":"ordinary-prefix-capture");\n            qwen_app_select_Q2_reader(1);qwen_app_select_Q2_bundle(true);\n            const auto bundles_before=qwen_app_Q2_bundle_hits();std::uint64_t hint_before[3]{};qwen_app_Q2_reader_stats(hint_before);')
 text=once(text,'            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);','            const auto rounded=qwen_app::final_prefix_handoff.new_allocation(context,bytes);\n            if(qwen_app::final_prefix_handoff.consumed()){const auto memory=qwen_app::observe_native_system_memory();if(memory.kernel_minimum!=898||memory.kernel_reserved!=206||memory.kernel_free<981)throw qwen_app::KernelMemoryPressure();}')
 text=once(text,'if(!std::isfinite(a)||!std::isfinite(b)||e>1e-5+1e-5*std::abs(b))value_error=true;','if(!std::isfinite(a)||!std::isfinite(b)||(ordinal!=2&&e>1e-5+1e-5*std::abs(b)))value_error=true;')
 text=once(text,'                ++rows;\n            });','                if(ordinal==2&&std::max_element(v,v+count)-v!=std::max_element(reference_logits.data()+rows*columns,reference_logits.data()+(rows+1)*columns)-(reference_logits.data()+rows*columns))value_error=true;\n                ++rows;\n            });')
 text=once(text,'            qwen_app::FirstGeneration trial(*engine);','''            qwen_app::ExpertQ2SpeculativeEngine causal(*engine,model,context,second);
            class FinalConsumer final:public qwen_app::Engine{
                qwen_app::ExpertQ2SpeculativeEngine&causal;qwen_app::LlamaEngine&e;llama_context*c;bool final;std::function<void(std::uint64_t)>admit;
            public:
                FinalConsumer(qwen_app::ExpertQ2SpeculativeEngine&a,qwen_app::LlamaEngine&v,llama_context*x,bool f,std::function<void(std::uint64_t)>g):causal(a),e(v),c(x),final(f),admit(std::move(g)){}
                std::uint32_t tokenize(const std::string&s)override{return causal.tokenize(s);}
                void prefill(std::uint32_t n)override{causal.prefill(n);if(final){const auto p=e.prefix_reuse_stats();qwen_app::final_prefix_handoff.arm(&e,c,2,p.request_hit&&p.restores==1&&p.last_reused_prompt_tokens==30);e.enable_speculative_step_prototype(admit);}}
                qwen_app::Token next()override{return causal.next();}void finish()override{causal.finish();}
                std::optional<qwen_app::ExpertCacheMetrics>expert_cache_metrics()const override{return e.expert_cache_metrics();}
            }consumer(causal,*engine,context,second,admit_checkpoint);
            qwen_app::FirstGeneration trial(consumer);''')
 start=text.index('            if(ordinal){const auto&a=routes[0],&b=routes[ordinal];')
 end=text.index('            const auto p=engine->prefix_reuse_stats();',start)
 text=text[:start]+'''            if(ordinal){const auto&a=routes[0],&b=routes[ordinal];const std::size_t offset=second?8*48:0;
                if(!second&&a.rows.size()!=b.rows.size())throw std::runtime_error("Ordinary optimized Q2 route geometry differs");
                for(std::size_t i=0;i<b.rows.size();++i){if(second&&b.rows[i].tokens!=1)break;
                    if(i+offset>=a.rows.size()||a.rows[i+offset].layer!=b.rows[i].layer||a.rows[i+offset].tokens!=b.rows[i].tokens||
                       !std::equal(a.rows[i+offset].ids.begin(),a.rows[i+offset].ids.begin()+10*b.rows[i].tokens,b.rows[i].ids.begin()))
                        throw std::runtime_error("Optimized Q2 ordinary/prefix continuation routes differ before the first mixed-width graph");}}
'''+text[end:]
 start=text.index('            if(second) {\n                const auto &first=routes[ordinal-1]')
 end=text.index('            require_model_CPU_budget();require_unchanged_model();',start)
 text=text[:start]+'''            const auto speculative=engine->speculative_step_stats();
            if(ordinal==1)qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,result.request_reset_completed);
            if(second&&(!qwen_app::final_prefix_handoff.consumed()||speculative.attempts!=1||speculative.accepted!=1||speculative.rejected||speculative.queued_bonus_samples!=1))
                throw std::runtime_error("Final Q2 consumer requires one completed causal target acceptance and bonus");
'''+text[end:]
 text=once(text,'            row["counting_quality_passed"]=counting_quality;','''            std::uint64_t hints[3]{};qwen_app_Q2_reader_stats(hints);
            row["bundled_Experts"]=qwen_app_Q2_bundle_hits()-bundles_before;row["range_hint_hits"]=hints[0]-hint_before[0];
            row["F32_comparison_scope"]=second?"unlike-width complete-vocabulary finite values and identical top1; same-width qualification is case 9160":"ordinary same-width full-F32 tolerance and ordered routes";
            row["speculation"]={{"attempts",speculative.attempts},{"accepted",speculative.accepted},{"rejected",speculative.rejected},{"queued_bonus_samples",speculative.queued_bonus_samples},{"causal_proposals",causal.causal_proposals}};
            row["counting_quality_passed"]=counting_quality;''')
 text=once(text,'{"passive_monitor_and_API_completed",true},{"demo",demo}',
  '{"passive_monitor_and_API_completed",true},{"optimized_delivery_and_final_prefix_handoff_completed",true},{"unlike_width_bit_equality_required",false},{"demo",demo}')
 return text
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','bundle-build','engine-build','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());bundle=json.loads(a.bundle_build.read_text());engine_parent=json.loads(a.engine_build.read_text());require(prior['all_Q2_probation_monitor']['scope']==PROBATION_SCOPE,'Qualified passive probation parent required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+active_link_inputs(bundle)+[record(x)for x in (a.parent,a.bundle_build,a.engine_build,Path(__file__),ROOT/'native/app/expert_q2_speculative.h',ROOT/'native/app/prefix_speculative_handoff.h',ROOT/'tools/expert_q2_reader_candidates.py')]
 for r in frozen:require(record(r['path'])==r,'Exact composed input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();original=Path(prior['expert_q2_model']['actual_entry']['path']);entry=a.out/'entry.private.cpp';entry.write_text(entry_source(original.read_text()),newline='\n')
 oldowner=bundle['all_Q2_IO_measurement']['owner'];owner=a.out/'owner.private.cpp';owner.write_text(reader_owner(Path(oldowner['path']).read_text()),newline='\n')
 bh=bundle['all_Q2_bundle_comparison']['actual_header'];header=a.out/'resident-mapped-source.private.h';header.write_text(candidate_header(Path(bh['path']).read_text()),newline='\n')
 plan=a.out/'Q2-bundle-plan.private.h';plan.write_bytes((Path(oldowner['path']).parent/plan.name).read_bytes())
 er=next(r for r in engine_parent['additional_cache_geometry']['compiled']if Path(r['compiled_source']['path']).name=='llama_engine.cpp');require(prior['link_command'].count(er['object']['path'])==1,'Exact actual selected engine override required');require(record(er['compiled_source']['path'])==er['compiled_source'],'Actual engine source changed')
 engine=a.out/'llama_engine.final-prefix.private.cpp';engine.write_text(engine_source(Path(er['compiled_source']['path']).read_text()),newline='\n')
 jobs=[];objects=[];replace={}
 for label,src,base,origin in [('entry',entry,prior['compile_commands'][0],original),('owner',owner,bundle['all_Q2_IO_measurement']['commands'][1],Path(oldowner['path'])),('engine',engine,er['command'],Path(er['compiled_source']['path']))]:
  cmd=base.copy();old=cmd[cmd.index('-o')+1];obj=a.out/(label+'.o');cmd[cmd.index('-c')+1]=str(src);cmd[cmd.index('-o')+1]=str(obj);cmd[1:1]=['-I',str(origin.parent)]
  if label=='engine':cmd[1:1]=['-I',str(ROOT/'native/app')]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(label+'.private.d'))
  if label=='owner':old=prior['all_Q2_payload_preflight']['object']['path']
  require(prior['link_command'].count(old)==1,'One actual composed object required: '+old);replace[old]=str(obj);jobs.append(cmd);objects.append(obj)
 cache_cmd=bundle['expert_q2_model']['commands'][1];cache=cache_cmd[cache_cmd.index('-o')+1];old_cache=prior['expert_q2_model']['commands'][1];old_cache=old_cache[old_cache.index('-o')+1];require(prior['link_command'].count(old_cache)==1,'Exact cache override required');replace[old_cache]=cache
 image=a.out/'qwen-native.pie.elf';link=[replace.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 pinned=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/llama-context.cpp';writer=pinned.read_text();segment=writer[writer.index('class llama_io_write_device'):writer.index('class llama_io_read_device')];require(segment.index('mbuf_cur = std::move(mbuf);')<segment.index('mbuf_cur.buf.reset(ggml_backend_alloc_ctx_tensors_from_buft'),'Pinned changed-payload writer must release old snapshot before allocation')
 for i,cmd in enumerate(jobs+[link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-6000:]);print(json.dumps(dict(optimized_monitor_build_step=i+1,total=4)),flush=True)
 frozen +=[record(x)for x in [entry,owner,engine,header,plan,pinned,*objects]]
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[jobs[0]],link_command=link,source_parent=record(a.parent),inputs_before=list({r['path']:r for r in frozen}.values()),lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=MODEL_SCOPE,actual_entry=record(entry),actual_cache=bundle['expert_q2_model']['actual_cache'],reader_header=record(header),commands=[jobs[0],cache_cmd],normal_application_validation_pending=True)
 receipt['all_Q2_optimized_monitor']=dict(scope=SCOPE,commands=jobs,actual_entry=record(entry),actual_owner=record(owner),actual_engine=record(engine),actual_reader=record(header),bundle_pack=bundle['all_Q2_bundle_comparison']['pack'],only_final_consumer_may_replace_prefix_snapshot=True,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(optimized_monitor_built=True,normal_qualification_pending=True,PS5_operations=0)))
if __name__=='__main__':main()

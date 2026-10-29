#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build causal Expert-sharing Q2 ABBA and a separate full-state rejection control."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from build_expert_q2_policy_comparison import POLICY_SCOPE as OLD_SCOPE,MODEL_SCOPE as OLD_MODEL,IO_SCOPE as OLD_IO
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-all-Q2-Expert-sharing-speculative-ABBA-v1',enabled=True,maximum_requests=6,warmup_requests=1,
 order=['causal_warmup','ordinary','causal','causal','ordinary','forced_rejection_diagnostic'],maximum_actual_attempts_per_request=1,
 expert_eviction_policy='two_touch_probation',active_cache_slots=867,cache_budget_bytes=1333739520,
 complete_F32_KV_recurrent_positions_logits_and_application_state=True,causal_past_token_and_Expert_route_proposals_only=True,
 same_width_full_F32_and_routes_required=True,cross_width_F32_bit_equality_required=False,forced_rejection_full_ordinary_F32_required=True,
 rejected_work_and_snapshot_costs_charged=True,original_GPU_math_unchanged=True,automatic_retries=0)
MODEL_SCOPE=dict(OLD_MODEL,schema='ps5-qwen-all-Q2-speculative-model-v1',maximum_requests=6,timed_requests=4)
IO_SCOPE=dict(OLD_IO,schema='ps5-qwen-all-Q2-speculative-IO-v1',maximum_requests=6)
def literal(v):return json.dumps(json.dumps(v,separators=(',',':')))
def entry_source(text):
 text='#include "expert_q2_speculative.h"\n#include "resident_checkpoint_capacity.h"\n'+text
 for before,after in ((OLD_SCOPE,SCOPE),(OLD_MODEL,MODEL_SCOPE),(OLD_IO,IO_SCOPE)):text=once(text,literal(before),literal(after))
 text=once(text,'policy.at("native_Expert_Q2_policy_comparison")','policy.at("native_Expert_Q2_speculative_comparison")')
 text=once(text,'        const unsigned request_count=5;','        const unsigned request_count=6;')
 text=once(text,'            const bool probation=ordinal==2||ordinal==3;','            const bool probation=true;\n            const bool speculate=ordinal==0||ordinal==2||ordinal==3,forced_rejection=ordinal==5;')
 text=once(text,'(probation?"two-touch-probation":"aged-lfu-control")','(forced_rejection?"forced-rejection-diagnostic":(speculate?"causal-Expert-sharing":"ordinary"))')
 text=once(text,'        Json completed=Json::array();','        Json completed=Json::array();\n        qwen_app::ResidentCheckpointCapacity checkpoint_capacity;\n        std::uint64_t last_snapshot_bytes=0;\n        std::vector<float> ordinary_reference_logits(resident_reference_rows*columns);\n        std::size_t ordinary_reference_rows=0;unsigned rejection_history=0;')
 text=once(text,'            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);','            const auto rounded=checkpoint_capacity.new_allocation(context,bytes);last_snapshot_bytes=bytes;')
 text=once(text,'                if(reuse)engine->enable_prefix_reuse(admit_checkpoint);','                if(speculate||forced_rejection)engine->enable_speculative_step_prototype(admit_checkpoint);')
 text=once(text,'                if(ordinal==0){std::copy(v,v+count,reference_logits.data()+rows*columns);++reference_rows;}','                auto&reference=speculate?reference_logits:ordinary_reference_logits;\n                auto&expected_rows=speculate?reference_rows:ordinary_reference_rows;\n                if(ordinal==0||ordinal==1){std::copy(v,v+count,reference.data()+rows*columns);++expected_rows;}')
 text=once(text,'if(rows>=reference_rows){geometry_error=true;return;}','if(rows>=expected_rows){geometry_error=true;return;}')
 text=once(text,'b=reference_logits[rows*columns+i]','b=reference[rows*columns+i]')
 text=once(text,'            qwen_app::FirstGeneration trial(*engine);','            const llama_token rejected_draft=forced_rejection?(reference_ids.at(rejection_history)==0?1:0):-1;\n            qwen_app::ExpertQ2SpeculativeEngine causal(*engine,model,context,speculate,rejected_draft,forced_rejection?rejection_history:2);\n            qwen_app::FirstGeneration trial(causal);')
 text=once(text,'(ordinal&&rows!=reference_rows)','(ordinal>1&&rows!=(speculate?reference_rows:ordinary_reference_rows))')
 old='            if(ordinal){const auto&a=routes[0],&b=routes[ordinal];\n                if(a.rows.size()!=b.rows.size())throw std::runtime_error("Repeated Q2 route row count differs");\n                for(std::size_t i=0;i<a.rows.size();++i)if(a.rows[i].layer!=b.rows[i].layer||a.rows[i].tokens!=b.rows[i].tokens||\n                    !std::equal(a.rows[i].ids.begin(),a.rows[i].ids.begin()+10*a.rows[i].tokens,b.rows[i].ids.begin()))\n                    throw std::runtime_error("Repeated Q2 original Expert selections differ");}'
 replacement='            if(ordinal>1){const auto&a=routes[speculate?0:1],&b=routes[ordinal];\n                const std::size_t extra=forced_rejection?48:0,at=(8+rejection_history-1)*48;\n                if(a.rows.size()+extra!=b.rows.size())throw std::runtime_error("Same-mode Q2 route row count differs");\n                for(std::size_t i=0;i<a.rows.size();++i){const auto&other=b.rows[i+(forced_rejection&&i>=at?extra:0)];\n                    if(a.rows[i].layer!=other.layer||a.rows[i].tokens!=other.tokens||\n                        !std::equal(a.rows[i].ids.begin(),a.rows[i].ids.begin()+10*a.rows[i].tokens,other.ids.begin()))\n                        throw std::runtime_error("Same-mode Q2 Expert selections differ");}}\n            const auto speculative=engine->speculative_step_stats();const auto checkpoint=engine->checkpoint_validation_stats();\n            if(ordinal==0){if(checkpoint.captures!=1||checkpoint.capture_positions[0]<30||checkpoint.capture_positions[0]>59)throw std::runtime_error("One causal Q2 snapshot required for same-position rejection coverage");rejection_history=unsigned(checkpoint.capture_positions[0]-30+1);}\n            if(checkpoint.captures)checkpoint_capacity.completed(context,last_snapshot_bytes,result.request_reset_completed);\n            if((!speculate&&!forced_rejection&&speculative.attempts)||speculative.attempts>1||\n               (forced_rejection&&(speculative.rejected!=1||speculative.accepted)))\n                throw std::runtime_error("Q2 causal or explicit rejection coverage differs");'
 text=once(text,old,replacement)
 text=once(text,'{"expert_eviction_policy",probation?"two_touch_probation":"aged_lfu"}','{"expert_eviction_policy","two_touch_probation"},{"causal_speculation",speculate},{"forced_rejection_diagnostic",forced_rejection}')
 text=once(text,'{"full_F32_logit_rows_compared",ordinal?rows:0}','{"full_F32_logit_rows_compared",ordinal>1?rows:0}')
 text=once(text,'            row["counting_quality_passed"]=counting_quality;', '            row["speculation"]={{"attempts",speculative.attempts},{"accepted",speculative.accepted},{"rejected",speculative.rejected},\n                {"causal_proposals",causal.causal_proposals},{"past_ordinary_route_observations",causal.ordinary_observations},\n                {"snapshot_captures",checkpoint.captures},{"snapshot_restores",checkpoint.restores},{"snapshot_payload_bytes",checkpoint.maximum_payload_bytes},\n                {"ending_minimum",causal.ending_minimum},{"ending_maximum",causal.ending_maximum}};\n            row["counting_quality_passed"]=counting_quality;')
 return once(text,'{"completed_policy_comparison",true}','{"completed_speculative_comparison",true},{"full_F32_comparison_scope","same-width plus forced-rejection ordinary continuation"}')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['all_Q2_policy_comparison']['scope']==OLD_SCOPE,'Qualified exact Q2 control required')
 frozen=[record(ROOT/'native/app/expert_q2_speculative.h'),record(ROOT/'native/app/llama_engine.h'),record(ROOT/'native/app/resident_checkpoint_capacity.h')]+active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__)]
 for r in frozen:require(record(r['path'])==r,'Qualified input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();snapshot=a.out/'generator.private.py';snapshot.write_bytes(Path(__file__).read_bytes())
 original=Path(prior['expert_q2_model']['actual_entry']['path']);source=a.out/'entry.private.cpp';source.write_text(entry_source(original.read_text()),newline='\n')
 command=prior['compile_commands'][0].copy();old_obj=command[command.index('-o')+1];obj=a.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(original.parent)]
 if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'entry.private.d')
 require(prior['link_command'].count(old_obj)==1,'Exact selected entry required');image=a.out/'qwen-native.pie.elf';link=[str(obj)if x==old_obj else x for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate((command,link)):
  r=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-5000:]);print(json.dumps(dict(speculative_build_step=i+1,total=2)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen input changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[command],source_parent=record(a.parent),inputs_before=frozen+[record(snapshot),record(source),record(obj)],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=MODEL_SCOPE,actual_entry=record(source),commands=[command,prior['expert_q2_model']['commands'][1]])
 receipt['all_Q2_IO_measurement'].update(scope=IO_SCOPE,entry=record(source))
 receipt['all_Q2_speculative_comparison']=dict(scope=SCOPE,model_scope=MODEL_SCOPE,IO_scope=IO_SCOPE,only_entry_object_changed=True,source_owner_GPU_cache_math_and_complete_state_implementation_unchanged=True,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(speculative_comparison_built=True,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()

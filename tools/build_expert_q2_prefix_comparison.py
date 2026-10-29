#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a matched warm-cache exact-prefix ABBA on the actual Q2 model."""
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
SCOPE=dict(schema='ps5-qwen-all-Q2-prefix-ABBA-v1',enabled=True,maximum_requests=9,warmup_requests=1,
 groups=['ordinary','exact_prefix','exact_prefix','ordinary'],requests_per_group=2,
 expert_eviction_policy='two_touch_probation',active_cache_slots=867,cache_budget_bytes=1333739520,
 complete_F32_KV_recurrent_positions_logits_and_application_state=True,exact_complete_prompt_required=True,
 TTFT_and_capture_cost_reported_separately=True,original_GPU_math_unchanged=True,automatic_retries=0)
MODEL_SCOPE=dict(OLD_MODEL,schema='ps5-qwen-all-Q2-prefix-model-v1',maximum_requests=9,timed_requests=8)
IO_SCOPE=dict(OLD_IO,schema='ps5-qwen-all-Q2-prefix-IO-v1',maximum_requests=9)
def literal(v):return json.dumps(json.dumps(v,separators=(',',':')))
def entry_source(text):
 text='#include "resident_checkpoint_capacity.h"\n'+text
 for before,after in ((OLD_SCOPE,SCOPE),(OLD_MODEL,MODEL_SCOPE),(OLD_IO,IO_SCOPE)):text=once(text,literal(before),literal(after))
 text=once(text,'policy.at("native_Expert_Q2_policy_comparison")','policy.at("native_Expert_Q2_prefix_comparison")')
 text=once(text,'        const bool prefix_comparison=false;','        const bool prefix_comparison=true;')
 text=once(text,'        const unsigned request_count=5;','        const unsigned request_count=9;')
 text=once(text,'            const bool probation=ordinal==2||ordinal==3;','            const bool probation=true;')
 text=once(text,'(probation?"two-touch-probation":"aged-lfu-control")','(reuse?"exact-prefix":"ordinary-warm-cache-control")')
 text=once(text,'        const auto admit_checkpoint=[&](std::uint64_t bytes){','        qwen_app::ResidentCheckpointCapacity checkpoint_capacity;\n        std::uint64_t last_snapshot_bytes=0;\n        const auto admit_checkpoint=[&](std::uint64_t bytes){')
 text=once(text,'            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);','            const auto rounded=checkpoint_capacity.new_allocation(context,bytes);last_snapshot_bytes=bytes;')
 text=once(text,'            const auto p=engine->prefix_reuse_stats();','            const auto p=engine->prefix_reuse_stats();\n            if(p.captures&&!second)checkpoint_capacity.completed(context,last_snapshot_bytes,result.request_reset_completed);')
 # Complete-prefix restoration removes eight prefill graph invocations. Compare
 # every remaining ordered route against its corresponding reference position.
 text=once(text,'if(a.rows.size()!=b.rows.size())throw std::runtime_error("Repeated Q2 route row count differs");',
  'const std::size_t offset=reuse&&second?8u*48u:0u;\n                if(a.rows.size()!=offset+b.rows.size())throw std::runtime_error("Repeated Q2 route row count differs");')
 text=once(text,'for(std::size_t i=0;i<a.rows.size();++i)if(a.rows[i].layer!=b.rows[i].layer||a.rows[i].tokens!=b.rows[i].tokens||\n                    !std::equal(a.rows[i].ids.begin(),a.rows[i].ids.begin()+10*a.rows[i].tokens,b.rows[i].ids.begin()))',
  'for(std::size_t i=0;i<b.rows.size();++i)if(a.rows[i+offset].layer!=b.rows[i].layer||a.rows[i+offset].tokens!=b.rows[i].tokens||\n                    !std::equal(a.rows[i+offset].ids.begin(),a.rows[i+offset].ids.begin()+10*a.rows[i+offset].tokens,b.rows[i].ids.begin()))')
 return once(text,'{"completed_policy_comparison",true}','{"completed_prefix_comparison",true}')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['all_Q2_policy_comparison']['scope']==OLD_SCOPE,'Qualified exact Q2 control required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__)]
 for r in frozen:require(record(r['path'])==r,'Qualified input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();snapshot=a.out/'generator.private.py';snapshot.write_bytes(Path(__file__).read_bytes())
 original=Path(prior['expert_q2_model']['actual_entry']['path']);source=a.out/'entry.private.cpp';source.write_text(entry_source(original.read_text()),newline='\n')
 command=prior['compile_commands'][0].copy();old_obj=command[command.index('-o')+1];obj=a.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(original.parent)]
 if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'entry.private.d')
 require(prior['link_command'].count(old_obj)==1,'Exact selected entry required');image=a.out/'qwen-native.pie.elf';link=[str(obj)if x==old_obj else x for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate((command,link)):
  r=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-5000:]);print(json.dumps(dict(prefix_build_step=i+1,total=2)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen input changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[command],source_parent=record(a.parent),inputs_before=frozen+[record(snapshot),record(source),record(obj)],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=MODEL_SCOPE,actual_entry=record(source),commands=[command,prior['expert_q2_model']['commands'][1]])
 receipt['all_Q2_IO_measurement'].update(scope=IO_SCOPE,entry=record(source))
 receipt['all_Q2_prefix_comparison']=dict(scope=SCOPE,model_scope=MODEL_SCOPE,IO_scope=IO_SCOPE,only_entry_object_changed=True,source_owner_GPU_cache_math_and_complete_state_implementation_unchanged=True,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(prefix_comparison_built=True,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()

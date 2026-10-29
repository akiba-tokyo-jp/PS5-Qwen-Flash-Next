#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare two coherent CPU-copy thresholds with the adopted Q2 cache fixed."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from build_expert_q2_policy_comparison import POLICY_SCOPE as OLD_SCOPE
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-all-Q2-enabled-small-copy-ABBA-v2',enabled=True,maximum_requests=5,warmup_requests=1,
    order=['control','control','small_copy','small_copy','control'],control_minimum_bytes=1<<20,
    candidate_minimum_bytes=256<<10,expert_eviction_policy='two_touch_probation',active_cache_slots=867,
    cache_budget_bytes=1333739520,original_GPU_math_and_IO_schedule_unchanged=True,
    original_host_visible_coherent_owner_and_sfence_required=True,
    control_streaming_copy_enabled=False,candidate_streaming_copy_enabled=True,automatic_retries=0)

def entry_source(text):
 text='extern "C" void qwen_app_select_Q2_small_copy(bool);\n'+text
 text=once(text,json.dumps(json.dumps(OLD_SCOPE,separators=(',',':'))),json.dumps(json.dumps(SCOPE,separators=(',',':'))))
 text=once(text,'policy.at("native_Expert_Q2_policy_comparison")','policy.at("native_Expert_Q2_copy_comparison")')
 text=once(text,'                qwen_app_select_Q2_probation(probation);',
  '                qwen_app_select_Q2_probation(true);\n                qwen_app_select_Q2_small_copy(probation);')
 text=once(text,'(probation?"two-touch-probation":"aged-lfu-control")','(probation?"small-streaming-copy":"original-copy-threshold")')
 text=once(text,'{"expert_eviction_policy",probation?"two_touch_probation":"aged_lfu"}',
  '{"expert_eviction_policy","two_touch_probation"},{"small_copy_candidate",probation}')
 marker='    if (source.schedule_enabled) result.update({'
 text=once(text,marker,'''    const auto copied=qwen_app::mapped_copy_stats();
    result["mapped_streaming_write_bytes"]=copied.bytes;
    result["mapped_streaming_write_calls"]=copied.calls;
'''+marker)
 return once(text,'{"completed_policy_comparison",true}', '{"completed_copy_comparison",true}')

def threshold_header(text):
 marker='inline std::atomic<bool> mapped_copy_configured{false},mapped_copy_scope{false};'
 text=once(text,marker,marker+'\ninline std::atomic<std::size_t> Q2_copy_minimum_bytes{1u<<20};')
 return once(text,'bytes<(1u<<20)','bytes<Q2_copy_minimum_bytes.load(std::memory_order_relaxed)')

def owner_source(text):
 return text+'''
extern "C" void qwen_app_select_Q2_small_copy(bool enabled){
    const auto state=qwen_app::native_model_source_stats();
    if(state.chunks!=state.completed_windows)
        throw std::runtime_error("Copy threshold requires all prior source windows completed");
    qwen_app::configure_mapped_copy(enabled);
    qwen_app::Q2_copy_minimum_bytes.store(enabled?(256u<<10):(1u<<20),std::memory_order_relaxed);
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['all_Q2_policy_comparison']['scope']==OLD_SCOPE,'Exact actual compared Q2 parent required')
 require(record(ROOT/'native/app/mapped_copy.h')['sha256']=='aa7f5299cc0041ad4ab8057721527dd64f795118cea69ee21dfb8ea3144bf333','Actual qualified copy header changed')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__),record(ROOT/'native/app/mapped_copy.h')]
 for row in frozen:require(record(row['path'])==row,'Qualified input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();snapshot=a.out/'generator.private.py';snapshot.write_bytes(Path(__file__).read_bytes())
 header=a.out/'mapped_copy.h';header.write_text(threshold_header((ROOT/'native/app/mapped_copy.h').read_text()),newline='\n')
 variants=[('entry',prior['compile_commands'][0],prior['expert_q2_model']['actual_entry'],entry_source),
  ('owner',prior['all_Q2_IO_measurement']['commands'][1],prior['all_Q2_IO_measurement']['owner'],owner_source)]
 commands=[];replacements={};added=[record(snapshot),record(header)]
 for label,original_command,original_record,derive in variants:
  original=Path(original_record['path']);require(record(original)==original_record,'Actual compiled source changed')
  source=a.out/(label+'.private.cpp');source.write_text(derive(original.read_text()),newline='\n');obj=a.out/(label+'.o');command=original_command.copy();old_obj=command[command.index('-o')+1]
  command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(original.parent)]
  if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(label+'.private.d'))
  require(prior['link_command'].count(old_obj)==1,'One actual selected object required');replacements[old_obj]=str(obj);commands.append(command);added.extend((record(original),record(source)))
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,command in enumerate(commands+[link]):
  r=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-6000:]);print(json.dumps(dict(copy_comparison_build_step=i+1,total=3)),flush=True)
 for row in frozen:require(record(row['path'])==row,'Frozen source changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[commands[0]],source_parent=record(a.parent),inputs_before=frozen+added+[record(a.out/'entry.o'),record(a.out/'owner.o')],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model']['actual_entry']=record(a.out/'entry.private.cpp');receipt['expert_q2_model']['commands']=[commands[0],prior['expert_q2_model']['commands'][1]]
 receipt['all_Q2_IO_measurement'].update(entry=record(a.out/'entry.private.cpp'),owner=record(a.out/'owner.private.cpp'),commands=commands)
 receipt['all_Q2_small_copy_comparison']=dict(scope=SCOPE,commands=commands,actual_header=record(header),original_header=record(ROOT/'native/app/mapped_copy.h'),GPU_objects_cache_and_read_schedule_unchanged=True,extra_static_bytes=8,no_extra_heap_arrays=True,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(small_copy_comparison_built=True,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()

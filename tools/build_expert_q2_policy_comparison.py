#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one finite all-Q2 control/probation ABBA; never execute the console."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
from expert_all_q2_model_source import SCOPE as PARENT_MODEL_SCOPE
from build_expert_q2_io_measurement import SCOPE as PARENT_IO_SCOPE
ROOT=Path(__file__).resolve().parents[1]
MODEL_SCOPE=dict(PARENT_MODEL_SCOPE,schema='ps5-qwen-all-Q2-policy-model-comparison-v1',maximum_requests=5,timed_requests=4)
IO_SCOPE=dict(PARENT_IO_SCOPE,schema='ps5-qwen-all-Q2-policy-IO-v1',maximum_requests=5,original_IO_and_GPU_work_unchanged=False,original_GPU_math_unchanged=True)
POLICY_SCOPE=dict(schema='ps5-qwen-all-Q2-probation-ABBA-v1',enabled=True,maximum_requests=5,
    warmup_requests=1,order=['control','control','two_touch_probation','two_touch_probation','control'],
    active_cache_slots=867,cache_budget_bytes=1333739520,extra_Expert_reads=False,
    current_top10_pinned=True,original_GPU_math_unchanged=True,automatic_retries=0)

def literal(value):return json.dumps(json.dumps(value,separators=(',',':')))

def entry_source(text):
 text='extern "C" void qwen_app_select_Q2_probation(bool);\n'+text
 text=once(text,literal(PARENT_MODEL_SCOPE),literal(MODEL_SCOPE))
 text=once(text,literal(PARENT_IO_SCOPE),literal(IO_SCOPE))
 text=once(text,'        const unsigned request_count=3;',
  '        if(policy.at("native_Expert_Q2_policy_comparison")!=Json::parse('+literal(POLICY_SCOPE)+'))\n'
  '            throw std::runtime_error("Exact finite Q2 policy comparison required");\n        const unsigned request_count=5;')
 text=once(text,'            const bool refill=false;','            const bool probation=ordinal==2||ordinal==3;\n            const bool refill=false;')
 text=once(text,'            const char *arm=ordinal==0?"warmup":(refill?"six-demand":"ordinary");',
  '            const char *arm=ordinal==0?"warmup":(probation?"two-touch-probation":"aged-lfu-control");')
 text=once(text,'                resident_reset_empty_context(context,model,startup.admission_report);',
  '                qwen_app_select_Q2_probation(probation);\n                resident_reset_empty_context(context,model,startup.admission_report);')
 text=once(text,'{"active_cache_slots",867},{"cache_initially_empty",!second},',
  '{"expert_eviction_policy",probation?"two_touch_probation":"aged_lfu"},{"active_cache_slots",867},{"cache_initially_empty",!second},')
 text=once(text,'{"completed_IO_measurement",true},{"per_token_source_snapshots",true},',
  '{"completed_policy_comparison",true},{"completed_IO_measurement",true},{"per_token_source_snapshots",true},')
 return text

def cache_source(text):
 text=once(text,'#include "llama-app-expert-policy.h"','#include "candidate_expert_policy.h"')
 marker='static std::uint64_t resident_reuse_ordinal=0;'
 text=once(text,marker,marker+'''
static bool Q2_probation_selected=false;
extern "C" void qwen_app_select_Q2_probation(bool enabled){
    if(!resident_reuse_enabled||!resident_reuse_owner||resident_reuse_thread!=std::this_thread::get_id())
        throw std::runtime_error("Q2 eviction selection requires the original retained-cache producer");
    Q2_probation_selected=enabled;
}
''')
 marker='        forecast.reset();if(predictive)forecast=std::make_unique<qwen_app::CrossLayerForecast>();'
 text=once(text,marker,'''        for(auto &g:groups)g.slru.policy.set_eviction_policy(Q2_probation_selected?
            qwen_app::ExpertEvictionPolicy::two_touch_probation:qwen_app::ExpertEvictionPolicy::aged_lfu);
'''+marker)
 return text

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','screen','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());screen=json.loads(a.screen.read_text())
 require(prior['all_Q2_IO_measurement']['scope']==PARENT_IO_SCOPE and prior['expert_q2_model']['scope']==PARENT_MODEL_SCOPE,'Exact never-executed IO parent required')
 selected=next(r for r in screen['policies']if r['mode']=='two_touch_probation')
 require(screen['native_counters_exact']and selected['eligible_for_native_speed_comparison'],'Closed actual-route held-out screen required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']
 frozen +=[record(a.parent),record(a.screen),record(__file__),record(ROOT/'native/app/expert_policy.h')]
 for row in frozen:require(record(row['path'])==row,'Qualified input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 header=a.out/'candidate_expert_policy.h';header.write_bytes((ROOT/'native/app/expert_policy.h').read_bytes())
 old_entry=Path(prior['expert_q2_model']['actual_entry']['path']);old_cache=Path(prior['expert_q2_model']['actual_cache']['path'])
 commands=[];replacements={};sources=[record(header)]
 for label,original,derive in [('entry',old_entry,entry_source),('cache',old_cache,cache_source)]:
  template=prior['compile_commands'][0]if label=='entry'else prior['expert_q2_model']['commands'][1]
  command=template.copy();source=a.out/(label+'.private.cpp');source.write_text(derive(original.read_text()),newline='\n')
  obj=a.out/(label+'.o');old_obj=command[command.index('-o')+1]
  command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(original.parent)]
  if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(label+'.private.d'))
  commands.append(command);replacements[old_obj]=str(obj);sources +=[record(original),record(source)]
 for old in replacements:require(prior['link_command'].count(old)==1,'One actual entry/cache link replacement required')
 link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
 link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,command in enumerate(commands+[link]):
  r=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-6000:])
  print(json.dumps(dict(policy_comparison_build_step=i+1,total=3)),flush=True)
 for row in frozen:require(record(row['path'])==row,'Frozen input changed during build')
 result=copy.deepcopy(prior);result.update(artifact=record(image),link_command=link,source_parent=record(a.parent),compile_commands=[commands[0]],
  inputs_before=frozen+sources+[record(a.out/'entry.o'),record(a.out/'cache.o')],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 result['expert_q2_model'].update(scope=MODEL_SCOPE,actual_entry=record(a.out/'entry.private.cpp'),actual_cache=record(a.out/'cache.private.cpp'),commands=commands)
 result['all_Q2_IO_measurement'].update(scope=IO_SCOPE,entry=record(a.out/'entry.private.cpp'))
 result['all_Q2_policy_comparison']=dict(scope=POLICY_SCOPE,commands=commands,header=record(header),screen=record(a.screen),
  extra_heap_arrays=0,GPU_provider_objects_unchanged=True,source_owner_object_unchanged=True,memory_identity_and_completion_guards_unchanged=True,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,result)
 result['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
 result['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Native import/dispatch audit failed')
 write_json(target,result);print(json.dumps(dict(policy_comparison_built=True,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()

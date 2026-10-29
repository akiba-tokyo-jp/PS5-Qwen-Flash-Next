#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the all-Q2 passive app with only the positively compared cache policy."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-all-Q2-probation-monitor-v1',enabled=True,policy='two_touch_probation',
 active_cache_slots=867,cache_budget_bytes=1333739520,maximum_requests=3,HTTP_requests=2,VideoOut_starts=1,
 original_GPU_math_unchanged=True,automatic_retries=0)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','policy-build','comparison','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());qualified=json.loads(a.policy_build.read_text());result=json.loads(a.comparison.read_text())
 require(prior['expert_q2_model']['passive_monitor']and prior['expert_q2_model']['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE','Qualified all-Q2 passive parent required')
 require(result['completed']and result['every_candidate_faster_than_every_control']and result['full_F32_rows_and_routes_identical']and result['native_normal_close_and_exact_control_restoration'],'Positive native same-model speed and complete-state evidence required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']
 frozen +=[record(a.parent),record(a.policy_build),record(a.comparison),record(__file__)]
 selected=qualified['expert_q2_model']['commands'][1];cache_object=Path(selected[selected.index('-o')+1]);frozen +=[record(cache_object),qualified['expert_q2_model']['actual_cache'],qualified['all_Q2_policy_comparison']['header']]
 for r in frozen:require(record(r['path'])==r,'Qualified monitor/cache input changed')
 old=prior['compile_commands'][0];original=Path(old[old.index('-c')+1]);text=original.read_text()
 text='extern "C" void qwen_app_select_Q2_probation(bool);\n'+text
 marker='        const unsigned request_count=3;'
 text=once(text,marker,'        if(policy.at("native_Expert_Q2_probation")!=Json::parse('+json.dumps(json.dumps(SCOPE,separators=(',',':')))+'))\n'
  '            throw std::runtime_error("Exact qualified probation monitor scope required");\n'+marker)
 text=once(text,'                resident_reset_empty_context(context,model,startup.admission_report);',
  '                qwen_app_select_Q2_probation(true);\n                resident_reset_empty_context(context,model,startup.admission_report);')
 text=once(text,'{"active_cache_slots",867},{"cache_initially_empty",!second},',
  '{"expert_eviction_policy","two_touch_probation"},{"active_cache_slots",867},{"cache_initially_empty",!second},')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();source=a.out/'entry.private.cpp';source.write_text(text,newline='\n');obj=a.out/'entry.o';command=old.copy();old_entry=command[command.index('-o')+1]
 command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(original.parent)]
 if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'entry.private.d')
 old_cache=prior['expert_q2_model']['commands'][1];old_cache_object=old_cache[old_cache.index('-o')+1]
 replace={old_entry:str(obj),old_cache_object:str(cache_object)}
 for old_path in replace:require(prior['link_command'].count(old_path)==1,'One exact monitor entry/cache replacement required')
 image=a.out/'qwen-native.pie.elf';link=[replace.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate((command,link)):
  r=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-5000:]);print(json.dumps(dict(probation_monitor_build_step=i+1,total=2)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen input changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[command],link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(source),record(obj)],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(actual_entry=record(source),actual_cache=qualified['expert_q2_model']['actual_cache'],commands=[command,selected],expert_eviction_policy='two_touch_probation',normal_application_validation_pending=True)
 receipt['all_Q2_probation_monitor']=dict(scope=SCOPE,headless_comparison=record(a.comparison),cache_build=record(a.policy_build),GPU_objects_source_owner_and_raster_unchanged=True,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(probation_passive_monitor_built=True,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()

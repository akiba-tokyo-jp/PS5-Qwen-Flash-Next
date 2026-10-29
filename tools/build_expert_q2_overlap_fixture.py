#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an unloaded Q2 I/O/GPU scheduling screen using a sealed existing pack."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from active_native_inputs import active_link_inputs
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-Q2-overlap-fixture-v1',enabled=True,model_loads=0,maximum_requests=0,HTTP_requests=0,VideoOut_starts=0,
 actual_Expert_triplets=10,mixed_layer_fixed_asset_cohort=True,modes=['one_graph_serial','split_serial','split_overlap'],
 warmups=3,timed_arms=6,maximum_GPU_graphs=40,CPU_windows=2,CPU_window_bytes=8<<20,maximum_device_bytes=48<<20,
 F32_input_and_original_contribution_order=True,CPU_worker_GPU_calls=0,originals_preserved=True,automatic_retries=0)
def entry_source(text):
 text='#include <nlohmann/json.hpp>\nnamespace qwen_app {nlohmann::json run_expert_Q2_overlap_fixture(void(*)(),void(*)(const char*));}\n'+text
 marker='        qwen_native_stage("resident_measured_GPU_phase_admitted_starting_GPU");';at=text.index(marker);end=text.index('        llama_backend_init();',at)+len('        llama_backend_init();')
 insertion='''
        if(policy.at("native_Expert_Q2_overlap_fixture")!=Json::parse(SCOPE))throw std::runtime_error("Exact separate unloaded Q2 overlap scope required");
        qwen_app::enforce_native_model_compute_limits();
        auto overlap=qwen_app::run_expert_Q2_overlap_fixture(qwen_native_driver_checkpoint,qwen_native_stage);
        require_model_CPU_budget();const auto overlap_ledger=qwen_app::native_model_device_stats();
        if(overlap_ledger.live)throw std::runtime_error("Q2 overlap fixture retained live device owners");
        qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        overlap.update({{"pid",getpid()},{"run_id",policy.at("native_first_generation_validation").at("run_id")},
            {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"source_workers_stopped",true},{"device_ledger_live_bytes",overlap_ledger.live},{"device_ledger_peak_bytes",overlap_ledger.peak}});
        write_fresh_report(startup.admission_report,overlap);
        qwen_native_stage("Q2_overlap_fixture_completed_without_model_waiting_for_ordinary_close");
        for(;;)usleep(1000000);
'''.replace('SCOPE',json.dumps(json.dumps(SCOPE,separators=(',',':'))))
 return text[:end]+insertion+text[end:]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['all_Q2_bundle_comparison']['scope']['bundled_Experts']==336,'Qualified exact bundle parent required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__),record(ROOT/'native/app/expert_q2_ready_graph.h'),record(ROOT/'native/app/expert_q2_overlap_fixture.cpp')]
 for r in frozen:require(record(r['path'])==r,'Qualified native input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();original=Path(prior['expert_q2_model']['actual_entry']['path']);owner=Path(prior['all_Q2_IO_measurement']['owner']['path'])
 source=a.out/'entry.private.cpp';source.write_text(entry_source(original.read_text()),newline='\n')
 owner_source=a.out/'owner.private.cpp';owner_source.write_text(owner.read_text()+'''\nextern "C" int qwen_app_Q2_bundle_fixture_descriptor(){required().require_completed_window();ops.require_metadata_idle();if(!Q2_bundle_verified||Q2_bundle_fd<0)throw std::runtime_error("Complete sealed bundle proof required");return Q2_bundle_fd;}\n''',newline='\n')
 jobs=[];replacements={};objects=[]
 for label,src,base,origin in [('entry',source,prior['compile_commands'][0],original),('owner',owner_source,prior['all_Q2_IO_measurement']['commands'][1],owner),('fixture',ROOT/'native/app/expert_q2_overlap_fixture.cpp',prior['compile_commands'][0],original)]:
  cmd=base.copy();old=cmd[cmd.index('-o')+1];obj=a.out/(label+'.o');cmd[cmd.index('-c')+1]=str(src);cmd[cmd.index('-o')+1]=str(obj);cmd[1:1]=['-I',str(origin.parent),'-I',str(owner.parent)]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(label+'.private.d'))
  if label!='fixture':require(prior['link_command'].count(old)==1,'One actual selected override required');replacements[old]=str(obj)
  jobs.append(cmd);objects.append(obj)
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link.insert(link.index(str(objects[0])),str(objects[2]));link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate(jobs+[link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-6000:]);print(json.dumps(dict(overlap_fixture_build_step=i+1,total=4)),flush=True)
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[jobs[0]],link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(p)for p in [source,owner_source,*objects]],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(actual_entry=record(source),commands=[jobs[0],prior['expert_q2_model']['commands'][1]])
 receipt['all_Q2_IO_measurement'].update(entry=record(source),owner=record(owner_source),commands=jobs)
 receipt['all_Q2_overlap_fixture']=dict(scope=SCOPE,only_entry_and_borrowed_descriptor_accessor_changed=True,actual_fixture=record(ROOT/'native/app/expert_q2_overlap_fixture.cpp'),original_weight_math_and_provider_unchanged=True,commands=jobs)
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Native import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(overlap_fixture_built=True,model_loads=0,PS5_operations=0)))
if __name__=='__main__':main()

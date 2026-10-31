#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build real device checkpoint writer/reuse/copy comparisons without a model."""
import argparse,copy,json,shlex,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from checkpoint_trial_source import transform
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-checkpoint-device-fixture-v1',model_loads=0,title_launches=1,HTTP_requests=0,VideoOut_starts=0,
 blocks=12,modes=[0,1,1,0,0,3,3,0,1,2,2,1],save_restore_events=60,maximum_seconds=600,
 payload_bytes=[119881728,121049088],write_spans=49,maximum_CPU_window_bytes=262144,
 complete_byte_and_canary_equality=True,changed_chunking_required=True,source_identity_required=True,
 unused_fixture_metadata_bytes=0,
 original_physical_reserves=True,original_OS_minimum=True,positive_completion_per_state_operation=True,
 original_shaders=True,automatic_retries=0,CI_runs=0,production_adoption=False)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--reuse-GPU',type=Path,help='Reuse a separately validated, byte-identical compiled GPU provider and shader controls')
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 recipe_path=a.cache/'build/llama-ps5/compile_commands.json';recipe=next(x for x in json.loads(recipe_path.read_text())if x['file'].endswith('/llama-context.cpp'))
 context=Path(recipe['file']);old_context=Path(recipe['output']);ctxcmd=shlex.split(recipe['command'],posix=False);ctxcmd=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in ctxcmd]
 ctxcmd[ctxcmd.index('-o')+1]=str(old_context);ctxcmd[1:1]=['-I',str(ROOT/'native/app')]
 seed=copy.deepcopy(n);archive=next(x for x in seed['link_command']if x.endswith('libllama.a'));seed['link_command'].insert(seed['link_command'].index(archive),str(old_context));seed['inputs_before'].append(record(old_context))
 seedpath=a.out/'context-seed.private.json';write_json(seedpath,seed)
 model=json.loads(Path(n['bounded_model_source_manifest']['path']).read_text());gpu=next(x for x in model['objects']if x['source'].endswith('/ggml-vulkan.cpp'))
 gc=gpu['command'];gc=shlex.split(gc,posix=False)if isinstance(gc,str)else gc.copy();gc=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in gc]
 gc[gc.index('-o')+1]=gpu['object']['path'];actual=Path(gpu['actual_source']['path'])
 require(seed['link_command'].count(gpu['object']['path'])==1,'Exactly one actual GPU provider required')
 entrycmd=n['compile_commands'][0];entry=Path(entrycmd[entrycmd.index('-c')+1]).read_text();entry='#include "checkpoint_device_fixture.h"\n'+entry
 branch='''        if(policy.at("native_checkpoint_device_fixture")!=Json::parse(SCOPE_LITERAL))throw std::runtime_error("Exact device checkpoint fixture scope required");
        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty checkpoint fixture device ledger required");
        qwen_native_stage("checkpoint_device_fixture_started_model_not_loaded");
        auto checked=qwen_app::checkpoint_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto live=qwen_app::native_model_device_stats();if(live.live)throw std::runtime_error("Checkpoint fixture device ledger remains live");
        const auto&owner=policy.at("native_first_generation_validation");
        checked.update({{"schema","ps5-qwen-checkpoint-device-fixture-result-v1"},{"completed",true},{"pid",getpid()},
            {"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",live.live},{"device_ledger_peak_bytes",live.peak},
            {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")}});
        write_fresh_report(startup.admission_report,checked);qwen_native_stage("checkpoint_device_fixture_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
'''.replace('SCOPE_LITERAL',json.dumps(json.dumps(SCOPE,separators=(',',':'))))
 entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
 headers=[ROOT/'native/app'/x for x in('checkpoint_device_trial.h','checkpoint_vk_batch.inc','checkpoint_device_fixture.h')]
 variants=dict(context=(ctxcmd,transform(context.read_text(),True)),entry=(entrycmd,entry));extra=[];reused=None
 if a.reuse_GPU:
  from external_shader_storage import validate_shader_resources
  reused=json.loads(a.reuse_GPU.read_text());require(reused['routing_sharing']['actual_sources']['cache']==n['routing_sharing']['actual_sources']['cache'],'GPU controls must bind the exact unchanged cache')
  validated=validate_shader_resources(reused['shader_resource_manifest']['path'],reused['bounded_model_source_manifest']['path'],reused['engine_receipt']['path'])
  row=reused['checkpoint_device_fixture'];savedcmd=row['commands']['gpu'];savedsource=row['actual_sources']['gpu'];savedobject=record(savedcmd[savedcmd.index('-o')+1])
  require(record(savedsource['path'])==savedsource and savedobject==validated['vulkan_object'],'Exact reused GPU source/object required')
  require(Path(savedsource['path']).read_text()==actual.read_text()+'\n#include "checkpoint_vk_batch.inc"\n','Only byte-identical GPU code may be reused')
  require(next(x for x in row['headers']if x['path'].endswith('checkpoint_vk_batch.inc'))==record(ROOT/'native/app/checkpoint_vk_batch.inc'),'Exact compiled copy-batch include required')
  seed['link_command'][seed['link_command'].index(gpu['object']['path'])]=savedobject['path'];seed['inputs_before'] +=[savedsource,savedobject,record(a.reuse_GPU)]
  for k in('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):seed[k]=reused[k]
  write_json(seedpath,seed);extra.append(a.reuse_GPU)
 else:variants['gpu']=(gc,actual.read_text()+'\n#include "checkpoint_vk_batch.inc"\n')
 r,jobs,sources=link(seedpath,a.out,variants,[Path(__file__),ROOT/'tools/checkpoint_trial_source.py',recipe_path,*headers,*extra])
 if reused:jobs['gpu']=savedcmd;sources['gpu']=savedsource
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  if key in r:r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
 r['checkpoint_device_fixture']=dict(scope=SCOPE,actual_sources=sources,commands=jobs,headers=[record(h)for h in headers],context_original=record(context),fixture_only=True)
 unsealed=a.out/'unsealed-link.private.json';write_json(unsealed,r)
 if not reused:
  completed=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600)
  (a.out/'GPU-provenance.private.log').write_bytes(completed.stdout+completed.stderr);require(completed.returncode==0,completed.stderr.decode(errors='replace')[-3500:])
  r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text())
 else:r['checkpoint_device_fixture']['reused_exact_GPU_controls']=record(a.reuse_GPU)
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='actual_device_checkpoint_fixture',model_loads=0,driver_unchanged=True,original_physical_and_OS_minimum_preserved=True,positive_completion_retained=True,CPU_heap_limit_bytes=512<<20,cache_slots=3072,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

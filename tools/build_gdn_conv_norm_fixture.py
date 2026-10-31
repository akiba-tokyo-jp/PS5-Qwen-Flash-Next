#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one additional pinned shader and a full-state F64 Vulkan comparison."""
import argparse,copy,json,shlex,subprocess,sys,struct,hashlib
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import recipes
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from gdn_conv_norm_source import transform as gpu_transform
from gdn_conv_norm_fixture_source import transform as fixture_transform
from additional_shader_source import transform as assets_transform
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-GDN-conv-normalization-fixture-v1',model_loads=0,HTTP_requests=0,VideoOut_starts=0,
 cases=4,GPU_graphs=144,maximum_graphs=320,deadline_seconds=180,S_v=128,H_K=16,H_V=48,channels=10240,
 weight_precision='original_F32_runtime_convolution',activation_and_state_precision='F32',original_PLE_BF16_preserved=True,
 fusion='convolution4_SiLU_RMS_norm_epsilon_over128_then_F32_scale',prefill_two_token_original_fallback=True,
 zero_and_epsilon_dominated_heads=True,full_recurrent_state_and_unwritten_snapshots=True,source_history_and_weights_exact=True,
 F64_maximum_absolute_error=1e-6,additional_readonly_shader_count=1,complete_additional_shader_SHA256_before_Vulkan=True,
 original_shader_registry_pool_and_lease_unchanged=True,original_physical_and_OS_minimum=True,all_positive_completion_checks=True,
 automatic_retries=0,CI_runs=0,production_adoption=False)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--reuse-compiled-GPU',type=Path,help='Reuse the exact successful GPU compile from an otherwise incomplete fresh build')
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 shader=ROOT/'native/app/gdn_conv_norm.comp';compiler=a.workspace/'toolchain/shaderc-clang64/clang64/bin/glslc.exe';spv=a.out/'gdn-conv-normalization.spv'
 command=[str(compiler),'--target-env=vulkan1.1','-O','-fshader-stage=compute',str(shader),'-o',str(spv)]
 run=subprocess.run(command,capture_output=True,timeout=90);(a.out/'shader-compile.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-2500:])
 data=spv.read_bytes();require(20<=len(data)<=1<<20 and len(data)%4==0 and data[:4]==b'\x03\x02\x23\x07','Bounded word-aligned SPIR-V required')
 validator=compiler.with_name('spirv-val.exe');validation=None
 if validator.is_file():
  validation=[str(validator),'--target-env','vulkan1.1',str(spv)];run=subprocess.run(validation,capture_output=True,timeout=30);(a.out/'shader-validation.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace'))
 words=struct.unpack('<'+'I'*(len(data)//4),data);digest=hashlib.sha256(data).digest()
 generated=a.out/'qwen_conv_norm_spirv.private.h';generated.write_text('#pragma once\nalignas(4) static const uint32_t qwen_conv_norm_spirv[]={'+','.join(hex(x)for x in words)+'};\nstatic const unsigned char qwen_conv_norm_sha[]={'+','.join(str(x)for x in digest)+'};\n__attribute__((constructor)) static void qwen_register_conv_norm_asset(){qwen_app_register_additional_shader(qwen_conv_norm_spirv,sizeof(qwen_conv_norm_spirv),qwen_conv_norm_sha);}\n',newline='\n')
 fixture=a.out/'gdn_conv_norm_fixture.private.h';fixture.write_text(fixture_transform((ROOT/'native/app/gdn_columns_fixture.h').read_text()),newline='\n')
 selected={}
 for c in recipes(n):
  if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']:selected[c[c.index('-o')+1]]=c
 choices=[c for c in selected.values()if 'extern "C" const void *qwen_app_prepare_shader_code('in Path(c[c.index('-c')+1]).read_text()]
 require(len(choices)==1,'One actual shader-asset implementation provider required');assetcmd=choices[0].copy();asset_source=Path(assetcmd[assetcmd.index('-c')+1]);assetcmd[1:1]=['-I',str(ROOT/'native/app')]
 model=json.loads(Path(n['bounded_model_source_manifest']['path']).read_text());gpu=next(x for x in model['objects']if x['source'].endswith('/ggml-vulkan.cpp'))
 gc=gpu['command'];gc=shlex.split(gc,posix=False)if isinstance(gc,str)else gc.copy();gc=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in gc];gc[gc.index('-o')+1]=gpu['object']['path']
 actual=Path(gpu['actual_source']['path']);entrycmd=n['compile_commands'][0];entry=Path(entrycmd[entrycmd.index('-c')+1]).read_text()
 entry='#include "additional_shader_assets.h"\n#include "gdn_conv_norm_fixture.private.h"\nextern "C" void qwen_app_conv_norm_trial_release();\n'+entry
 branch='''        if(policy.at("native_GDN_conv_normalization_fixture")!=Json::parse(SCOPE_LITERAL))throw std::runtime_error("Exact convolution normalization fixture scope required");
        if(qwen_app_additional_shaders_verified()!=1)throw std::runtime_error("One separately SHA256-admitted immutable shader required before Vulkan");
        qwen_app::enforce_native_model_compute_limits();if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty convolution normalization fixture ledger required");
        qwen_native_stage("GDN_conv_normalization_fixture_started_model_not_loaded");
        auto checked=qwen_app::gdn_conv_norm_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_app_conv_norm_trial_release();qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto live=qwen_app::native_model_device_stats();if(live.live)throw std::runtime_error("Convolution normalization device ledger remains live");
        const auto&owner=policy.at("native_first_generation_validation");
        checked.update({{"schema","ps5-qwen-GDN-conv-normalization-fixture-result-v1"},{"completed",true},{"pid",getpid()},
            {"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"additional_shader_verified",qwen_app_additional_shaders_verified()},{"additional_shader_modules",qwen_app_additional_shader_modules()},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",live.live},{"device_ledger_peak_bytes",live.peak},
            {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")}});
        write_fresh_report(startup.admission_report,checked);qwen_native_stage("GDN_conv_normalization_fixture_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
'''.replace('SCOPE_LITERAL',json.dumps(json.dumps(SCOPE,separators=(',',':'))))
 entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
 headers=[ROOT/'native/app'/k for k in('additional_shader_assets.h','gdn_conv_norm.comp','gdn_conv_norm_state.inc','gdn_conv_norm_backend.inc','gdn_columns_fixture.h')]
 helpers=[ROOT/'tools'/k for k in('gdn_conv_norm_source.py','gdn_conv_norm_fixture_source.py','additional_shader_source.py')]
 variants=dict(assets=(assetcmd,assets_transform(asset_source.read_text())),entry=(entrycmd,entry));parent=a.parent;extra=[];reused=None
 if a.reuse_compiled_GPU:
  old=a.reuse_compiled_GPU;oldsource=old/'gpu.private.cpp';oldobject=old/'gpu.o';oldheader=old/generated.name;oldlog=old/'0.private.log'
  require(oldsource.read_text()==gpu_transform(actual.read_text())and oldheader.read_bytes()==generated.read_bytes(),'Exact GPU source and immutable shader bytes required for partial-build reuse')
  require(oldobject.is_file()and oldobject.stat().st_size>0 and oldlog.is_file()and b' error:'not in oldlog.read_bytes(),'Successfully produced fresh GPU object required')
  savedcmd=gc.copy();original_source=Path(savedcmd[savedcmd.index('-c')+1]);savedcmd[savedcmd.index('-c')+1]=str(oldsource);savedcmd[savedcmd.index('-o')+1]=str(oldobject);savedcmd[1:1]=['-I',str(original_source.parent),'-I',str(old)]
  if '-MF'in savedcmd:savedcmd[savedcmd.index('-MF')+1]=str(old/'gpu.private.d')
  savedsource=record(oldsource);savedobject=record(oldobject);seed=copy.deepcopy(n);require(seed['link_command'].count(gpu['object']['path'])==1,'One actual original GPU provider required')
  seed['link_command'][seed['link_command'].index(gpu['object']['path'])]=str(oldobject);seed['inputs_before'] +=[savedsource,savedobject,record(oldheader),record(oldlog)]
  parent=a.out/'compiled-GPU-seed.private.json';write_json(parent,seed);extra=[oldsource,oldobject,oldheader,oldlog];reused=dict(source=savedsource,object=savedobject,compiled_original_shader_header=record(oldheader),command=savedcmd,successful_partial_build_log=record(oldlog))
 else:variants['gpu']=(gc,gpu_transform(actual.read_text()))
 r,jobs,sources=link(parent,a.out,variants,[Path(__file__),*helpers,*headers,generated,fixture,shader,spv,compiler,*extra])
 if reused:jobs['gpu']=savedcmd;sources['gpu']=savedsource
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  if key in r:r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 for row in r['CPU_metadata_scope']['changed_sources']:
  if row['object_path']==assetcmd[assetcmd.index('-o')+1]:row.update(source=sources['assets'],object_path=jobs['assets'][jobs['assets'].index('-o')+1],command=jobs['assets'])
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
 r['GDN_conv_normalization_fixture']=dict(scope=SCOPE,actual_sources=sources,commands=jobs,headers=[record(x)for x in headers]+[record(generated),record(fixture)],shader=record(spv),shader_compiler=record(compiler),shader_command=command,shader_validation_command=validation,original_shader_registry_unchanged=True,reused_exact_GPU_compile=reused)
 unsealed=a.out/'unsealed-link.private.json';write_json(unsealed,r)
 done=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600);(a.out/'GPU-provenance.private.log').write_bytes(done.stdout+done.stderr);require(done.returncode==0,done.stderr.decode(errors='replace')[-3500:])
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='GDN_convolution_normalization_F64_full_state_fixture',model_loads=0,cache_slots=3424,original_driver_and_physical_OS_minimum=True,all_positive_completion_checks=True,CPU_heap_limit_bytes=512<<20,additional_shader_full_SHA_before_Vulkan=True,original_shader_registry_unchanged=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

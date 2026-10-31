#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded original-Q2 Gate/Up fusion comparison with actual weights."""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
from gdn_conv_norm_source import CREATE
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-gate-up-fixture-v1',model_loads=0,requests=0,GPU_graphs=108,cases=3,tokens=[1,2,3],
 original_actual_Gate_Up_Q2_K=True,F32_inputs_and_accumulation=True,F64_all_outputs=True,
 original_three_token_fallback=True,additional_immutable_shaders=2,physical_reserves_and_positive_completion=True,
 deadline_seconds=240,automatic_retries=0,CI_runs=0,production_adoption=False)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','pack','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());pack=json.loads(a.pack.read_text());require(pack['completed']and len(pack['bundles'])==348 and pack['CPU_Direct_positively_retired'],'Sealed actual Q2 pack required');a.out.mkdir(parents=True,exist_ok=False)
 shader=ROOT/'native/app/expert_gate_up_q2.comp';compiler=a.workspace/'toolchain/shaderc-clang64/clang64/bin/glslc.exe';spv=a.out/'expert-gate-up.spv';sc=[str(compiler),'--target-env=vulkan1.1','-O','-fshader-stage=compute',str(shader),'-o',str(spv)]
 v=subprocess.run(sc,capture_output=True,timeout=90);(a.out/'shader.private.log').write_bytes(v.stdout+v.stderr);require(v.returncode==0,v.stderr.decode(errors='replace'));data=spv.read_bytes();require(len(data)%4==0 and data[:4]==b'\x03\x02\x23\x07','Valid word-aligned shader required')
 validator=compiler.with_name('spirv-val.exe')
 if validator.is_file():
  v=subprocess.run([str(validator),'--target-env','vulkan1.1',str(spv)],capture_output=True,timeout=30);require(v.returncode==0,v.stderr.decode(errors='replace'))
 header=a.out/'qwen_gate_up_spirv.private.h';header.write_text('#pragma once\nalignas(4) static const uint32_t qwen_gate_up_spirv[]={'+','.join(hex(x)for x in struct.unpack('<'+'I'*(len(data)//4),data))+'};\nstatic const unsigned char qwen_gate_up_sha[]={'+','.join(str(x)for x in hashlib.sha256(data).digest())+'};\n__attribute__((constructor)) static void qwen_register_gate_up_asset(){qwen_app_register_additional_shader(qwen_gate_up_spirv,sizeof(qwen_gate_up_spirv),qwen_gate_up_sha);}\n',newline='\n')
 state=(ROOT/'native/app/gdn_conv_norm_state.inc').read_text().replace('QwenConvNorm','QwenGateUp').replace('qwen_conv_norm','qwen_gate_up').replace('qwen_app_conv_norm','qwen_app_gate_up')
 state=once(state,'uint32_t xo,wo,yo,qo,ko,xstride,wstride;float epsilon,scale;',
  'uint32_t go,uo,xo,io,yo,gplane,uplane,grow,urow,xstep,istep,ystep,slots,selected,tokens;');state=once(state,'sizeof(QwenGateUpPC)==36','sizeof(QwenGateUpPC)==60')
 sh=a.out/'expert_gate_up_state.private.inc';sh.write_text(state,newline='\n')
 output=pack['output'];assets=a.out/'expert_gate_up_fixture_assets.private.h';assets.write_text('#pragma once\ninline constexpr const char*gate_up_pack_path='+json.dumps('/app0/'+output['path'].split('/PPSA99190/',1)[1])+';\ninline constexpr const char*gate_up_pack_sha256='+json.dumps(output['sha256'])+';\ninline constexpr unsigned long long gate_up_pack_bytes='+str(output['bytes'])+'ULL;\n',newline='\n')
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(n['io_gpu_comparison']['GPU_source']['path']).read_text();gpu=once(gpu,'#include "ggml-vulkan-common.h"','#include "ggml-vulkan-common.h"\n#include "expert_gate_up_state.private.inc"')
 create=CREATE.replace('QwenConvNorm','QwenGateUp').replace('qwen_conv_norm','qwen_gate_up').replace('qwen_conv_norm_f32','qwen_gate_up_q2')
 anchor='    ggml_vk_create_pipeline(device, device->pipeline_ssm_conv_bias_silu_f32,';start=gpu.index(anchor);end=gpu.index('\n',start)+1;gpu=gpu[:end]+create+gpu[end:]
 anchor='void ggml_vk_mul_mat_id(ggml_backend_vk_context * ctx, vk_context& subctx, const struct ggml_cgraph * cgraph, int node_idx) {'
 gpu=once(gpu,anchor,'#include "expert_gate_up_backend.inc"\n'+anchor+'\n    if(ctx->num_additional_fused_ops==2&&qwen_gate_up_match(cgraph,node_idx)){qwen_gate_up_dispatch(ctx,subctx,cgraph,node_idx);return;}')
 gpu=once(gpu,'            if(qwen_norm.extra){',
  '            if(qwen_gate_up_match(cgraph,i)){ctx->num_additional_fused_ops=2;ctx->fused_ops_write_mask=1u<<2;fusion_string="Q2_GATE_UP_SWIGLU";op_srcs_fused_elementwise[0]=false;op_srcs_fused_elementwise[1]=false;op_srcs_fused_elementwise[2]=true;}else if(qwen_norm.extra){')
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "expert_gate_up_fixture.h"\nextern "C" void qwen_app_gate_up_trial_release();\n'+entry
 entry=entry.replace('qwen_app_additional_shaders_verified()!=1','qwen_app_additional_shaders_verified()!=2')
 branch='''        {if(policy.at("native_GDN_conv_normalization_fixture")!=Json::parse(SCOPE_LITERAL))throw std::runtime_error("Exact Gate/Up fixture policy required");
        qwen_app::enforce_native_model_compute_limits();if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty Gate/Up fixture ledger required");
        auto result=qwen_app::gate_up_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_app_gate_up_trial_release();qwen_app_conv_norm_trial_release();qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto ledger=qwen_app::native_model_device_stats();if(ledger.live)throw std::runtime_error("Gate/Up fixture has live resources");
        const auto&owner=policy.at("native_first_generation_validation");
        result.update({{"schema","ps5-qwen-gate-up-fixture-result-v1"},{"completed",true},{"pid",getpid()},{"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},{"device_ledger_live_bytes",ledger.live},{"device_ledger_peak_bytes",ledger.peak},
            {"additional_shader_verified",qwen_app_additional_shaders_verified()},{"all_model_source_device_owners_positively_retired",true}});
        write_fresh_report(startup.admission_report,result);qwen_native_stage("Gate_Up_fixture_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }
'''.replace('SCOPE_LITERAL',json.dumps(json.dumps(SCOPE,separators=(',',':'))))
 entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
 ec=ec.copy();ec+=['-I',str(ROOT/'native/app')];gc=gc.copy();gc+=['-I',str(ROOT/'native/app')]
 inputs=[Path(__file__),a.pack,header,sh,assets,shader,spv,compiler,ROOT/'native/app/expert_gate_up_backend.inc',ROOT/'native/app/expert_gate_up_fixture.h']
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc,gpu)),inputs)
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
 r['GDN_conv_normalization_fixture']=dict(scope=SCOPE,actual_sources=sources,commands=jobs,shader=record(spv),shader_command=sc,headers=[record(x)for x in [header,sh,assets]],native_verification_pending=True)
 unsealed=a.out/'unsealed.private.json';write_json(unsealed,r);v=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600);(a.out/'provenance.private.log').write_bytes(v.stdout+v.stderr);require(v.returncode==0,v.stderr.decode(errors='replace')[-2500:]);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='actual_Q2_Gate_Up_F64_fixture',candidate=record(a.out/'receipt.private.json'),physical_guards_and_positive_completion_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

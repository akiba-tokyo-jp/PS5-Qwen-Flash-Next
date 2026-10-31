#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the natively qualified two-Expert kernel with the full Top2 model."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import recipes,literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from gdn_conv_norm_source import CREATE
from multiple_shader_source import transform as multiple_assets
from qualify_post_top2_reporting import transform as reporting
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','fixture','proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());f=json.loads(a.fixture.read_text());proof=json.loads(a.proof.read_text())
    require(proof['completed']and proof['GPU_graphs']==180 and proof['all_F64_outputs_passed']and
        proof['all_model_source_device_owners_positively_retired']and proof['device_ledger_live_bytes']==0,'Complete native Top2 F64/canary fixture required')
    require(n['driver']==f['driver']and n['GDN_model_comparison']['scope']['candidate']=='Q4-cache3712-Top2','Current matched Q4/Top2 and pinned driver required')
    a.out.mkdir(parents=True,exist_ok=False)
    headers=f['GDN_conv_normalization_fixture']['headers'];state=Path(next(x['path']for x in headers if Path(x['path']).name=='expert_gate_up_state.private.inc'))
    backend=Path(f['post_top2_gate_up']['complete_fixtures'][1]['path'])
    for item in headers+[f['post_top2_gate_up']['complete_fixtures'][1]]:require(record(item['path'])==item,'Qualified kernel asset changed')
    gc=n['io_gpu_comparison']['GPU_command'];gpu_path=Path(gc[gc.index('-c')+1]);gpu=gpu_path.read_text()
    require(n['lossless_shader_storage']['vulkan_object']['sha256']=='17cb982ec26903fcee469639592d5acd761acd6f883bc35135b9d665fc4b6ad2','Original qualified GPU provider required')
    gpu=once(gpu,'#include "ggml-vulkan-common.h"','#include "ggml-vulkan-common.h"\n#include '+json.dumps(state.resolve().as_posix()))
    create=CREATE.replace('QwenConvNorm','QwenGateUp').replace('qwen_conv_norm','qwen_gate_up').replace('qwen_gate_up_f32','qwen_gate_up_q2').replace('{128,1,1}','{64,1,1}')
    anchor='    ggml_vk_create_pipeline(device, device->pipeline_ssm_conv_bias_silu_f32,'
    at=gpu.index('\n',gpu.index(anchor))+1;gpu=gpu[:at]+create+gpu[at:]
    anchor='void ggml_vk_mul_mat_id(ggml_backend_vk_context * ctx, vk_context& subctx, const struct ggml_cgraph * cgraph, int node_idx) {'
    gpu=once(gpu,anchor,'#include '+json.dumps(backend.resolve().as_posix())+'\n'+anchor+
        '\n    if(ctx->num_additional_fused_ops==2&&qwen_gate_up_match(cgraph,node_idx)){qwen_gate_up_dispatch(ctx,subctx,cgraph,node_idx);return;}')
    gpu=once(gpu,'            if(qwen_norm.extra){',
        '            if(qwen_gate_up_match(cgraph,i)){ctx->num_additional_fused_ops=2;ctx->fused_ops_write_mask=1u<<2;fusion_string="TOP2_Q2_GATE_UP_SWIGLU";op_srcs_fused_elementwise[0]=false;op_srcs_fused_elementwise[1]=false;op_srcs_fused_elementwise[2]=true;}else if(qwen_norm.extra){')
    selected={c[c.index('-o')+1]:c for c in recipes(n) if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
    choices=[c for c in selected.values()if 'extern "C" const void *qwen_app_prepare_shader_code('in Path(c[c.index('-c')+1]).read_text()]
    require(len(choices)==1,'One actual linked shader registry required');ac=choices[0];assets=multiple_assets(Path(ac[ac.index('-c')+1]).read_text())
    old=n['GDN_model_comparison']['scope'];scope=dict(old,schema='ps5-qwen-top2-gate-up-model-v1',candidate='two-Expert-Gate-Up',candidate_id=1,
        control_Experts=2,candidate_Experts=2,additional_immutable_shader_count=2,additional_registry_software_capacity=4,
        original_GPU_program_and_F64_qualified_dispatch_unchanged=False,original_GDN_shader_in_both_arms=True,
        qualified_Gate_Up_fixture=30700,no_new_GPU_payload_buffers=True,registered_shader_records_additional_bytes=144)
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
    entry='#include <cstdint>\nextern "C" void qwen_app_gate_up_trial_select(bool);\nextern "C" std::uint64_t qwen_app_gate_up_trial_selections();\nextern "C" void qwen_app_gate_up_trial_release();\n'+entry
    entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);qwen_app_gate_up_trial_select(arm==1);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";','arm==0?"Top2-original-Gate-Up":"Top2-fused-Gate-Up";')
    entry=once(entry,'if(qwen_app_additional_shaders_verified()!=1)','if(qwen_app_additional_shaders_verified()!=2)')
    entry=once(entry,'const auto gdn_before=qwen_app_conv_norm_trial_selections();',
        'const auto gate_up_before=qwen_app_gate_up_trial_selections();const auto gdn_before=qwen_app_conv_norm_trial_selections();')
    entry=once(entry,'            row["phase"]=phase;',
        '            row["Gate_Up_pipeline_selections"]=qwen_app_gate_up_trial_selections()-gate_up_before;\n            row["phase"]=phase;')
    entry=once(entry,'qwen_app_conv_norm_trial_release();qwen_native_driver_complete();',
        'qwen_app_gate_up_trial_release();qwen_app_conv_norm_trial_release();qwen_native_driver_complete();')
    entry=reporting(entry)
    variants={k:(c+['-I',str(ROOT/'native/app')],s)for k,(c,s)in dict(entry=(ec,entry),gpu=(gc,gpu),assets=(ac,assets)).items()}
    inputs=[Path(__file__),ROOT/'tools/multiple_shader_source.py',ROOT/'tools/qualify_post_top2_reporting.py',a.fixture,a.proof,state,backend]
    r,jobs,sources=link(a.parent,a.out,variants,inputs);update_sources(r,jobs,sources)
    for row in r['CPU_metadata_scope']['changed_sources']:
        if row['object_path']==ac[ac.index('-o')+1]:row.update(source=sources['assets'],object_path=jobs['assets'][jobs['assets'].index('-o')+1],command=jobs['assets'])
    r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
    r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['post_top2_gate_up_model']=dict(scope=scope,actual_sources=sources,commands=jobs,qualification=record(a.proof),native_validation_pending=True)
    unsealed=a.out/'unsealed.private.json';write_json(unsealed,r)
    done=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),
        '--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600)
    (a.out/'GPU-provenance.private.log').write_bytes(done.stdout+done.stderr);require(done.returncode==0,done.stderr.decode(errors='replace')[-2800:])
    r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='natively_qualified_Top2_gate_up_full_model_comparison',
        scope=scope,candidate=record(a.out/'receipt.private.json'),original_weights_driver_and_physical_guards=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify GPU finite argmax and compact readback on the real vocabulary shape."""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import recipes
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from multiple_shader_source import transform as multiple_assets
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-finite-greedy-fixture-v1',model_loads=0,requests=0,GPU_graphs=110,cases=11,
    vocabulary=248320,rows=[1,2],first_index_ties=True,all_finite_status_checked=True,
    input_and_output_canaries=True,additional_immutable_shaders=2,synthetic_inputs_only=True,
    deadline_seconds=180,automatic_retries=0,CI_runs=0,production_adoption=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--workgroup',type=int,choices=(32,256),default=32)
    a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    scope=dict(SCOPE,workgroup_size=a.workgroup)
    require(n['lossless_shader_storage']['vulkan_object']['sha256']=='17cb982ec26903fcee469639592d5acd761acd6f883bc35135b9d665fc4b6ad2','Actual selected GPU provider required')
    shader=ROOT/'native/app/gpu_greedy_f32.comp';compiler=a.workspace/'toolchain/shaderc-clang64/clang64/bin/glslc.exe'
    validator=a.workspace/'toolchain/msys-clang64/clang64/bin/spirv-val.exe';spv=a.out/'finite-greedy.spv'
    sc=[str(compiler),'--target-env=vulkan1.1','-O','-fshader-stage=compute',str(shader),'-o',str(spv)]
    for i,c in enumerate([sc,[str(validator),'--target-env','vulkan1.1',str(spv)]]):
        r=subprocess.run(c,capture_output=True,timeout=120);(a.out/f'shader-{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'))
    data=spv.read_bytes();require(data[:4]==b'\x03\x02\x23\x07'and len(data)%4==0,'Valid immutable SPIRV required')
    header=a.out/'finite-greedy-asset.private.h'
    header.write_text('#pragma once\nextern "C" void qwen_app_register_additional_shader(const void*,size_t,const unsigned char*);\n'+
        'alignas(4) static const uint32_t qwen_greedy_spirv[]={'+','.join(hex(x)for x in struct.unpack('<'+'I'*(len(data)//4),data))+'};\n'+
        'static const unsigned char qwen_greedy_sha[]={'+','.join(str(x)for x in hashlib.sha256(data).digest())+'};\n'+
        '__attribute__((constructor)) static void qwen_register_greedy_asset(){qwen_app_register_additional_shader(qwen_greedy_spirv,sizeof(qwen_greedy_spirv),qwen_greedy_sha);}\n',newline='\n')
    gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text()
    gpu=once(gpu,'#include "ggml-vulkan-common.h"','#include "ggml-vulkan-common.h"\n#include '+json.dumps(header.resolve().as_posix()))
    gpu=once(gpu,'"argmax_f32", argmax_f32_len, argmax_f32_data',
        '"qwen_finite_argmax_f32", sizeof(qwen_greedy_spirv), reinterpret_cast<const unsigned char*>(qwen_greedy_spirv)')
    import re
    gpu,count=re.subn(r'("qwen_finite_argmax_f32"[^\n]*?)\{\s*device->subgroup_size\s*\}',lambda m:m[1]+'{'+str(a.workgroup)+'}',gpu)
    require(count==1,'One actual finite-argmax workgroup specialization required')
    selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
    choices=[c for c in selected.values()if 'extern "C" const void *qwen_app_prepare_shader_code('in Path(c[c.index('-c')+1]).read_text()]
    require(len(choices)==1,'One actual shader registry provider required');ac=choices[0];assets=multiple_assets(Path(ac[ac.index('-c')+1]).read_text())
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "greedy_gpu_fixture.h"\n'+entry
    entry=once(entry,'if(qwen_app_additional_shaders_verified()!=1)','if(qwen_app_additional_shaders_verified()!=2)')
    branch=r'''        {if(policy.at("native_GDN_conv_normalization_fixture")!=Json::parse(SCOPE))throw std::runtime_error("Exact finite-greedy fixture scope required");
        qwen_app::enforce_native_model_compute_limits();if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty greedy fixture ledger required");
        auto result=qwen_app::greedy_gpu_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_app_conv_norm_trial_release();qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto ledger=qwen_app::native_model_device_stats();if(ledger.live)throw std::runtime_error("Greedy fixture has live owners");
        const auto&owner=policy.at("native_first_generation_validation");
        result.update({{"schema","ps5-qwen-finite-greedy-fixture-result-v1"},{"completed",true},{"pid",getpid()},{"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},{"device_ledger_live_bytes",ledger.live},{"device_ledger_peak_bytes",ledger.peak},
            {"additional_shaders_verified",qwen_app_additional_shaders_verified()},{"all_model_source_device_owners_positively_retired",true}});
        write_fresh_report(startup.admission_report,result);qwen_native_stage("finite_greedy_fixture_completed_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));}
'''.replace('SCOPE',json.dumps(json.dumps(scope,separators=(',',':'))))
    entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
    deps=[Path(__file__),ROOT/'native/app/greedy_gpu_fixture.h',ROOT/'native/app/finite_greedy.h',shader,header,spv,compiler,validator,ROOT/'tools/multiple_shader_source.py']
    variants={k:(c+['-I',str(ROOT/'native/app')],s)for k,(c,s)in dict(entry=(ec,entry),gpu=(gc,gpu),assets=(ac,assets)).items()}
    r,jobs,sources=link(a.parent,a.out,variants,deps)
    for v in r.values():
        if isinstance(v,dict)and isinstance(v.get('actual_sources'),dict)and 'entry'in v['actual_sources']:
            v['actual_sources']['entry']=sources['entry']
            if isinstance(v.get('commands'),dict)and 'entry'in v['commands']:v['commands']['entry']=jobs['entry']
    r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
    for row in r['CPU_metadata_scope']['changed_sources']:
        if row['object_path']==ac[ac.index('-o')+1]:row.update(source=sources['assets'],object_path=jobs['assets'][jobs['assets'].index('-o')+1],command=jobs['assets'])
    r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
    r['GDN_conv_normalization_fixture']=dict(scope=scope,actual_sources=sources,commands=jobs,shader=record(spv),shader_command=sc,
        headers=[record(header),record(ROOT/'native/app/greedy_gpu_fixture.h')],native_verification_pending=True)
    r['post_top2_greedy_fixture']=dict(scope=scope,actual_sources=sources,commands=jobs,additional_shader_registry_capacity=4)
    seed=a.out/'linked-seed.private.json';write_json(seed,r)
    subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
    r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='finite_greedy_actual_vocabulary_fixture',candidate=record(a.out/'receipt.private.json'),
        scope=scope,original_driver_physical_and_completion_guards_preserved=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()

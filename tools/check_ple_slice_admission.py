#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check strict PLE fixture admission and native compilation, without execution."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    # Synthetic policy bindings test parsing only. They never admit an actual
    # file, shader, SELF, console session or deployment.
    digest='0'*64
    fixture=dict(schema='ps5-qwen-PLE-slice-policy-v1',enabled=True,driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',
        profile='cumulative-idle',native_archive_sha256='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925',
        model_loading_enabled=False,persistent_caches_enabled=False,deterministic_data='original_shapes_not_model_weights',
        maximum_GPU_payload_bytes=16<<20,rounds=8,maximum_graphs=208,maximum_source_scratch_bytes=8<<20,widths=[1,2,3,4],modes=[0,1,2,3])
    storage=dict(schema='ps5-qwen-shader-storage-policy-v1',enabled=True,verify_all_original_assets_before_Vulkan=True,
        model_and_shader_precision_unchanged=True,persistent_caches_enabled=False,registry_sha256=digest,shader_count=1,
        original_bytes=64,stored_bytes=16384,lookup_entries=1,external_file=dict(schema='ps5-qwen-external-shader-file-policy-v1',
        single_read_only_descriptor=True,new_model_source_window=False,bytes=16384,sha256=digest,
        path='/app0/qwen-runtime/shader-storage-'+digest+'.bin',input_window_bytes=16384))
    policy=a.out/'policy.private.json';policy.write_text(json.dumps(dict(native_PLE_slice_validation=fixture,native_shader_storage=storage))+'\n')
    base=dict(schema='ps5-qwen-app-v1',mode='PLE-slice-validation',native_display=False,
        development_policy='/app0/qwen-runtime/development.json',model_receipt='/app0/qwen-runtime/model-receipt.json',web_assets='/app0/qwen-runtime/web')
    configs=[]
    for name,edit in [('valid',{}),('display',dict(native_display=True)),('clock',dict(clock_calibration=dict(console_epoch_ms=1,utc_epoch_ms=1,uncertainty_ms=1)))]:
        path=a.out/(name+'.private.json');path.write_text(json.dumps(dict(base,**edit))+'\n');configs.append(path)
    exe=a.out/'ple-policy.exe';commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
        '-I',str(up/'vendor'),str(ROOT/'tests/ple_slice_policy.cpp'),str(ROOT/'native/app/startup.cpp'),'-o',str(exe)],
        [str(exe),str(policy),*[str(c)for c in configs]]]
    prior_path=a.cache/'build/application-native-metadata-2615/receipt.private.json';prior=json.loads(prior_path.read_text())
    files=[Path(__file__),prior_path,policy,*configs]+[ROOT/f for f in('tests/ple_slice_policy.cpp','native/app/ple_slice_admission.h',
        'native/app/ple_slice_admission.cpp','native/app/ple_convolution_graph.h','native/app/ple_slice_graph.h','native/app/startup.h',
        'native/app/startup.cpp','native/app/validation_policy.h','native/app/native_main.cpp','tools/build_native.py')]
    for name in('ple_slice_admission.cpp','startup.cpp','native_main.cpp'):
        command=next(c.copy()for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name==('llama_engine.cpp'if name=='ple_slice_admission.cpp'else name))
        command[command.index('-c')+1]=str(ROOT/'native/app'/name);command[command.index('-o')+1]=str(a.out/(name+'.o'))
        commands.append(command)
    text=(ROOT/'native/app/native_main.cpp').read_text();branch=text[text.index('if(startup.palette_validation||startup.vector_bank_validation||startup.device_state_validation'):text.index('if (setenv("MESA_SHADER_CACHE_DISABLE", "true", 1) ||')]
    assert branch.index('admit_native_startup_memory()')<branch.index('admit_shader_storage_CPU(')<branch.index('native_resources_started=true')<branch.index('admit_PLE_slice_fixture(')<branch.index('qwen_native_driver_complete()')<branch.index('write_fresh_report(')
    fixture_source=(ROOT/'native/app/ple_slice_admission.cpp').read_text()
    fixture_entry=fixture_source[fixture_source.index('Json admit_PLE_slice_fixture('):]
    assert fixture_entry.index('check(!PLE_slice_CPU_bootstrap(policy)')<fixture_entry.index('qwen_native_gpu_initialize(')
    assert text.index('CPU-only PLE shader bootstrap requires the isolated CPU entry point')<text.index('native_resources_started=true')
    fixed=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,env=env,timeout=180);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('PLE admission '+str(i)+': '+r.stderr.decode(errors='replace')[-2500:])
        if i==1:controls=json.loads(r.stdout)
    assert fixed==[record(f)for f in files]
    result=dict(controls=controls,inputs=fixed,commands=commands,native_units_compiled=3,
        startup_shader_completion_order_source_checked=True,SELF_linked_or_console_admitted=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('inputs','commands')}),flush=True)
if __name__=='__main__':main()

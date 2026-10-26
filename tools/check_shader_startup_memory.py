#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check CPU-only shader attribution policy, native compilation and terminal order."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    source=(ROOT/'native/app/native_main.cpp').read_text();start=source.index('        const bool shader_startup_memory_diagnostic=')
    end=source.index('        if(startup.model_validation || startup.first_generation_validation)',start);block=source[start:end]
    ordered=['require_shader_startup_memory_policy','begin_native_stage_memory_probe','admit_shader_storage_CPU(',
        'end_native_stage_memory_probe','write_fresh_report','shader_startup_memory_CPU_completed_GPU_not_started_waiting_for_ordinary_close','for(;;)']
    positions=[block.index(s)for s in ordered];assert positions==sorted(positions)
    assert not any(s in block for s in('ggml_backend_','qwen_native_gpu_initialize','read_model_receipt(','inspect_container(','start_native_model_sources('))
    files=[Path(__file__)]+[ROOT/name for name in('native/app/native_main.cpp','native/app/validation_policy.h','native/app/shader_startup_memory_policy.h',
        'native/app/native_bootstrap.cpp','native/app/stage_memory_probe.h','tests/shader_startup_memory_policy.cpp')]
    prior_path=a.cache/'build/application-native-PLE-2654/receipt.private.json';files.append(prior_path)
    fixed=[record(f)for f in files];exe=a.out/'shader-startup-policy.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),
        str(ROOT/'tests/shader_startup_memory_policy.cpp'),'-o',str(exe)],[str(exe)]]
    prior=json.loads(prior_path.read_text());native=next(c.copy()for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name=='native_main.cpp')
    native[native.index('-o')+1]=str(a.out/'native_main.o');commands.append(native)
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Shader startup '+str(i)+': '+r.stderr.decode(errors='replace')[-3000:])
        if i==1:controls=json.loads(r.stdout)
    assert controls['scope_refusals']==35 and fixed==[record(f)for f in files]
    result=dict(inputs=fixed,commands=commands,controls=controls,actual_native_main_compiled=True,CPU_terminal_before_model_or_GPU_source_checked=True,
        existing_stage_probe_and_idle_controls_reused=True,PS5_operations=0,SELF_link_or_execution=False,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('inputs','commands')}),flush=True)
if __name__=='__main__':main()

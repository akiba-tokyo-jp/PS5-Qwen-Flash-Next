#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify shared CPU admission order and refusals without GPU or model execution."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(p):
    return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out','policy'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    main=ROOT/'native/app/native_main.cpp';source=main.read_text()
    start=source.index('static void admit_shader_storage_CPU(');end=source.index('\nint main(',start)
    helper=source[start:end];extracted=a.out/'actual_shader_CPU_admission.inc';extracted.write_text(helper,newline='\n')
    branch=source[source.index('if(startup.palette_validation||startup.vector_bank_validation||startup.device_state_validation)'):source.index('if (setenv("MESA_SHADER_CACHE_DISABLE", "true", 1) ||')]
    assert branch.index('admit_shader_storage_CPU(')<branch.index('native_resources_started=true')<branch.index('qwen_app::admit_vector_bank(')
    assert 'qwen_native_gpu_initialize'not in helper and 'ggml_backend_'not in helper
    old=(a.cache/'vector-bank-app-build-2511/source-at-execution/native_main.cpp').read_text()
    old_start=old.index('        if(qwen_app::native_shader_assets_registered()!=policy.contains("native_shader_storage"))')
    old_end=old.index('        if(startup.model_validation || startup.first_generation_validation)',old_start)
    body=old[old_start:old_end].replace('!startup.first_generation_validation','!allow_storage').replace('startup.admission_report','report_path').replace('policy.at("native_first_generation_validation").at("run_id")','run_id')
    body='\n'.join(line[4:]if line.startswith('    ')else line for line in body.splitlines())+'\n'
    assert helper.rstrip('\n')==('static void admit_shader_storage_CPU(const Json &policy,const std::string &report_path,bool allow_storage,const Json &run_id) {\n'+body+'}').rstrip('\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';exe=a.out/'shader-startup-tests.exe'
    files=[main,ROOT/'tests/vector_bank_shader_startup.cpp',a.policy,Path(__file__)]
    fixed=[record(p)for p in files]
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),
        '-I',str(up/'vendor'),str(ROOT/'tests/vector_bank_shader_startup.cpp'),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,cmd in enumerate([command,[str(exe),str(a.policy)]]):
        r=subprocess.run(cmd,capture_output=True,timeout=120,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
    assert fixed==[record(p)for p in files]
    result=json.loads(r.stdout);result.update(shared_old_body_preserved_except_parameters=True,CPU_admission_before_GPU_boundary_source_checked=True,
        inputs=fixed,extracted=record(extracted),command=command,native_execution=False)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','extracted','command')}),flush=True)
if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check headless state-fixture policy and actual native compilation, without execution."""
import argparse,json,os,subprocess
from pathlib import Path
from prepare_device_state_fixture import validate,record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','fixture-manifest','policy','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();m=validate(a.fixture_manifest,a.cache);a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    config=a.out/'app-config.json';config.write_text(json.dumps(dict(schema='ps5-qwen-app-v1',mode='device-state-validation',native_display=False,
        development_policy='/app0/qwen-runtime/development.json',model_receipt='/app0/qwen-runtime/model-receipt.json',web_assets='/app0/qwen-runtime/web'))+'\n')
    main=ROOT/'native/app/native_main.cpp';text=main.read_text();branch=text[text.index('if(startup.palette_validation||startup.vector_bank_validation||startup.device_state_validation)'):text.index('if (setenv("MESA_SHADER_CACHE_DISABLE", "true", 1) ||')]
    assert branch.index('device_state_fixture_linked()')<branch.index('admit_shader_storage_CPU(')<branch.index('native_resources_started=true')<branch.index('admit_device_state_fixture(')
    exe=a.out/'device-policy-tests.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),str(ROOT/'tests/device_state_policy.cpp'),str(ROOT/'native/app/startup.cpp'),'-o',str(exe)],
        [str(exe),str(a.policy),str(config)]]
    base=json.loads((a.cache/'build/application-native-palette-2535/receipt.private.json').read_text())
    native=next(c for c in base['compile_commands']if Path(c[c.index('-c')+1]).name=='padded_bank_layout.cpp').copy()
    native[native.index('-c')+1]=str(ROOT/'native/app/device_state_admission.cpp');native[native.index('-o')+1]=str(a.out/'device-state.o')
    native+=['-Wall','-Wextra','-Werror','-DQWEN_DEVICE_STATE_FIXTURE=1','-I',str(Path(m['generated']['path']).parent)];commands.append(native)
    files=[main,ROOT/'native/app/device_state_admission.h',ROOT/'native/app/device_state_admission.cpp',ROOT/'native/app/startup.cpp',ROOT/'native/app/startup.h',ROOT/'tests/device_state_policy.cpp',a.policy,config,Path(__file__),a.fixture_manifest]
    fixed=[record(p)for p in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'));controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=240,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Step '+str(i)+' failed: '+r.stderr.decode(errors='replace')[-4000:])
        if i==1:controls=json.loads(r.stdout)
    assert fixed==[record(p)for p in files]
    result=dict(host_policy=controls,native_unit_compiled=True,CPU_and_link_admission_before_GPU_source_checked=True,inputs=fixed,commands=commands,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','commands')}),flush=True)
if __name__=='__main__':main()

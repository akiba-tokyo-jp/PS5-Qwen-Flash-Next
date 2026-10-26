#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check strict prefix policy, actual F32-bit SHA and native integration units."""
import argparse,hashlib,json,os,struct,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    policy=json.loads((a.cache/'hardware-first-generation-2240/private-policy/development.json').read_text())
    policy['native_prefix_validation']=dict(schema='ps5-qwen-exact-prefix-validation-v1',enabled=True,prefix_reuse_enabled=True,
        context_tokens=256,prefill_tokens=4,prompt_tokens=30,maximum_output_tokens=32,maximum_requests=2,
        maximum_state_bytes=136<<20,maximum_metadata_bytes=1<<20,maximum_additional_CPU_bytes=8<<20,
        maximum_logit_records_per_request=33,full_F32_logit_fingerprints=True,additional_GPU_downloads=0,
        checkpoint_qualification_SELF_SHA256='b10752c83004a13f4941f5503b1557e5fe72c841057f29ec7553937918ebd1f0',
        checkpoint_qualification_result_SHA256='e9d0db6bfb5b2d090e021c972cf14728f3a7d96b956c03b08946a60d6fdb50d7')
    policy_path=a.out/'policy.private.json';policy_path.write_text(json.dumps(policy,indent=2)+'\n')
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    policy_exe=a.out/'prefix-policy.exe';hash_exe=a.out/'logit-fingerprint.exe'
    common=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor')]
    commands=[common+[str(ROOT/'tests/prefix_validation_policy.cpp'),'-o',str(policy_exe)],[str(policy_exe),str(policy_path)],
        common+['-I',str(up/'vendor/hash'),str(ROOT/'native/app/model_integrity.cpp'),str(ROOT/'native/app/sha256_backend.cpp'),str(ROOT/'tests/model_logit_fingerprint.cpp'),'-o',str(hash_exe)],
        [str(hash_exe)]]
    prior=json.loads((a.cache/'build/application-native-checkpoint-2576/receipt.private.json').read_text())
    for name in('llama_engine.cpp','model_checkpoint.cpp','model_integrity.cpp','native_main.cpp'):
        c=next(c for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name==name).copy()
        c[c.index('-o')+1]=str(a.out/(name+'.o'));c+=['-Wall','-Wextra','-Werror']
        if name=='native_main.cpp':
            for i in range(len(c)-1):
                if c[i]=='-I'and Path(c[i+1])==up/'common':c[i]='-isystem'
        commands.append(c)
    files=[Path(__file__),policy_path,*[ROOT/'tests'/n for n in('prefix_validation_policy.cpp','model_logit_fingerprint.cpp')]]
    files+=list((ROOT/'native/app').glob('*.h'))+list((ROOT/'native/app').glob('*.cpp'));fixed=[record(f)for f in files]
    controls={}
    for index,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,env=env,timeout=300);(a.out/(str(index)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Prefix check '+str(index)+': '+r.stderr.decode(errors='replace')[-3500:])
        if index in(1,3):controls[str(index)]=json.loads(r.stdout)
    raw=struct.pack('<8I',0,0x80000000,0x3f800001,0xbf800001,1,0x007fffff,0x7f7fffff,0xff7fffff)
    assert controls['3']['sha256']==hashlib.sha256(raw).hexdigest()and controls['1']['policy_refusals']==27
    assert fixed==[record(f)for f in files]
    result=dict(inputs=fixed,commands=commands,controls=controls,all_four_native_units_compiled=True,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(host_policy_refusals=27,actual_F32_bit_SHA256_matches=True,all_four_native_units_compiled=True,PS5_operations=0,CI_runs=0)),flush=True)
if __name__=='__main__':main()

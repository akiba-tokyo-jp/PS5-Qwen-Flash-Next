#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check bounded GPU-bank policy and compile its native client without executing."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(path):
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','cache','out','policy'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--app-config',type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False);(args.out/'tmp').mkdir()
    upstream=args.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    host=args.workspace/'toolchain/msys-clang64/clang64/bin';exe=args.out/'policy-tests.exe'
    config=args.app_config or args.out/'app-config.json'
    if args.app_config is None:
        config.write_text(json.dumps(dict(schema='ps5-qwen-app-v1',mode='vector-bank-validation',native_display=False,
            development_policy='/app0/qwen-runtime/development.json',model_receipt='/app0/qwen-runtime/model-receipt.json',web_assets='/app0/qwen-runtime/web'))+'\n')
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(upstream/'vendor'),str(ROOT/'tests/vector_bank_policy.cpp'),str(ROOT/'native/app/startup.cpp'),'-o',str(exe)],
        [str(exe),str(args.policy),str(config)]]
    base=json.loads((args.cache/'build/application-native-frame-2183/receipt.private.json').read_text())
    native=next(c for c in base['compile_commands']if Path(c[c.index('-c')+1]).name=='padded_bank_layout.cpp').copy()
    native[native.index('-c')+1]=str(ROOT/'native/app/vector_bank_admission.cpp');native[native.index('-o')+1]=str(args.out/'vector-bank.o')
    native+=['-Wall','-Wextra','-Werror'];commands.append(native)
    inputs=[record(p)for p in [ROOT/'native/app/vector_bank_admission.h',ROOT/'native/app/vector_bank_admission.cpp',ROOT/'native/app/vectored_source_batch.h',ROOT/'native/app/batch_io_journal.h',ROOT/'native/app/startup.cpp',ROOT/'native/app/startup.h',ROOT/'tests/vector_bank_policy.cpp',args.policy,config,Path(__file__)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(args.out/'tmp'),TEMP=str(args.out/'tmp'))
    controls=None
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=180,env=env)
        (args.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Step '+str(i)+' failed: '+result.stderr.decode(errors='replace')[-3000:])
        if i==1:controls=json.loads(result.stdout)
    assert all(record(Path(row['path']))==row for row in inputs)
    result=dict(host_policy=controls,native_unit_compiled=True,inputs=inputs,commands=commands,PS5_executions=0,GPU_calls=0,CI_runs=0)
    (args.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','commands')}),flush=True)
if __name__=='__main__':main()

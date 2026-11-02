#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build/run one original-digest-bound CPU restoration of a live bundle file."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','bundle-plan','CPU-providers','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    plan=load(args.bundle_plan);need(plan['completed'] and plan['quantization_changes']==plan['source_writes']==0,'Exact lossless restoration plan required')
    need(record(plan['header']['path'])==plan['header'],'Prepared original pack inputs changed')
    native=ROOT/'native/qwen_flash_next/expert_q2_bundle_pack.cpp';text=native.read_text()
    for before,after in (('constexpr size_t owned_bytes=8u<<20;','constexpr size_t owned_bytes=4u<<20;'),
                         ('readback=scratch+(4u<<20);','readback=scratch;'),
                         ('window_bytes=8388608','window_bytes=4194304')):
        need(text.count(before)==1,'Exact serial CPU scratch ownership boundary required')
        text=text.replace(before,after,1)
    marker='line("BUNDLE index="+std::to_string(i)+" layer="+std::to_string(v.layer)+" Expert="+std::to_string(v.expert)+" SHA256="+expected[i]);'
    need(text.count(marker)==1,'One completed copy checkpoint required')
    text=text.replace(marker,marker+'\n        if((i+1)%32==0)need(!fsync(output),"Owned CPU copy checkpoint fsync failed");',1)
    marker='line("SEALED bytes="+std::to_string(bundle_probe_file_bytes)+" SHA256="+hex(whole)+'
    need(text.count(marker)==1,'Exact successful native seal boundary required')
    text=text.replace(marker,'const auto restored_digest=hex(whole);need(restored_digest=='+json.dumps(plan['expected_SHA256'])+',"Restored complete original bundle digest differs");\n    line("SEALED bytes="+std::to_string(bundle_probe_file_bytes)+" SHA256="+restored_digest+',1)
    text='extern "C" int qwen_bundle_payload_main(int,char**);\n#define main qwen_bundle_payload_main\n'+text
    source=args.out/'packer.cpp';source.write_text(text,encoding='utf-8',newline='\n')
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk';llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    upstream=Path('D:/PS5-AI/qwen-flash-next/upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569')
    obj=args.out/'packer.o'
    command=[str(llvm/'clang++.exe'),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
        '-isystem',str(sdk/'target/include/c++/v1'),'-isystem',str(sdk/'target/include'),'-std=c++17',
        '-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',str(Path(plan['header']['path']).parent),'-I',str(ROOT/'native/app'),
        '-I',str(upstream/'vendor'),'-c',str(source),'-o',str(obj)]
    run=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'compile.private.log').write_bytes(run.stdout+run.stderr);need(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
    provider=load(args.CPU_providers)['actual_current_CPU_providers']['SHA256'];need(record(provider['path'])==provider,'Actual current SHA provider changed')
    retained=load(args.current/'provenance/retained-relink-inputs.private.json');wanted={'libc++.a','libc++abi.a','libunwind.a','libclang_rt.builtins-x86_64.a'}
    libraries=[{k:r[k] for k in ('path','bytes','sha256')} for r in retained if Path(r['original_path']).name in wanted]
    need(len(libraries)==4,'Four actual current C++/unwind/compiler providers required')
    link=dict(CPU_only=True,source_writes=0,GPU_calls=0,Direct_CPU_bytes=4<<20,
              objects=[record(obj),provider],libraries=libraries,source=record(native),derived=record(source),compile_command=command,
              original_whole_SHA256_required=plan['expected_SHA256'],bundle_plan=record(args.bundle_plan))
    old=current_files(args.current);controller=build(args.workspace,args.mount_plan,old,old,[],'restore-bundle',args.out/'controller',bundle_link=link)
    save(args.out/'plan.private.json',dict(completed=True,bundle_plan=record(args.bundle_plan),controller=record(args.out/'controller/plan.private.json'),CPU_only=True,GPU_calls=0))
    if not args.execute:print('Original-digest-bound CPU packer built; PS5 operations=0');return
    state_path=args.current/'active-console.private.json';state=load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['unknown_completion'],
         'Positively idle original application required for startup data repair')
    state['startup_bundle_repair']=dict(phase='CPU-copy-in-progress',plan=record(args.out/'plan.private.json'),output=plan['output'])
    state['unknown_completion']=True
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    try:
        result=execute(lan_module(),controller,args.out/'controller')
    except BaseException:
        receipt=args.out/'controller/result.private.json'
        if receipt.exists() and load(receipt).get('helper_exited') is True:
            state['unknown_completion']=False;state['startup_bundle_repair']['phase']='known-helper-refusal-ordinarily-retired'
            state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
        raise
    raw=(args.out/'controller/execution/console.private.log').read_bytes()
    seal=re.search(rb'SEALED bytes=(\d+) SHA256=([0-9a-f]{64}) identity=([0-9,]+) mode=0444 original_sources_preserved=1',raw)
    need(seal and int(seal[1])==plan['output_bytes'] and seal[2].decode()==plan['expected_SHA256'] and
         b'DIRECT known_completion_cleanup_returned=1 fully_released=1' in raw,'Exact original whole SHA and positive CPU Direct release required')
    identity=list(map(int,seal[3].split(b',')));need(len(identity)==10 and identity[2:5]==[0o100444,0,0] and identity[5]==plan['output_bytes'],'Complete immutable new inode identity required')
    restored=dict(completed=True,path=plan['output'],bytes=plan['output_bytes'],sha256=plan['expected_SHA256'],identity=identity,
        identity_provider_symbol=plan['identity_provider_symbol'],old_identity=plan['old_identity'],
        full_native_SHA256_readback=True,CPU_Direct_positively_retired=True,original_sources_unchanged=True,
        current_seven_files_native_hashed=True,helper_exited=True,helper_files_removed=True,
        quantization_changes=0,GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0,Direct_CPU_bytes=4<<20,
        native_result=record(args.out/'controller/result.private.json'))
    save(args.out/'result.private.json',restored)
    state['unknown_completion']=False;state['startup_bundle_repair'].update(phase='exact-original-bytes-restored',result=record(args.out/'result.private.json'))
    state.setdefault('restored_required_bundle_inputs',[]).append({k:restored[k] for k in ('path','bytes','sha256','identity','identity_provider_symbol')})
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in restored.items() if k not in ('path','identity','old_identity','native_result')}))


if __name__=='__main__':main()

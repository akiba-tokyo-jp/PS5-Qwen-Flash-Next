#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare original and fused complete-sort SPIRV on a pinned software backend."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess

from build_performance_quantizer import record
from native_dispatch import ELF
from shader_storage import unpack
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','build','software-ICD','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();built=load(a.build);need(built['completed'] and built['original_full_bitonic_tie_schedule_preserved'],'Prepared fused full sort required')
    need(record(built['shader']['path'])==built['shader'],'Fused shader changed')
    a.out.mkdir(parents=True,exist_ok=False)
    native=ELF(a.current/'provenance/qwen-native.pie.elf');token=native.symbol_data('argsort_f32_data')
    magic,offset,stored,decoded=struct.unpack('<8sQII',token)
    need(magic==b'QWSPVX01' and token.hex()==built['original_shader_token'],'Exact original linked shader token required')
    storage=next((a.current/'qwen-runtime').glob('shader-storage-*.bin'));blob=storage.read_bytes()[offset:offset+stored]
    raw=unpack(blob);need(len(raw)==decoded,'Exact original shader decoded length required')
    original=a.out/'original-argsort.spv';original.write_bytes(raw)
    common=ROOT/'tools/check_iq2_paired_down_gpu.cpp';focused=ROOT/'tools/check_fused_rank_software.cpp'
    prefix=common.read_text(encoding='utf-8').split('Json check(',1)[0]
    source=a.out/'desktop.cpp';source.write_text(prefix+focused.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    exe=a.out/'fused-sort.exe';command=[str(host/'clang++.exe'),'-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',
        '-I',str(a.workspace/'toolchain/Vulkan-Headers/include'),'-I',str(up/'vendor'),str(source),'-o',str(exe)]
    env=os.environ.copy();env['PATH']=str(host)+os.pathsep+env.get('PATH','');env['VK_DRIVER_FILES']=str(a.software_ICD)
    library=(a.software_ICD.parent/load(a.software_ICD)['ICD']['library_path']).resolve()
    need(library.name=='vk_swiftshader.dll' and library.exists(),'An installed explicit software ICD is required')
    result=subprocess.run(command,capture_output=True,env=env,timeout=240);(a.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,'Focused software checker compile failed')
    output=a.out/'software.private.json';execute=[str(exe),str(original),built['shader']['path'],str(output)]
    save(a.out/'intent.private.json',dict(build=record(a.build),inputs=[record(x) for x in (common,focused,a.software_ICD,library,storage)],
        command=command,execute=execute,maximum_dispatches=64,original_cases=16,fused_cases=48,PS5_operations=0))
    result=subprocess.run(execute,capture_output=True,env=env,timeout=600);(a.out/'run.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,'Focused software sort failed; inspect the existing case journal')
    checked=load(output);need(checked['completed'] and checked['positive_fences']==64 and checked['all_resources_positively_retired'],'All finite cases must positively retire')
    save(a.out/'result.private.json',dict(completed=True,build=record(a.build),software=record(output),original_shader=record(original),
        source=record(source),executable=record(exe),positive_fences=64,original_cases=16,fused_cases=48,
        original_512_execution_not_software_qualified=True,full_indices_and_ties_exact=True,alias_canaries_exact=True,
        PS5_operations=0,PS5_speed_claimed=False,native_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,positive_software_fences=64,full_order_exact=True,PS5_operations=0)))


if __name__=='__main__':main()

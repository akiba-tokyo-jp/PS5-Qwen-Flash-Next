#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and cross-check a bounded host Q4_0 encoder against pinned ggml Python."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import time
from expert_q4 import pinned_gguf, record, require, write_json, independent_dequantize
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','cache','samples','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    dll=a.out/'expert-q4-encode.dll';exe=a.out/'expert-q4-geometry.exe'
    commands=[
        [host/'clang.exe','-std=c11','-O3','-ffp-contract=off','-shared',ROOT/'tools/expert_q4_quantize.c','-o',dll],
        [host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app',ROOT/'tests/expert_q4_geometry.cpp','-o',exe],
        [exe]]
    for i,c in enumerate(commands):
        r=subprocess.run(list(map(str,c)),cwd=ROOT,capture_output=True,timeout=120,env=env)
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        require(r.returncode==0,r.stderr.decode(errors='replace')[-2500:])
    os.add_dll_directory(str(host));lib=ctypes.CDLL(str(dll.resolve()));fn=lib.qwen_quantize_bf16_q4_0
    fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];fn.restype=ctypes.c_int
    gguf,np=pinned_gguf(a.cache);samples=json.loads(a.samples.read_text());timings=[]
    for item in samples['matrices']:
        raw=Path(item['original']['path']).read_bytes();require(record(item['original']['path'])['sha256']==item['original']['sha256'],'Original sample changed')
        src=np.frombuffer(raw,dtype='<u2');out=np.empty(src.size//32*18,dtype=np.uint8)
        begin=time.perf_counter();rc=fn(src.ctypes.data,out.ctypes.data,src.size);timings.append(time.perf_counter()-begin)
        require(rc==0,'Host Q4 encoder returned a failure')
        expected=(np.frombuffer(raw,dtype='<u2').astype(np.uint32)<<16).view(np.float32)
        expected=gguf.quants.quantize(expected,gguf.GGMLQuantizationType.Q4_0)
        require(np.array_equal(out,expected),'Independent native encoder differs from pinned Q4_0')
    for size in (0,1,31,33):
        require(fn(src.ctypes.data,out.ctypes.data,size)==1,'Malformed Q4 block size was accepted')
    bad=np.full(32,0x7f80,dtype=np.uint16)
    require(fn(bad.ctypes.data,out.ctypes.data,32)==2,'Nonfinite original weights were accepted')
    write_json(a.out/'receipt.private.json',dict(schema='ps5-qwen-expert-q4-host-encoder-v1',completed=True,
        library=record(dll),geometry_executable=record(exe),sample_source=record(a.samples),
        inputs=[record(x)for x in(Path(__file__),ROOT/'tools/expert_q4_quantize.c',ROOT/'native/app/expert_q4_geometry.h',ROOT/'tests/expert_q4_geometry.cpp')],
        native_encoded_matrices=27,all_native_bytes_match_pinned_Q4_0=True,invalid_inputs_refused=5,
        mean_matrix_seconds=sum(timings)/len(timings),console_operations=0,model_inference=False,CI_runs=0))
    print(json.dumps(dict(native_encoder_crosscheck_passed=True,matrices=27,mean_matrix_seconds=sum(timings)/len(timings))),flush=True)


if __name__=='__main__':main()

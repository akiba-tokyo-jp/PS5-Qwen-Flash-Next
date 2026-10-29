#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare fragmented accelerated/scalar SHA ABI against Python hashlib."""
import argparse,ctypes,hashlib,json,os,random,subprocess,time
from pathlib import Path
from expert_q4 import LOCK,record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'third_party/sha-intrinsics';origin=json.loads((source/'source.json').read_text())
    require(record(source/'sha256-x86.c')['sha256']==origin['sha256'],'Pinned public-domain compression source changed')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';dll=a.out/'sha256-accelerated.dll'
    upstream=a.cache/'upstream'/('llama.cpp-'+LOCK['llama_cpp']['revision'])
    command=[host/'clang++.exe','-std=c++17','-O3','-msha','-msse4.1','-shared','-I',upstream/'vendor','-I',upstream/'vendor/hash',
        ROOT/'native/app/sha256_accelerated_backend.cpp',ROOT/'tests/sha256_acceleration.cpp','-o',dll]
    r=subprocess.run(list(map(str,command)),capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
    (a.out/'build.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-3500:])
    os.add_dll_directory(str(host));lib=ctypes.CDLL(str(dll));fn=lib.qwen_sha256_test
    fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_int]
    randomizer=random.Random(7600);controls=0
    def test(raw,chunk,scalar,offset=0):
        nonlocal controls
        source=ctypes.create_string_buffer(b'\xa5'*offset+raw);out=ctypes.create_string_buffer(32)
        fn(out,ctypes.addressof(source)+offset,len(raw),chunk,scalar)
        require(out.raw==hashlib.sha256(raw).digest(),'Incremental SHA256 differs from hashlib');controls+=1
    for size in (0,1,2,31,55,56,57,63,64,65,127,128,129,255,256,257,1024,65535,65536,65537):
        raw=randomizer.randbytes(size)
        for chunk in (1,7,31,63,64,65,127,4096,8388608):
            for scalar in (0,1):test(raw,chunk,scalar,size%16)
    for _ in range(64):
        size=randomizer.randrange(1,100000);test(randomizer.randbytes(size),randomizer.randrange(1,5000),0,randomizer.randrange(16))
    block=randomizer.randbytes(8<<20);timings={}
    for scalar in (1,0):
        begin=time.perf_counter();test(block,len(block),scalar);timings[str(scalar)]=time.perf_counter()-begin
    write_json(a.out/'receipt.private.json',dict(completed=True,hashlib_and_scalar_controls=controls,
        host_SHA_instructions_available=bool(lib.qwen_sha256_acceleration_available()),timings_8MiB_seconds=timings,
        library=record(dll),command=list(map(str,command)),source=origin,
        inputs=[record(x)for x in(Path(__file__),ROOT/'native/app/sha256_accelerated_backend.cpp',ROOT/'tests/sha256_acceleration.cpp',source/'source.json',source/'sha256-x86.c')],
        console_operations=0,production_backend_changed=False))
    print(json.dumps(dict(SHA256_conformance_controls=controls,host_SHA_instructions_available=bool(lib.qwen_sha256_acceleration_available()),
        timings_8MiB_seconds=timings,production_backend_changed=False)),flush=True)

if __name__=='__main__':main()

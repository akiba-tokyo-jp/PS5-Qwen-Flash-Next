#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the native codec with pinned GGUF decoding and encoding."""
import argparse,ctypes,os,subprocess,sys,types
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tools'));from expert_q4 import LOCK
    pkg=types.ModuleType('gguf');pkg.__path__=[str(a.cache/('upstream/llama.cpp-'+LOCK['llama_cpp']['revision'])/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.quants import Q2_K,Q2_0
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';a.out.mkdir(parents=True,exist_ok=False);dll=a.out/'repack.dll'
    subprocess.run([str(host/'clang.exe'),'-std=c11','-O3','-ffp-contract=off','-shared',str(root/'tools/expert_q2_repack.c'),'-o',str(dll)],check=True)
    os.add_dll_directory(str(host));lib=ctypes.CDLL(str(dll));run=lib.qwen_repack_q2k_q20;run.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];run.restype=ctypes.c_int
    rng=np.random.default_rng(12002);encoded=rng.integers(0,256,size=(4096,84),dtype=np.uint8)
    scales=rng.uniform(0,0.02,size=(4096,2)).astype('<f2');encoded[:,80:84]=scales.view(np.uint8).reshape(-1,4)
    decoded=Q2_K.dequantize(encoded);expected=Q2_0.quantize(decoded).reshape(-1);output=np.empty(expected.size,dtype=np.uint8)
    assert run(encoded.ctypes.data,output.ctypes.data,4096)==0 and np.array_equal(output,expected)
    assert run(encoded.ctypes.data,output.ctypes.data,0)!=0
    bad=np.array(encoded[0],copy=True).reshape(-1);bad[80:82]=[0,124]
    assert run(bad.ctypes.data,output.ctypes.data,1)!=0
    print('PASS: 1048576 decoded values,294912 exact Q2_0 bytes; zero blocks and nonfinite source refused.')

if __name__=='__main__':main()

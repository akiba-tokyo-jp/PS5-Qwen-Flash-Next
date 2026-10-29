#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare Q2_0 component assets from the preserved original BF16 samples."""
import argparse,ctypes,json,os,subprocess,time
from pathlib import Path
from expert_q4 import pinned_gguf,record,require,write_json,sha,MATRIX_VALUES
ROOT=Path(__file__).resolve().parents[1]

def independent_dequantize(raw,np):
    blocks=np.frombuffer(raw,dtype=np.uint8).reshape(-1,18)
    scales=blocks[:,:2].copy().view('<f2').astype(np.float32)
    packed=blocks[:,2:]
    return (((packed[:,:,None]>>np.array([0,2,4,6],dtype=np.uint8))&3).reshape(-1,64).astype(np.int16)-1)*scales

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','workspace','samples','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    gguf,np=pinned_gguf(a.cache);old=json.loads(a.samples.read_text())
    require(old['completed']and len(old['matrices'])==27,'Complete original component provenance required')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';dll=a.out/'expert-q2-encode.dll'
    command=[str(host/'clang.exe'),'-std=c11','-O3','-ffp-contract=off','-shared',str(ROOT/'tools/expert_q2_quantize.c'),'-o',str(dll)]
    r=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
    (a.out/'compile.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'))
    os.add_dll_directory(str(host));lib=ctypes.CDLL(str(dll));fn=lib.qwen_quantize_bf16_q2_0
    fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];fn.restype=ctypes.c_int
    m=dict(schema='ps5-qwen-expert-q2-samples-v1',format='Q2_0',completed=False,matrices=[],
        original_sample_manifest=record(a.samples),library=record(dll),source=record(ROOT/'tools/expert_q2_quantize.c'),
        model_quality_qualified=False,console_operations=0)
    pack=a.out/'expert-q2-samples.bin';times=[]
    with pack.open('xb')as f:
        for item in old['matrices']:
            source=item['original'];require(record(source['path'])==source,'Original sample changed')
            raw=Path(source['path']).read_bytes();require(len(raw)==MATRIX_VALUES*2,'Original Expert matrix differs')
            src=np.frombuffer(raw,dtype='<u2');out=np.empty(MATRIX_VALUES//64*18,dtype=np.uint8)
            begin=time.perf_counter();require(fn(src.ctypes.data,out.ctypes.data,src.size)==0,'Q2 encoder failed');times.append(time.perf_counter()-begin)
            x=(src.astype(np.uint32)<<16).view(np.float32)
            reference=gguf.quants.quantize(x,gguf.GGMLQuantizationType.Q2_0)
            require(np.array_equal(out,reference),'Native Q2 bytes differ from pinned quantizer')
            decoded=independent_dequantize(out.tobytes(),np).reshape(-1)
            require(np.array_equal(decoded,gguf.quants.dequantize(out,gguf.GGMLQuantizationType.Q2_0)),'Independent Q2 decoder differs')
            row={k:item[k]for k in ('layer','role','expert','columns','rows','original')}
            row.update(q2_payload_sha256=sha(out.tobytes()),q2_payload_bytes=out.size,
                weight_NRMSE=float(np.linalg.norm(decoded.astype(np.float64)-x)/np.linalg.norm(x.astype(np.float64))))
            for label,data in (('bf16',raw),('q2',out.tobytes())):
                f.write(bytes((-f.tell())%16384));row[label+'_offset']=f.tell();f.write(data)
            m['matrices'].append(row)
        f.write(bytes((-f.tell())%16384));f.flush();os.fsync(f.fileno())
    for count in (0,1,63,65):require(fn(src.ctypes.data,out.ctypes.data,count)==1,'Invalid block accepted')
    for bits in (0x7f80,0x7fc0,0xff80):
        bad=np.full(64,bits,dtype=np.uint16);require(fn(bad.ctypes.data,out.ctypes.data,64)==2,'Nonfinite BF16 accepted')
    m.update(completed=True,pack=record(pack),all_native_bytes_match_pinned_Q2_0=True,invalid_inputs_refused=7,
        mean_encode_seconds=sum(times)/len(times),effective_bits_per_weight=2.25)
    write_json(a.out/'manifest.private.json',m)
    print(json.dumps(dict(Q2_component_assets=27,pinned_byte_equality=True,weight_NRMSE_range=[min(r['weight_NRMSE']for r in m['matrices']),max(r['weight_NRMSE']for r in m['matrices'])])),flush=True)
if __name__=='__main__':main()

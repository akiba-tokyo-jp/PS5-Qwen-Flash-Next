#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare Q2_K component assets from the preserved original BF16 samples."""
import argparse,ctypes,json,os,subprocess,time
from pathlib import Path
from expert_q4 import pinned_gguf,record,require,write_json,sha,MATRIX_VALUES
ROOT=Path(__file__).resolve().parents[1]

def independent_dequantize(raw,np):
    blocks=np.frombuffer(raw,dtype=np.uint8).reshape(-1,84)
    d=blocks[:,80:82].copy().view('<f2').astype(np.float32)
    dm=blocks[:,82:84].copy().view('<f2').astype(np.float32)
    scales=blocks[:,:16];q=blocks[:,16:80]
    decoded=np.empty((blocks.shape[0],256),dtype=np.float32)
    for i in range(256):
        group=i//16
        value=(q[:,(i//128)*32+i%32]>>(2*((i%128)//32)))&3
        decoded[:,i]=d[:,0]*(scales[:,group]&15)*value-dm[:,0]*(scales[:,group]>>4)
    return decoded

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','workspace','samples','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    gguf,np=pinned_gguf(a.cache);old=json.loads(a.samples.read_text())
    require(old['completed']and len(old['matrices'])==27,'Complete original component provenance required')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';dll=a.out/'expert-q2k-encode.dll'
    command=[str(host/'clang.exe'),'-std=c11','-O3','-ffp-contract=off','-shared',str(ROOT/'tools/expert_q2k_quantize.c'),'-o',str(dll)]
    r=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
    (a.out/'compile.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'))
    os.add_dll_directory(str(host));lib=ctypes.CDLL(str(dll));fn=lib.qwen_quantize_bf16_q2_K
    fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];fn.restype=ctypes.c_int
    m=dict(schema='ps5-qwen-expert-q2-samples-v1',format='Q2_K',completed=False,matrices=[],
        original_sample_manifest=record(a.samples),library=record(dll),source=record(ROOT/'tools/expert_q2k_quantize.c'),
        model_quality_qualified=False,console_operations=0)
    pack=a.out/'expert-q2-samples.bin';times=[]
    with pack.open('xb')as f:
        for item in old['matrices']:
            source=item['original'];require(record(source['path'])==source,'Original sample changed')
            raw=Path(source['path']).read_bytes();require(len(raw)==MATRIX_VALUES*2,'Original Expert matrix differs')
            src=np.frombuffer(raw,dtype='<u2');out=np.empty(MATRIX_VALUES//256*84,dtype=np.uint8)
            begin=time.perf_counter();require(fn(src.ctypes.data,out.ctypes.data,src.size)==0,'Q2 encoder failed');times.append(time.perf_counter()-begin)
            x=(src.astype(np.uint32)<<16).view(np.float32)
            require(out.size==537600,'Q2_K matrix byte geometry differs')
            decoded=independent_dequantize(out.tobytes(),np).reshape(-1)
            require(np.array_equal(decoded,gguf.quants.dequantize(out,gguf.GGMLQuantizationType.Q2_K)),'Independent Q2 decoder differs')
            row={k:item[k]for k in ('layer','role','expert','columns','rows','original')}
            row.update(q2_payload_sha256=sha(out.tobytes()),q2_payload_bytes=out.size,
                weight_NRMSE=float(np.linalg.norm(decoded.astype(np.float64)-x)/np.linalg.norm(x.astype(np.float64))))
            for label,data in (('bf16',raw),('q2',out.tobytes())):
                f.write(bytes((-f.tell())%16384));row[label+'_offset']=f.tell();f.write(data)
            m['matrices'].append(row)
        f.write(bytes((-f.tell())%16384));f.flush();os.fsync(f.fileno())
    for count in (0,1,255,257):require(fn(src.ctypes.data,out.ctypes.data,count)==1,'Invalid block accepted')
    for bits in (0x7f80,0x7fc0,0xff80):
        bad=np.full(256,bits,dtype=np.uint16);require(fn(bad.ctypes.data,out.ctypes.data,256)==2,'Nonfinite BF16 accepted')
    m.update(completed=True,pack=record(pack),pinned_ggml_C_reference_encoder=True,invalid_inputs_refused=7,
        mean_encode_seconds=sum(times)/len(times),effective_bits_per_weight=2.625)
    write_json(a.out/'manifest.private.json',m)
    print(json.dumps(dict(Q2_component_assets=27,pinned_byte_equality=True,weight_NRMSE_range=[min(r['weight_NRMSE']for r in m['matrices']),max(r['weight_NRMSE']for r in m['matrices'])])),flush=True)
if __name__=='__main__':main()

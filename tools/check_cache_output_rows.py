#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce zero-output cropping with real GGML and cache eligibility code."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--model-io-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir()
    manifest=json.loads(a.model_io_manifest.read_text());source=a.model_io_manifest.parent/'source/src/llama-moe-cache.cpp'
    digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest==manifest['sources']['src/llama-moe-cache.cpp']['patched_sha256']
    text=source.read_text();start=text.index('    ggml_tensor * get_slot_map(');end=text.index('    ggml_tensor * get_experts(',start)
    header='''struct ActualCacheEligibility {
    struct layer { int32_t ig; ggml_tensor * slot_map; mutable bool eligibility_reported; };
    struct group { int32_t n_slots; };
    std::vector<layer> layers; std::vector<group> groups;
    static constexpr int64_t max_batch=32;
'''+text[start:end]+'};\n'
    (a.out/'actual_cache_eligibility.h').write_text(header,encoding='utf-8',newline='\n')
    base=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    libs=[]
    for name in ['ggml.a','ggml-cpu.a','ggml-base.a']:
        rows=list((a.cache/'host-CPU-reference-066/build').rglob(name))+list((a.cache/'host-CPU-reference-066/build').rglob('lib'+name));assert len(rows)==1;libs.append(str(rows[0]))
    exe=a.out/'cache-output-rows.exe';command=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(a.out),'-I',str(base/'ggml/include'),str(ROOT/'tests/cache_output_rows.cpp'),'-Wl,--start-group',*libs,'-Wl,--end-group','-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for label,cmd in [('compile',command),('run',[str(exe)])]:
        r=subprocess.run(cmd,capture_output=True,env=env,timeout=90);(a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Actual cache output-row '+label+' failed')
    result=json.loads(r.stdout);result.update(actual_cache_method_sha256=digest,model_inference=False,console_requests=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()

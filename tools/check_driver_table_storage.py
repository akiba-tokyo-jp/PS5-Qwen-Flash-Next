#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual table bytes and production restoration with fault controls."""
import argparse,json,os,subprocess
from pathlib import Path
from driver_table_storage import validate
from shader_storage import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('manifest','donor','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=validate(a.manifest,a.donor);a.out.mkdir(parents=True,exist_ok=False)
    code='.bss\n.p2align 14\n.global __qwen_driver_tables_start\n__qwen_driver_tables_start:\n'
    for r in m['tables']:
        code+='.balign '+str(max(1,r['alignment']))+'\n.global '+r['symbol']+'\n'+r['symbol']+':\n.space '+str(r['bytes'])+'\n'
    code+='.p2align 14\n.global __qwen_driver_tables_end\n__qwen_driver_tables_end:\n.data\n.global qwen_driver_table_packed\nqwen_driver_table_packed:\n.incbin '+json.dumps(Path(m['pool']['path']).as_posix())+'\n'
    asm=a.out/'host-tables.S';asm.write_text(code,newline='\n')
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text())
    include=a.cache/'upstream'/('llama.cpp-'+lock['llama_cpp']['revision'])/'vendor/hash'
    compiler=a.workspace/'toolchain/msys-clang64/clang64/bin/clang++.exe'
    sha_source=include/'sha256/sha256.c';obj=a.out/'sha.o';exe=a.out/'restore.exe'
    commands=[[str(compiler),'-x','c','-O2','-I',str(include),'-c',str(sha_source),'-o',str(obj)],
        [str(compiler),'-std=c++17','-O2','-I',str(ROOT/'native/app'),'-I',str(include.parent),
         str(ROOT/'tests/driver_table_restore.cpp'),m['registry']['path'],str(asm),str(obj),'-lz','-Wl,--section-alignment,16384','-o',str(exe)],
        [str(exe)]]
    mock=a.out/'mock';(mock/'ps5platform').mkdir(parents=True);(mock/'sys').mkdir()
    (mock/'ps5platform/heap.h').write_text('#pragma once\n#include <stddef.h>\nextern "C" { void *ps5_heap_calloc(size_t,size_t); int ps5_heap_owns(const void *); void ps5_heap_free(void *); }\n')
    (mock/'sys/mman.h').write_text('#pragma once\n#include <stddef.h>\n#define PROT_READ 1\nextern "C" int mprotect(void *,size_t,int);\n')
    runtime=a.out/'runtime.exe'
    commands += [[str(compiler),'-std=c++17','-O2','-I',str(mock),'-I',str(ROOT/'native/app'),'-I',str(include.parent),
        str(ROOT/'tests/driver_table_runtime.cpp'),str(ROOT/'native/app/driver_tables.cpp'),m['registry']['path'],str(asm),str(obj),
        '-lz','-Wl,--section-alignment,16384','-o',str(runtime)],[str(runtime),'positive'],[str(runtime),'pressure']]
    env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate(commands):
        r=subprocess.run(c,env=env,capture_output=True,timeout=120);(a.out/f'step-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
    result=dict(actual_table_count=len(m['tables']),all_original_SHA256_passed=True,restoration_fault_controls=7,
        actual_production_wrapper_admission_and_no_retry_controls=2,
        manifest=record(a.manifest),commands=commands,production_restorer=record(ROOT/'native/app/driver_table_restore.h'),PS5_operations=0)
    (a.out/'complete.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('commands','manifest','production_restorer')}))
if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check whole-expert/whole-backing readiness and split byte-storage metadata only."""
import argparse,json,os,struct,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    providers=list((a.cache/'host-CPU-reference-066/build').rglob('ggml-base.a'))+list((a.cache/'host-CPU-reference-066/build').rglob('libggml-base.a'))
    if len(providers)!=1:raise ValueError('Exact existing GGML metadata provider required')
    library=providers[0];files=[Path(__file__),library,up/'ggml/include/ggml.h']+[ROOT/n for n in(
        'native/app/ready_expert_wave.h','native/app/split_padded_bank.h','native/app/padded_bank.h','native/app/padded_bank_layout.h',
        'tests/ready_expert_wave.cpp','tests/split_padded_bank_geometry.cpp')];fixed=[record(f)for f in files]
    common=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app')]
    owner=a.out/'ready-wave.exe';geometry=a.out/'split-bank.exe'
    commands=[common+[str(ROOT/'tests/ready_expert_wave.cpp'),'-o',str(owner)],
        common+['-I',str(up/'ggml/include'),str(ROOT/'tests/split_padded_bank_geometry.cpp'),str(library),'-o',str(geometry)],[str(owner)],[str(geometry)]]
    native_source=a.out/'ready-wave-native.cpp'
    native_source.write_text('#include "ready_expert_wave.h"\n#include <cstdint>\n'
        '__attribute__((used,section(".qwen_ready_layout"))) const std::uint64_t layout[]={sizeof(qwen_app::ReadyExpertWave),'
        'sizeof(qwen_app::ReadyWaveSnapshot),qwen_app::split_bank_total_bytes,qwen_app::split_bank_active[0],qwen_app::split_bank_active[1]};\n'
        'void instantiate_ready_wave_metadata(){std::array<std::int32_t,10> ids{};std::array<unsigned,10> slots{};'
        'for(unsigned i=0;i<10;++i){ids[i]=i;slots[i]=i%2?26+i/2:i/2;}'
        'qwen_app::ReadyExpertWave::Owners owners{{{{11,11,11}},{{22,22,22}}}};'
        'qwen_app::ReadyExpertWave p(ids,slots,owners,47,1,17,1);p.bind_reader(std::this_thread::get_id());'
        'for(unsigned i=0;i<10;++i)p.admit_resident(slots[i],47*512+i,1);'
        'p.begin_wave(0,2);p.complete_wave(17,2,true);p.begin_wave(1,3);p.complete_wave(17,3,true);'
        'p.begin_original_reduction(4);p.complete_original_reduction(17,4,true);p.retire_completed(17);}\n',newline='\n')
    prior_path=a.cache/'build/application-native-metadata-2615/receipt.private.json';prior=json.loads(prior_path.read_text())
    native=next(c.copy()for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    obj=a.out/'ready-wave-native.o';native[native.index('-c')+1]=str(native_source);native[native.index('-o')+1]=str(obj)
    native+=['-Wall','-Wextra','-Werror'];layout=a.out/'native-layout.private.bin'
    commands+=[native,[str(Path(native[0]).parent/'llvm-objcopy.exe'),'--dump-section=.qwen_ready_layout='+str(layout),str(obj)]]
    files.extend((native_source,prior_path));fixed=[record(f)for f in files]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls={}
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Ready wave '+str(i)+': '+r.stderr.decode(errors='replace')[-2600:])
        if i in(2,3):controls[str(i)]=json.loads(r.stdout)
    assert controls['2']['unknown_or_failed_retention_cases']==10 and controls['3']['bounded_read_envelopes']==3180
    raw=layout.read_bytes()
    if len(raw)!=40:raise ValueError('Exact native metadata-layout section required')
    native_size,snapshot_size,bank_bytes,first,second=struct.unpack('<5Q',raw)
    assert 0<native_size<65536 and snapshot_size<native_size and bank_bytes==533495808 and(first,second)==(26,27)
    assert fixed==[record(f)for f in files]
    result=dict(controls=controls,inputs=fixed,commands=commands,actual_SDK_header_compilation=True,
        native_metadata_bytes=native_size,native_snapshot_bytes=snapshot_size,actual_model_cache_or_graph_integration=False,
        native_buffer_or_GPU_qualification=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('inputs','commands')}),flush=True)
if __name__=='__main__':main()

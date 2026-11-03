#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual GLSL uint32 index helper against independent uint64 references."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','shaders','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();built=load(a.shaders);decoder=built['carrier_decoder']
    need(built['completed'] and built['large_cache_index_safe'] and built['cache_planes']==3713 and
         built['all_seventeen_resources_recompiled'] and record(decoder['path'])==decoder,
         'The exact complete index-safe shader family is required')
    text=Path(decoder['path']).read_text(encoding='utf-8');start=text.index('uvec2 iq2_down_plane_value(')
    end=text.index('\n}',start)+2;function=text[start:end]
    need('uint64' not in function and 'values_per_index' in function,'The tested GPU helper must use only uint32')
    a.out.mkdir(parents=True,exist_ok=False);header=a.out/'iq2_down_index_under_test.h'
    header.write_text('#include <cstdint>\nusing uint=std::uint32_t;\nstruct uvec2{uint x,y;uvec2(uint a,uint b):x(a),y(b){}};\nconstexpr uint IQ2_DOWN_VALUES=1638400u;\n'+function+'\n',encoding='utf-8')
    source=ROOT/'tests/iq2_down_large_cache_index_test.cpp';exe=a.out/'index-controls.exe'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';commands=[]
    for label,command in [('compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-include','initializer_list',
                                    '-I',a.out,source,'-o',exe]),('run',[exe])]:
        command=list(map(str,command));commands.append(command)
        child=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,
            PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(label+'.private.log')).write_bytes(child.stdout+child.stderr)
        need(child.returncode==0,'The actual unsigned index helper failed its independent boundary control')
    result=json.loads(child.stdout)
    need(result['completed'] and result['planes']==3713 and result['cases']>=20000000 and
         result['old_overflow_negatives']>0,'All cache planes, local exhaustive ranges and old-form negatives must pass')
    save(a.out/'result.private.json',dict(result,shaders=record(a.shaders),decoder=decoder,
        actual_GLSL_helper_extracted=True,actual_helper_SHA256=hashlib.sha256(function.encode()).hexdigest(),
        tested_header=record(header),harness=record(source),commands=commands,
        independent_uint64_reference=True,packed_units=[4,64],all3713_planes_checked=True,
        all_local_indices_exhausted_at_planes=[0,2620,2621,2622,3711,3712],
        Euclidean_quotient_remainder_domain_bounds_checked=True,all_physical_addresses_below_2GiB=True,
        native_quality_or_speed_qualified=False,PS5_operations=0,native_replays=0))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()

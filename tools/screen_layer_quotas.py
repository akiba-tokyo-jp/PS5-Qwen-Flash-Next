#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen causal nonuniform layer floors against completed actual native routes."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def header_source(original,root_weight):
    text='#include <cmath>\n'+original
    text=once(text,'    std::uint64_t tick_=0;','    std::uint64_t tick_=0,quota_tick_=UINT64_MAX;\n    std::vector<double>layer_repeats_;std::vector<std::size_t>quotas_;')
    text=once(text,'        experts_=experts;slots_=slots;cached_layers_=cached_layers;routes_=0;tick_=0;',
        '        experts_=experts;slots_=slots;cached_layers_=cached_layers;routes_=0;tick_=0;quota_tick_=UINT64_MAX;layer_repeats_.assign(layers,1.0);quotas_.assign(layers,0);')
    text=once(text,'            if(counts_.at(key)!=UINT32_MAX)','            if(counts_.at(key))layer_repeats_.at(layer)+=1.0;\n            if(counts_.at(key)!=UINT32_MAX)')
    text=once(text,'if(++routes_==4096){for(auto&count:counts_)count/=2;routes_=0;}',
        'if(++routes_==4096){for(auto&count:counts_)count/=2;for(auto&w:layer_repeats_)w=1.0+(w-1.0)*0.5;routes_=0;}')
    marker='        const auto floor=(slots_-selected.size())/cached_layers_;'
    weight='std::sqrt(layer_repeats_[l])'if root_weight else'layer_repeats_[l]'
    text=once(text,marker,'''
        if(quota_tick_!=tick_){
            const auto available=slots_-selected.size();const auto base=std::min<std::size_t>(6,available/cached_layers_);
            const auto spare=available-base*cached_layers_;double sum=0;
            for(std::size_t l=0;l<cached_layers_;++l)sum+='''+weight+''';
            std::size_t used=0;std::vector<std::pair<double,std::size_t>>fractions;fractions.reserve(cached_layers_);
            for(std::size_t l=0;l<cached_layers_;++l){const double amount=spare*('''+weight+''')/sum;
                quotas_[l]=base+std::size_t(amount);used+=quotas_[l];fractions.emplace_back(-(amount-std::size_t(amount)),l);}
            std::sort(fractions.begin(),fractions.end());
            for(std::size_t k=0;k<available-used;++k)++quotas_[fractions.at(k).second];quota_tick_=tick_;
        }
''')
    return once(text,'else if(residents_[layer]<=floor)continue;','else if(residents_[layer]<=quotas_[layer])continue;')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('case','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    traces=[json.loads((a.case/f'native-arm{i}.routes.private.json').read_text())for i in (1,2)]
    terminal=json.loads((a.case/'native-model-terminal.private.json').read_text());slots=terminal['active_cache_slots']
    require(terminal['completed']and slots==1381 and all(t['complete']for t in traces),'Completed actual1381 routes required')
    text=f'{slots} 2\n'
    for i,t in enumerate(traces):
        text+=f'{int(i==0)} {len(t["records"])}\n'
        for r in t['records']:text+=f'{r["layer"]} {len(r["ids"])} '+' '.join(map(str,r['ids']))+'\n'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));rows=[]
    original=(ROOT/'native/app/expert_temporal_probation.h').read_text()
    for mode in ('control','quota_linear','quota_sqrt'):
        folder=a.out/mode;folder.mkdir();header=folder/'expert_temporal_probation.h'
        header.write_text(original if mode=='control'else header_source(original,mode=='quota_sqrt'),newline='\n')
        exe=folder/'replay.exe';command=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(folder),'-I',str(ROOT/'native/app'),str(ROOT/'tools/replay_completed_routes.cpp'),'-o',str(exe)]
        build=subprocess.run(command,capture_output=True,timeout=120,env=env);require(build.returncode==0,build.stderr.decode()[-1500:])
        run=subprocess.run([str(exe)],input=text.encode(),capture_output=True,timeout=120,env=env);require(run.returncode==0,run.stderr.decode()[-1500:])
        counts=[list(map(int,line.split()))for line in run.stdout.decode().splitlines()]
        if mode=='control':require(all(h==t['cache_hits']and m==t['cache_misses']for(_,h,m),t in zip(counts,traces)),'Actual control counts not reproduced')
        (folder/'completed.private.log').write_bytes(run.stdout)
        rows.append(dict(mode=mode,counts=counts,header=record(header),compiled_source=record(ROOT/'tools/replay_completed_routes.cpp')))
    write_json(a.out/'analysis.private.json',dict(completed=True,causal_past_only=True,actual_control_reproduced=True,routing_frozen=True,native_speedup_established=False,rows=rows,inputs=[record(a.case/f'native-arm{i}.routes.private.json')for i in(1,2)]))
    print(json.dumps(dict(completed=True,native_speedup_established=False,rows=[dict(mode=r['mode'],counts=r['counts'])for r in rows])))
if __name__=='__main__':main()

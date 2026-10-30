#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replay the actual current cache planner and screen new partial placements."""
import argparse,collections,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]

CPP=r'''
#include "expert_temporal_probation.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#define GGML_ASSERT(v) do{if(!(v))throw std::runtime_error("Actual cache planner assertion");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Actual cache planner aborted")
extern "C" bool llama_app_expert_policy_enabled(){return true;}
extern "C" void qwen_app_route_resident(unsigned,unsigned,bool){}
#include "actual-planner.private.h"
using Json=nlohmann::json;
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("Two explicit paths required");
 std::ifstream in(argv[1]);Json traces;in>>traces;Json out=Json::array();
 for(const auto&trace:traces){
  moe_cache_slru planner;planner.init(49,512,867,48);
  std::vector<std::vector<int32_t>>maps(49,std::vector<int32_t>(512,-1));
  for(unsigned i=0;i<48;++i)planner.slot_map[i]=maps[i].data();
  uint64_t hits=0,misses=0,unique=0;Json rows=Json::array();unsigned graph=0;
  for(const auto&row:trace.at("records")){
   const auto layer=row.at("layer").get<unsigned>();const auto tokens=row.at("tokens").get<unsigned>();
   const auto experts=row.at("experts").get<unsigned>();const auto ids=row.at("ids").get<std::vector<int32_t>>();
   if(layer>=48||tokens<1||tokens>16||(experts!=6&&experts!=8&&experts!=10)||ids.size()!=experts*tokens)
      throw std::runtime_error("Native current routing geometry differs");
   if(!layer)++graph;std::vector<moe_cache_slru::fill>fills;size_t h=0;
   if(!planner.plan(int32_t(layer),ids.data(),ids.size(),fills,h))throw std::runtime_error("Native current planner refused");
   Json keys=Json::array();for(auto fill:fills)keys.push_back(fill.expert);
   rows.push_back({{"layer",layer},{"tokens",tokens},{"graph",graph-1},{"fills",keys}});
   hits+=h;misses+=fills.size();unique+=h+fills.size();
  }
  if(hits!=trace.at("cache_hits")||misses!=trace.at("cache_misses")||unique!=trace.at("unique_selected_experts"))
      throw std::runtime_error("Replay does not reproduce current native hits/misses");
  out.push_back({{"hits",hits},{"misses",misses},{"unique",unique},{"rows",rows}});
 }
 std::ofstream file(argv[2]);file<<out.dump()<<'\n';
}catch(const std::exception&e){std::cerr<<e.what();return 1;}}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','workspace','parent','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    parent=json.loads(a.parent.read_text());selected=parent['routing_sharing']['actual_sources']['cache']
    require(record(selected['path'])==selected,'Actual selected cache source changed')
    source=Path(selected['path']).read_text();start=source.index('struct moe_cache_slru {');end=source.index('// gate, up, down or gate_up, down',start)
    (a.out/'actual-planner.private.h').write_text(source[start:end],newline='\n')
    traces=[];inputs=[record(a.parent),selected,record(__file__)]
    for case,ordinal in ((9720,1),(9630,17),(9630,23),(9630,29)):
        root=a.cache/f'hardware-first-generation-{case}';path=root/f'native-arm{ordinal}.routes.private.json'
        trace=json.loads(path.read_text());close=json.loads((root/'restored-complete.private.json').read_text())
        require(trace['complete']and trace['cache_reset_before_request']and trace['cache_slots']==867 and
                close['completed']and not close['unknown_completion'],'Closed current-policy native trace required')
        traces.append(trace);inputs +=[record(path),record(root/'restored-complete.private.json')]
    write_json(a.out/'traces.private.json',traces);cpp=a.out/'replay.private.cpp';cpp.write_text(CPP,newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'replay.exe';raw=a.out/'fills.private.json'
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
              '-I',str(a.out),'-I',str(up/'vendor'),str(cpp),'-o',str(exe)],
              [str(exe),str(a.out/'traces.private.json'),str(raw)]]
    for i,cmd in enumerate(commands):
        run=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    replay=json.loads(raw.read_text());base_path=ROOT/'.local/q2-bundle-selection-9070/selection.private.json'
    extra_path=Path(parent['all_Q2_IO_normal']['extra_pack']['path'])
    base=json.loads(base_path.read_text());extra=json.loads(extra_path.read_text())
    require(record(extra['selection']['path'])==extra['selection'],'Existing extra selection changed')
    extra_selection=json.loads(Path(extra['selection']['path']).read_text())
    extra_rows=extra_selection.get('Experts',extra_selection.get('experts'))
    require(isinstance(extra_rows,list),'Existing extra placement must have explicit Expert keys')
    existing={(int(row['layer']),int(row['expert']))for row in [*base['Experts'],*extra_rows]}
    require(len(existing)==420,'Exact existing placement coverage required')
    inputs +=[record(base_path),record(extra_path),extra['selection']]
    # Fit only the counting decode trace; quality traces remain held out.
    counts=collections.Counter();co=collections.Counter()
    for row in replay[0]['rows']:
        if row['tokens']!=1:continue
        keys=[(row['layer'],e)for e in row['fills']if(row['layer'],e)not in existing]
        counts.update(keys)
        for i,key in enumerate(keys):
            for other in keys[i+1:]:co[tuple(sorted((key,other)))]+=1
    selected_keys=[key for key,_ in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:84]]
    # Greedy within-layer co-demand ordering avoids reading unused gap Experts.
    ordered=[];remaining=set(selected_keys)
    while remaining:
        key=max(remaining,key=lambda k:(counts[k],-k[0],-k[1]));ordered.append(key);remaining.remove(key)
        while remaining:
            same=[k for k in remaining if k[0]==key[0]]
            if not same:break
            nxt=max(same,key=lambda k:(co[tuple(sorted((key,k)))],counts[k],-k[1]))
            if not co[tuple(sorted((key,nxt)))]:break
            ordered.append(nxt);remaining.remove(nxt);key=nxt
    coverage=[]
    for trace,rows in zip(traces,replay):
        chosen=set(ordered);misses=0;covered=0;decode=0;decode_covered=0
        for row in rows['rows']:
            for e in row['fills']:
                misses+=1;hit=(row['layer'],e)in chosen;covered+=hit
                if row['tokens']==1:decode+=1;decode_covered+=hit
        coverage.append(dict(misses=misses,covered_new_misses=covered,decode_misses=decode,
            covered_decode_misses=decode_covered,minimum_role_calls_saved=2*covered,
            additional_bytes_from_per_triplet_padding=4096*covered))
    selection=dict(completed=True,no_Experts_omitted=True,bundles=len(ordered),
                   Experts=[dict(layer=k[0],expert=k[1])for k in ordered],
                   trained_only_on_counting_decode=True,held_out_quality_inputs=3)
    write_json(a.out/'selection.private.json',selection)
    report=dict(completed=True,actual_current_planner_and_native_counters_exact=True,existing_bundles=420,
        candidate_bundles=len(ordered),candidate_file_bytes=((len(ordered)*1540096+65535)//65536)*65536,
        coverage=coverage,eligible_for_native_comparison=bool(ordered)and all(r['covered_new_misses']>0 for r in coverage),
        native_speed_qualified=False,PS5_operations=0,inputs=inputs,commands=commands)
    write_json(a.out/'receipt.private.json',report)
    print(json.dumps({k:v for k,v in report.items()if k not in ('inputs','commands')},indent=2))

if __name__=='__main__':main()

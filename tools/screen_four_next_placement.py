#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce installed cache misses and select at most348 immutable triplets."""
import argparse,collections,json,os,re,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from screen_expanded_miss_placement import keys
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "indexed_probation_policy.h"
#include "decode_prefill_protection.h"
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#define GGML_ASSERT(v) do{if(!(v))throw std::runtime_error("Actual planner assertion");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Actual planner aborted")
static bool decode=false;
extern "C" bool llama_app_expert_policy_enabled(){return true;}
extern "C" bool qwen_app_route_is_decode(){return decode;}
extern "C" void qwen_app_route_resident(unsigned,unsigned,bool){}
qwen_app::DecodePrefillProtection speed_history;
#include "actual-planner.private.h"
using Json=nlohmann::json;
int main(int argc,char**argv)try{
 if(argc!=3)throw std::runtime_error("Input/output required");Json input;std::ifstream(argv[1])>>input;Json result=Json::array();
 moe_cache_slru p;std::array<std::array<int,512>,49>maps{};
 for(const auto&t:input){const bool clear=t["cache_reset_before_request"];
  if(clear){p.init(49,512,3072,48);for(unsigned l=0;l<49;++l){maps[l].fill(-1);p.slot_map[l]=maps[l].data();}}
  if(t["ordinal"]!=2||clear)speed_history.begin(true,clear);
  uint64_t hits=0,misses=0;Json rows=Json::array();unsigned record_index=0;
  for(const auto&r:t["records"]){unsigned l=r["layer"],tokens=r["tokens"];auto ids=r["ids"].get<std::vector<int>>();decode=tokens<=2;
   std::vector<moe_cache_slru::fill>fills;std::size_t hit=0;
   if(!p.plan(l,ids.data(),ids.size(),fills,hit))throw std::runtime_error("Planner refused");
   Json es=Json::array();for(auto f:fills)es.push_back(f.expert);
   rows.push_back({{"layer",l},{"tokens",tokens},{"fills",es}});hits+=hit;misses+=fills.size();
   if(l==47&&decode&&record_index+1<t["records"].size())speed_history.commit();++record_index;
  }
  if(hits!=t["cache_hits"]||misses!=t["cache_misses"])throw std::runtime_error("Installed native counters differ: "+std::to_string(hits)+"/"+std::to_string(misses));
  result.push_back({{"hits",hits},{"misses",misses},{"rows",rows}});
 }
 std::ofstream(argv[2])<<result.dump()<<'\n';return 0;
}catch(const std::exception&e){std::cerr<<e.what();return 1;}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','cache','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);r=json.loads(a.parent.read_text());src=Path(r['routing_sharing']['actual_sources']['cache']['path']);text=src.read_text();start=text.index('struct moe_cache_slru {');end=text.index('// gate, up, down or gate_up, down',start)
 (a.out/'actual-planner.private.h').write_text(text[start:end],newline='\n')
 traces=[];inputs=[record(a.parent),record(src),record(__file__)]
 for case,ordinals in [(17000,[0,1,2]),(16800,[10,11,12,13])]:
  for ordinal in ordinals:
   path=a.cache/f'hardware-first-generation-{case}/native-arm{ordinal}.routes.private.json';t=json.loads(path.read_text());require(t['complete']and not t['capture_failed']and t['cache_slots']==3072,'Completed installed-geometry routes required');traces.append(t);inputs.append(record(path))
 write_json(a.out/'traces.private.json',traces);cpp=a.out/'replay.private.cpp';cpp.write_text(CPP,newline='\n');exe=a.out/'replay.exe';host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
 commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(a.out),'-I'+str(ROOT/'native/app'),'-I'+str(up/'vendor'),str(cpp),'-o',str(exe)],[str(exe),str(a.out/'traces.private.json'),str(a.out/'fills.private.json')]]
 for i,cmd in enumerate(commands):
  v=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'{i}.private.log').write_bytes(v.stdout+v.stderr);require(v.returncode==0,v.stderr.decode(errors='replace')[-2200:])
 rows=json.loads((a.out/'fills.private.json').read_text());base=json.loads((ROOT/'.local/q2-bundle-selection-9070/selection.private.json').read_text())['Experts'];extra=json.loads(Path(json.loads(Path(r['all_Q2_IO_normal']['extra_pack']['path']).read_text())['selection']['path']).read_text());extra=extra.get('Experts',extra.get('experts'))
 owner=Path(r['all_Q2_optimized_monitor']['commands'][1][r['all_Q2_optimized_monitor']['commands'][1].index('-c')+1]);current=owner.parent/'limit-winner-bundle.private.h';old=keys(current,'Q2_current');existing={(int(x['layer']),int(x['expert']))for x in base+extra}|set(old)
 require(len(existing)==676 and len(old)==256,'Exact installed676 keys and256 supplemental required')
 counts=collections.Counter((v['layer'],int(e))for v in rows[1]['rows']for e in v['fills']if(v['layer'],int(e))not in existing)
 selected=old+[k for k,_ in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:92]];require(len(selected)==348 and len(set(selected))==348,'Bounded348 superset required')
 new=set(selected)-set(old);coverage=[sum((v['layer'],int(e))in new for v in row['rows']for e in v['fills'])for row in rows]
 write_json(a.out/'selection.private.json',dict(completed=True,no_Experts_omitted=True,bundles=348,Experts=[dict(layer=l,expert=e)for l,e in selected],old_keys_retained=256,new_keys=92))
 write_json(a.out/'complete.private.json',dict(completed=True,installed_native_hits_and_misses_exact=True,cache_slots=3072,total_existing_keys=676,new_keys=92,new_total_keys=768,new_pack_bytes=((348*1540096+65535)//65536)*65536,fit_trace=1,held_out_traces=[0,2,3,4,5,6],covered_misses=coverage,maximum_role_request_reduction=[2*x for x in coverage],extra_alignment_bytes_per_covered_miss=4096,host_trace_screen_not_native_speed=True,inputs=inputs,commands=commands,PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(native_cache_reproduced=True,new_keys=92,covered_misses=coverage)))
if __name__=='__main__':main()

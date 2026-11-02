#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen all-hit layer runs only if replay reproduces every real native counter."""
import argparse
import collections
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "indexed_probation_policy.h"
#include "decode_prefill_protection.h"
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#define GGML_ASSERT(v) do{if(!(v))throw std::runtime_error("Planner assertion");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Planner aborted")
extern "C" bool llama_app_expert_policy_enabled(){return true;}
static bool decode=false;
qwen_app::DecodePrefillProtection speed_history;
#include "planner.h"
using Json=nlohmann::json;
int main(int argc,char**argv)try{
 if(argc!=3)throw std::runtime_error("One exact input/output required");Json input;std::ifstream(argv[1])>>input;Json result=Json::array();
 moe_cache_slru p;std::array<std::array<int,512>,49>maps{};
 for(const auto&t:input){const bool clear=t["cache_reset_before_request"];
  if(clear){p=moe_cache_slru{};p.init(49,512,3712,48);for(unsigned l=0;l<49;++l){maps[l].fill(-1);p.slot_map[l]=maps[l].data();}}
  if(t["ordinal"]!=2||clear)speed_history.begin(true,clear);
  std::uint64_t hits=0,misses=0;Json rows=Json::array();unsigned record_index=0;
  for(const auto&r:t["records"]){unsigned layer=r["layer"],tokens=r["tokens"];auto ids=r["ids"].get<std::vector<int>>();decode=tokens<=2;
   std::vector<moe_cache_slru::fill>fills;std::size_t hit=0;if(!p.plan(layer,ids.data(),ids.size(),fills,hit))throw std::runtime_error("Planner refused");
   rows.push_back({{"layer",layer},{"tokens",tokens},{"hits",hit},{"misses",fills.size()},{"all_selected_cached",fills.empty()}});hits+=hit;misses+=fills.size();
   if(layer==47&&decode&&record_index+1<t["records"].size())speed_history.commit();++record_index;
  }
  if(hits!=t["cache_hits"]||misses!=t["cache_misses"])throw std::runtime_error("Native hit/miss mismatch: "+std::to_string(hits)+"/"+std::to_string(misses)+" expected "+std::to_string(t["cache_hits"].get<unsigned>())+"/"+std::to_string(t["cache_misses"].get<unsigned>()));
  result.push_back({{"ordinal",t["ordinal"]},{"hits",hits},{"misses",misses},{"rows",rows}});
 }
 std::ofstream(argv[2])<<result.dump()<<'\n';return 0;
}catch(const std::exception&e){std::cerr<<e.what();return 1;}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','case','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);up=a.cache/('upstream/llama.cpp-'+REVISION)
    source=up/'src/llama-moe-cache.cpp';text=source.read_text(encoding='utf-8')
    text=text[text.index('struct moe_cache_slru {'):text.index('// gate, up, down or gate_up, down')]
    text=once(text,'    qwen_app::ExpertPolicy policy;','    qwen_app::IndexedProbationPolicy policy;')
    text=once(text,'policy.victim(key_of, il, uniq)','policy.victim_avoiding(key_of, il, uniq, speed_history.keys(decode))')
    text=once(text,'        if (adaptive) policy.observe(il, uniq);','        if (adaptive) policy.observe(il, uniq);\n        speed_history.observe(il,uniq,decode);')
    text=once(text,'            key_of[s] = il*n_expert + e;','            if(adaptive)policy.replaced(s,key_of[s],il*n_expert+e);\n            key_of[s] = il*n_expert + e;')
    header=a.out/'planner.h';header.write_text(text,encoding='utf-8',newline='\n')
    terminal=load(a.case/'passive-observer/native.private.bin');need(terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0,'Complete independent current model record required')
    traces=[];inputs=[record(source),record(a.case/'passive-observer/native.private.bin'),record(__file__),record(header)]
    for ordinal in range(3):
        path=a.case/('native-arm'+str(ordinal)+'.routes.private.bin');trace=load(path)
        need(trace['complete'] and not trace['capture_failed'] and trace['cache_slots']==3712 and trace['ordinal']==ordinal and
            trace['pid']==terminal['pid'] and trace['run_id']==terminal['run_id'] and trace['process_calls']==terminal['requests'][ordinal]['completed_performance']['delta']['process_calls'],
            'All three exact completed3712-slot routes required')
        traces.append(trace);inputs.append(record(path))
    data=a.out/'traces.private.json';save(data,traces);cpp=a.out/'replay.cpp';cpp.write_text(CPP,encoding='utf-8',newline='\n');exe=a.out/'replay.exe';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    for name in ('indexed_probation_policy.h','decode_prefill_protection.h','expert_temporal_probation.h','expert_policy.h'):
        inputs.append(record(ROOT/'native/app'/name))
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),str(cpp),'-o',str(exe)],
        [str(exe),str(data),str(a.out/'replayed.private.json')]]
    for i,command in enumerate(commands):
        run=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr);need(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    summary=[]
    for request in load(a.out/'replayed.private.json'):
        rows=request['rows'];processes=[rows[i:i+48] for i in range(0,len(rows),48)]
        need(all(len(group)==48 and [row['layer'] for row in group]==list(range(48)) and len({row['tokens'] for row in group})==1 for group in processes),'Complete ordered original48-layer processes required')
        runs=[];prefixes=[];full=0;layers=0;hits=0
        for group in processes:
            if group[0]['tokens']>2:continue
            prefix=0;run=0;missed=False
            for row in group:
                layers+=1;hits+=row['all_selected_cached']
                if row['all_selected_cached']:
                    run+=1
                    if not missed:prefix+=1
                else:
                    missed=True
                    if run:runs.append(run);run=0
            if run:runs.append(run)
            prefixes.append(prefix);full+=prefix==48
        summary.append(dict(ordinal=request['ordinal'],decode_processes=len(prefixes),decode_layers=layers,all_selected_cached_layers=hits,
            full48_layer_all_hit_processes=full,initial_all_hit_prefix_lengths=prefixes,all_hit_run_histogram=dict(sorted(collections.Counter(runs).items()))))
    need(all(record(row['path'])==row for row in inputs),'A screened source or route changed')
    save(a.out/'result.private.json',dict(completed=True,actual_three_request_native_cache_counters_reproduced=True,requests=summary,
        inputs=inputs,commands=commands,source_scope='Pinned base planner plus explicit indexed policy/protection updates; aggregate native counters required exact',
        whole_selected_provider_object_byte_reconstruction_claimed=False,actual_GPU_all_hit_continuation_implemented=False,
        original_CPU_cache_planning_cannot_be_removed_from_this_screen=True,predicated_state_and_miss_resume_still_require_native_qualification=True,
        hit_coverage_is_not_speed=True,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,native_counters_exact=True,requests=summary,PS5_operations=0)))


if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare identical dedicated slot-map storage with and without unchanged uploads."""
import argparse,json
from pathlib import Path
from build_throughput_current import command
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from scoped_native_variant import link,seal
from expert_q4 import record,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args()
 from native_slot_map_qualification import REASON
 p.error(REASON)
 n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 cc=command(n,next(x for x in n['link_command']if Path(x).name=='cache.o'));cache=Path(cc[cc.index('-c')+1]).read_text();cache='''#include "resident_slot_maps.h"
extern "C" void qwen_slot_maps_select(bool v){qwen_app::reuse_slot_maps=v;}
extern "C" void qwen_slot_maps_stats(std::uint64_t*out){std::copy(qwen_app::slot_map_counts.begin(),qwen_app::slot_map_counts.end(),out);}
'''+cache
 cache=once(cache,'    std::vector<int32_t> ids;','    std::unique_ptr<qwen_app::ResidentSlotMaps> resident_slot_maps;\n    std::vector<int32_t> ids;')
 cache=once(cache,'        if(resident_reuse_enabled){','''        if(groups.size()==1&&groups[0].id>=0&&std::strncmp(ggml_backend_name(devices[groups[0].id].backend),"Vulkan",6)==0)
            resident_slot_maps=std::make_unique<qwen_app::ResidentSlotMaps>(devices[groups[0].id].backend,layers.size(),groups[0].n_slots);
        if(resident_reuse_enabled){''')
 cache=once(cache,'        ggml_backend_tensor_set_async(backend, dst, src->data, 0, ggml_nbytes(src));','        if(resident_slot_maps&&resident_slot_maps->publish(backend,unsigned(il),src,dst))return true;\n        ggml_backend_tensor_set_async(backend, dst, src->data, 0, ggml_nbytes(src));')
 ec=n['compile_commands'][0];entry='''#include <array>
#include <cstdint>
extern "C" void qwen_slot_maps_select(bool);
extern "C" void qwen_slot_maps_stats(std::uint64_t*);
static std::array<std::uint64_t,8>slot_map_snapshot(){std::array<std::uint64_t,8>v{};qwen_slot_maps_stats(v.data());return v;}
'''+Path(ec[ec.index('-c')+1]).read_text()
 entry=once(entry,'qwen_throughput::mode=arm?5:0;','qwen_throughput::mode=5;qwen_slot_maps_select(arm);')
 entry=once(entry,'            const auto cpu_before=qwen_load::snapshot();','            const auto map_before=slot_map_snapshot();\n            const auto cpu_before=qwen_load::snapshot();')
 entry=once(entry,'            row["phase"]=phase;','            const auto map_after=slot_map_snapshot();Json map_delta=Json::array();for(unsigned j=0;j<8;++j)map_delta.push_back(map_after[j]-map_before[j]);row["resident_slot_map_delta"]=map_delta;row["resident_slot_map_reuse_enabled"]=bool(arm);\n            row["phase"]=phase;')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,control_throughput_mode=5,candidate_throughput_mode=5,resident_slot_map_comparison=True,both_arms_dedicated_slot_maps=True,original_ID_download_and_cache_planning_preserved=True,candidate_omits_only_byte_identical_map_uploads=True,original_normal_external_qualification_required=True)
 entry=once(entry,literal(old),literal(scope))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry),cache=(cc+['-I',str(ROOT/'native/app')],cache)),[Path(__file__),ROOT/'native/app/resident_slot_maps.h'])
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison']['scope']=scope;r['resident_slot_maps']=dict(scope=scope,actual_sources=sources,commands=jobs,shared_driver_unchanged=True,weight_precision_and_cache_capacity_unchanged=True,slot_map_layers=49,slot_map_logical_bytes=49*640*4)
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,host_source_and_link_checks_only=True,native_qualification_claimed=False,original_ID_download_cache_selection_and_positive_completion_preserved=True,weights_and_cache_slots_unchanged=True,both_arms_dedicated_storage=True,source_map_range_checked_before_dispatch=True,PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(completed=True,dedicated_slot_map_bytes=49*640*4)))
if __name__=='__main__':main()

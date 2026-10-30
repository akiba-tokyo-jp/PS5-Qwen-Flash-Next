#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Adopt the physically measured 28 supplemental Expert triplets in the normal app."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_placement_prefix_screen import owner_source
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','comparison','analysis','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());comp=json.loads(a.comparison.read_text());analysis=json.loads(a.analysis.read_text())
 require(analysis['completed']and analysis['placement']['eligible_for_normal_integration']and analysis['placement']['all_counting_F32_exact'],'A closed measured exact placement winner is required')
 a.out.mkdir(parents=True,exist_ok=False)
 header=Path(comp['artifact']['path']).parent/'current_bundle.private.h';(a.out/header.name).write_bytes(header.read_bytes())
 oldscope=prior['all_Q2_optimized_monitor']['scope'];scope=dict(oldscope,schema='ps5-qwen-normal-performance-placement-v1',supplemental_bundles=28,total_bundled_Experts=448)
 literal=lambda v:json.dumps(json.dumps(v,separators=(',',':')))
 cmd=prior['compile_commands'][0];text=Path(cmd[cmd.index('-c')+1]).read_text()
 text='#include <cstdint>\nextern "C" void qwen_app_select_current_bundle(bool);\nextern "C" std::uint64_t qwen_app_current_bundle_hits();\n'+text
 text=once(text,literal(oldscope),literal(scope))
 require(text.count('qwen_app_select_Q2_normal_IO(5);')==1,'One current normal I/O selection required')
 text=text.replace('qwen_app_select_Q2_normal_IO(5);','qwen_app_select_Q2_normal_IO(5);qwen_app_select_current_bundle(true);')
 text=once(text,'            const auto graph_reuses_before=', '            const auto current_hits_before=qwen_app_current_bundle_hits();\n            const auto graph_reuses_before=')
 text=once(text,'            row["actual_graph_reuses"]=', '            row["current_bundle_hits"]=qwen_app_current_bundle_hits()-current_hits_before;\n            row["actual_graph_reuses"]=')
 owner_cmd=prior['all_Q2_optimized_monitor']['commands'][1]
 result,commands,sources=link(a.parent,a.out,{'entry':(cmd,text),'owner':(owner_cmd,owner_source(Path(owner_cmd[owner_cmd.index('-c')+1]).read_text()))},
  [Path(__file__),a.comparison,a.analysis,a.out/header.name])
 result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry']);result['all_Q2_optimized_monitor']['commands'][0]=commands['entry']
 result['routing_sharing']['scope']=scope;result['routing_winners_normal'].update(scope=scope,actual_entry=sources['entry'])
 result['normal_performance'].update(scope=scope,actual_entry=sources['entry'],current_placement=dict(complete_triplets=28,measured_comparison=record(a.analysis),
  immutable_header=record(a.out/header.name),actual_owner=sources['owner'],normal_validation_pending=True))
 result['normal_performance']['actual_sources']['entry']=sources['entry'];result['normal_performance']['actual_sources']['owner']=sources['owner']
 result['normal_performance']['commands']['entry']=commands['entry'];result['normal_performance']['commands']['owner']=commands['owner']
 seal(result,a.workspace,a.cache,a.out);print('Measured 28-triplet placement integrated into the selected normal composition.')

if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the audited synchronization provider with prior measured winners."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_throughput_owner import entry_scope
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','feature','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--role',choices=['model_graph','lifecycle','gpu'],required=True);p.add_argument('--bit',type=int,required=True);p.add_argument('--base-throughput-mode',type=int,required=True);a=p.parse_args()
 require((a.role,a.bit)in(('model_graph',2),('lifecycle',4),('gpu',8))and not(a.base_throughput_mode&a.bit),'One new ordered feature required')
 n=json.loads(a.parent.read_text());f=json.loads(a.feature.read_text());a.out.mkdir(parents=True,exist_ok=False)
 ec,entry,old=entry_scope(n,a.bit,a.base_throughput_mode);scope=dict(f['throughput']['scope'],control_frontier_mode=7,candidate_frontier_mode=7,control_throughput_mode=a.base_throughput_mode,candidate_throughput_mode=a.base_throughput_mode|a.bit,earlier_measured_winners_in_both_arms=True)
 entry=once(entry,literal(old),literal(scope))
 if a.bit==2:
  entry=entry.replace('if(compare&&(io_max_error!=0||bitwise_error))','if(compare&&arm==0&&(io_max_error!=0||bitwise_error))').replace('if(compare&&!same_routes)','if(compare&&arm==0&&!same_routes)')
 if a.bit==8:
  require(scope.get('pending_writes_published_before_every_compute_batch_end')is True,'Cross-submission visibility proof required')
  entry='#include <cstdint>\nextern "C" std::uint64_t qwen_throughput_sync_tail_flushes();\n'+entry
  marker='            row["service_mode"]=qwen_service::mode.load();';entry=once(entry,marker,'            row["throughput_sync_tail_flushes"]=qwen_throughput_sync_tail_flushes();\n'+marker)
 oldcmd=n['frontier']['commands'][a.role];newcmd=f['throughput']['commands'][a.role];oldobj=oldcmd[oldcmd.index('-o')+1];newobj=newcmd[newcmd.index('-o')+1]
 require(n['link_command'].count(oldobj)==1 and f['link_command'].count(newobj)==1,'Actual single current and feature provider required')
 seed=copy.deepcopy(n);seed['link_command'][seed['link_command'].index(oldobj)]=newobj;seed['inputs_before']+=active_link_inputs(f)
 seed['frontier']['commands'][a.role]=newcmd;seed['frontier']['actual_sources'][a.role]=f['throughput']['actual_sources'][a.role]
 if a.role=='gpu':
  for k in('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):seed[k]=copy.deepcopy(f[k])
  seed['io_gpu_comparison'].update(GPU_command=newcmd,GPU_source=f['throughput']['actual_sources']['gpu'])
 seedpath=a.out/'selected-provider-seed.private.json';write_json(seedpath,seed)
 r,jobs,sources=link(seedpath,a.out,dict(entry=(ec,entry)),[Path(__file__),ROOT/'tools/build_throughput_owner.py',ROOT/'native/app/throughput_options.h',a.parent,a.feature]);update_sources(r,jobs,sources)
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier']['scope']=scope;r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs)
 selected=copy.deepcopy(n.get('throughput',{}).get('selected_providers',{}));selected[a.role]=dict(command=newcmd,source=f['throughput']['actual_sources'][a.role],object=record(newobj),feature=record(a.feature))
 if 'owner'in n.get('throughput',{}).get('commands',{}):
  cmd=n['throughput']['commands']['owner'];selected['owner']=dict(command=cmd,source=n['throughput']['actual_sources']['owner'],object=record(cmd[cmd.index('-o')+1]),feature=record(a.parent))
 for provider in selected:
  command=seed['frontier']['commands'][provider];selected[provider].update(command=command,source=record(command[command.index('-c')+1]),object=record(command[command.index('-o')+1]))
 r['throughput']=dict(scope=scope,actual_sources=dict(sources,**{a.role:f['throughput']['actual_sources'][a.role]}),commands=dict(jobs,**{a.role:newcmd}),selected_providers=selected,parent_comparison=record(a.parent),compiled_feature=record(a.feature))
 if a.role=='gpu':
  unsealed=a.out/'unsealed.private.json';write_json(unsealed,r);run=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600);(a.out/'GPU-provenance.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:]);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text())
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,already_compiled_feature_object_reused=True,earlier_measured_winners_in_both_arms=True,original_weights_and_positive_completion_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

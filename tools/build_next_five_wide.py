#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare width2/4 with three native recurrent rollback slots in both arms."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import command_for,update_sources,ROOT
from build_cache_capacity_1125 import recipes,literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
CAP=5216120832+(248<<20)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 ec=n['compile_commands'][0];en=n['routing_sharing']['commands'][2];rc=command_for(n,'routing.private.cpp');gc=command_for(n,'graph.private.cpp')
 commands={r['object_path']:r['command']for r in n['CPU_metadata_scope']['changed_sources']if r['object_path']in n['link_command']}
 for cmd in(ec,en,rc,gc):commands[cmd[cmd.index('-o')+1]]=cmd
 budget=a.cache/'build/Four-next-rollback-17600/device_buffer_budget.h';(a.out/budget.name).write_text(budget.read_text().replace('5216120832ull',str(CAP)+'ull'),newline='\n')
 api=ROOT/'native/app/llama_engine.h';api_text=api.read_text();api_text=once(api_text,'    Token next_with_one_draft(llama_token draft);','    Token next_with_one_draft(llama_token draft);\n    Token next_with_three_drafts(const std::array<llama_token,3>&);\n    unsigned wide_bonus_remaining()const{return unsigned(wide_logits_.size()-wide_cursor_);}')
 api_text=once(api_text,'    void guard() const {','    std::vector<std::vector<float>> wide_logits_;\n    std::size_t wide_cursor_=0;\n    void guard() const {');(a.out/api.name).write_text(api_text,newline='\n')
 mappings={}
 for name in (budget.name,api.name):
  targets={ROOT/'native/app'/name,ROOT.with_name(ROOT.name+'-refill')/'native/app'/name}
  for cmd in commands.values():
   dirs=[Path(cmd[cmd.index('-c')+1]).parent]+[Path(cmd[i+1])for i,x in enumerate(cmd[:-1])if x=='-I'];targets.update(d/name for d in dirs if(d/name).is_file())
  for row in n['inputs_before']:
   if Path(row['path']).name==name:targets.add(Path(row['path']))
  for t in targets:mappings[t]=a.out/name
 overlay=a.out/'wide-ABI-budget.private.json';write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},roots=[dict(type='file',name=k.resolve().as_posix(),**{'external-contents':v.resolve().as_posix()})for k,v in sorted(mappings.items())]))
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='width-four-history',candidate_id=6,n_rs_seq=3,postload_budget_bytes=CAP,additional_recurrent_allowance_bytes=248<<20,
  source_proposals='causal_recursive_single_latest_history',control_width=2,candidate_width=4,all_or_nothing_three_draft_acceptance=True,partial_rejections_rewind_all_three_uncommitted_tokens=True,Attention_KV_bits=32)
 entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "next_five_wide_causal.h"\n'+entry;entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?1:0);','qwen_next_select(arm?6:0);');entry=entry.replace('qwen_app::NextFiveCausalEngine','qwen_app::WideHistoryEngine')
 entry=once(entry,'qwen_app::model_postload_device_budget==5216120832ull','qwen_app::model_postload_device_budget=='+str(CAP)+'ull');entry=once(entry,'arm==0?"installed-control":"routing4";','arm==0?"width2-nrs3":"width4-nrs3";')
 entry=once(entry,'{"causal_proposals",causal.causal_proposals}','{"causal_proposals",causal.causal_proposals},{"width_four_proposals",causal.wide_proposals}')
 engine=Path(en[en.index('-c')+1]).read_text();engine=once(engine,'params.n_rs_seq=1;','params.n_rs_seq=3;');engine=once(engine,'llama_n_rs_seq(context_)!=1','llama_n_rs_seq(context_)!=3')
 engine=once(engine,'Token LlamaEngine::next() {','Token LlamaEngine::next() {\n    if(wide_bonus_remaining()){restored_logits_=std::move(wide_logits_[wide_cursor_++]);restored_logits_active_=true;pending_=LLAMA_TOKEN_NULL;++speculative_stats_.queued_bonus_samples;if(wide_cursor_==wide_logits_.size()){wide_logits_.clear();wide_cursor_=0;}return next_once();}')
 engine+='\n#include "next_five_wide_engine.inc"\n'
 routing=Path(rc[rc.index('-c')+1]).read_text();routing=once(routing,'(elements!=512&&elements!=1024)','(elements<512||elements>2048||elements%512)')
 graph=Path(gc[gc.index('-c')+1]).read_text();require(graph.count('n_tokens<=2')==2,'Exactly two routed decode width guards required');graph=graph.replace('n_tokens<=2','n_tokens<=4')
 special={ec[ec.index('-o')+1]:('entry',entry),en[en.index('-o')+1]:('engine',engine),rc[rc.index('-o')+1]:('routing',routing),gc[gc.index('-o')+1]:('graph',graph)};variants={};originals={}
 for i,(obj,cmd)in enumerate(commands.items()):
  path=Path(cmd[cmd.index('-c')+1]);label,text=special.get(obj,('budget'+str(i),path.read_text()));variants[label]=(cmd+['-ivfsoverlay',str(overlay),'-I',str(ROOT/'native/app')],text);originals[label]=record(path)
 r,jobs,sources=link(a.parent,a.out,variants,[Path(__file__),overlay,a.out/api.name,a.out/budget.name,ROOT/'native/app/next_five_wide_causal.h',ROOT/'native/app/next_five_wide_engine.inc'])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['CPU_metadata_scope']['changed_sources']=[dict(original=originals[k],source=sources[k],object_path=jobs[k][jobs[k].index('-o')+1],command=jobs[k])for k in jobs if k not in('entry','engine','routing','graph')]
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='width4_three_snapshot_native_rollback',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

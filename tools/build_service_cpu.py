#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare one cumulative service-overhead factor with unchanged qualified GPU math."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--control-mode',type=int,required=True);p.add_argument('--candidate-mode',type=int,required=True);p.add_argument('--stage',choices=('1','2','3'),required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='service-stage-'+a.stage,control_service_mode=a.control_mode,candidate_service_mode=a.candidate_mode,serialized_tail_disabled_in_both_arms=True,per_token_fsync_preserved=True,all_before_operation_records_preserved=True)
 entry='#include "durable_token_ledger.h"\n'+entry;entry=once(entry,literal(old),literal(scope))
 entry=once(entry,'qwen_load_tail_select(arm==1);qwen_post_submit_select(arm==1);','qwen_load_tail_select(true);qwen_post_submit_select(true);if(qwen_service::pending_stage[0])throw std::runtime_error("Unflushed stage pair at request boundary");qwen_service::mode=arm?'+str(a.candidate_mode)+':'+str(a.control_mode)+';')
 entry=once(entry,'            const auto &result=trial.run(request,','            qwen_service::TokenLedger token_ledger;qwen_load::CpuSpan measured_run(qwen_load::request_run);\n            const auto &result=trial.run(request,')
 entry=once(entry,'            },[&](const auto &token,const auto &m){','            },[&](const auto &token,const auto &m){qwen_load::CpuSpan measured(qwen_load::token_persistence);')
 start=entry.index('                write_fresh_report(report_prefix+".token-"');end=entry.index('\n                if(ordinal){',start);original=entry[start:end];body=original[original.index(',{{')+1:];require(body.endswith(');'),'Exact token persistence expression required');value=body[:-2]
 entry=entry[:start]+'                if(qwen_service::ledger())token_ledger.append(report_prefix+".token-ledger",Json('+value+'));\n                else '+original.strip()+entry[end:]
 marker='            qwen_checkpoint_trial_stats(checkpoint_after);';entry=once(entry,marker,'            {qwen_load::CpuSpan measured(qwen_load::token_persistence);token_ledger.close();}measured_run.end();if(qwen_service::pending_stage[0])throw std::runtime_error("Unflushed request stage pair");\n'+marker)
 marker='            row["phase"]=phase;';entry=once(entry,marker,'            row["service_mode"]=qwen_service::mode;row["token_ledger_records"]=token_ledger.records();row["token_ledger_bytes"]=token_ledger.bytes();row["stage_pair_totals"]={qwen_service::stage_pairs,qwen_service::stage_writes,qwen_service::stage_syncs};\n'+marker)
 variants=dict(entry=(ec+['-I',str(ROOT/'native/app')],entry));deps=[Path(__file__),ROOT/'native/app/service_options.h',ROOT/'native/app/durable_token_ledger.h']
 if a.stage=='2':
  cmds={c[c.index('-o')+1]:c for c in recipes(n)if'-c'in c and'-o'in c and c[c.index('-o')+1]in n['link_command']};found=[c for c in cmds.values()if'extern "C" void qwen_native_bootstrap() {'in Path(c[c.index('-c')+1]).read_text()];require(len(found)==1,'One actual linked bootstrap required');bc=found[0];boot='#include "service_options.h"\n'+Path(bc[bc.index('-c')+1]).read_text()
  marker='    if (write(journal,line,bytes+1)!=static_cast<ssize_t>(bytes+1))stop_bootstrap("bootstrap_stage_persist_failed");'
  code='''    const char*data=line;std::size_t count=bytes+1;char combined[1120];
    if(qwen_service::pair_stages()&&!recording){
        if(!std::strcmp(stage,"inference_decode_synchronization_completed")){if(qwen_service::pending_stage[0])stop_bootstrap("stage_pair_pending_collision");std::memcpy(qwen_service::pending_stage,line,count);qwen_service::pending_stage[count]=0;return;}
        if(qwen_service::pending_stage[0]){const auto prior=std::strlen(qwen_service::pending_stage);if(prior+count>sizeof(combined))stop_bootstrap("stage_pair_bounds");std::memcpy(combined,qwen_service::pending_stage,prior);std::memcpy(combined+prior,line,count);data=combined;count+=prior;qwen_service::pending_stage[0]=0;++qwen_service::stage_pairs;}
    }
    ++qwen_service::stage_writes;
    if(write(journal,data,count)!=static_cast<ssize_t>(count))stop_bootstrap("bootstrap_stage_persist_failed");'''
  boot=once(boot,marker,code);boot=once(boot,'    if(fsync(journal))stop_bootstrap("bootstrap_stage_persist_failed");','    ++qwen_service::stage_syncs;if(fsync(journal))stop_bootstrap("bootstrap_stage_persist_failed");');variants['bootstrap']=(bc+['-I',str(ROOT/'native/app')],boot)
 r,jobs,sources=link(a.parent,a.out,variants,deps);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['service_cpu']=dict(scope=scope,stage=a.stage,actual_sources=sources,commands=jobs,production_adopted=False);seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,per_token_sync_preserved=True,all_before_operation_records_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

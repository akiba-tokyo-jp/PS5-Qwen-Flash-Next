#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare an unchanged, already durable owner boundary against mode-69 control."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def transform(source):
 source='#include "frontier_options.h"\n#include "owner_checkpoint_certificate.h"\nnamespace {qwen_frontier::OwnerCheckpointCertificate frontier_owner;}\nextern "C" void qwen_frontier_owner_stats(std::uint64_t*out){for(unsigned i=0;i<4;++i)out[i]=qwen_frontier::owner_stats[i];}\n'+source
 source=once(source,'void DriverLifecycle::initialize(const char * journal) {','void DriverLifecycle::initialize(const char * journal) {\n    if(frontier_owner.frontend==this)frontier_owner={};')
 source=once(source,'submitted != submits_.load() || !ops_.checkpoint())','submitted != submits_.load())')
 marker='        if(device&&submitted&&kick.completed_epoch){service_idle='
 start=source.index(marker)
 code='''        ps5_ai_native_arena_journal_stats journal_before{};
        ps5_ai_native_arena_journal_snapshot(&journal_before);
        bool checkpoint_reused=false;
        if((qwen_frontier::mode.load(std::memory_order_relaxed)&1) &&
           frontier_owner.matches(this,device,submitted,kick.completed_epoch,owner,journal_before)) {
            // Snapshots take the original journal/owner mutexes. A repeated stable
            // allocation generation and journal generation prevent an ABA or a
            // writer crossing this proof window. Queue calls stay excluded.
            ps5_ai_native_arena_journal_stats journal_after{};
            ps5_ai_native_arena_journal_snapshot(&journal_after);
            ps5_ai_arena_stats owner_after{};ops_.snapshot(&owner_after);
            checkpoint_reused=qwen_frontier::same_journal(journal_before,journal_after) &&
                qwen_frontier::same_owner(owner,owner_after) && submitted==submits_.load();
        }
        ++qwen_frontier::owner_stats[0];
        if(checkpoint_reused)++qwen_frontier::owner_stats[1];
        else {
            ++qwen_frontier::owner_stats[2];
            if(!ops_.checkpoint())reject("Native completed-owner journal is uncertain");
        }
        ps5_ai_native_arena_journal_stats durable{};
        ps5_ai_native_arena_journal_snapshot(&durable);
        if(device&&submitted&&kick.completed_epoch && durable.log_healthy==1 &&
           durable.abi_bytes==sizeof(durable)&&durable.records&&durable.fsync_calls) {
            frontier_owner={this,device,submitted,kick.completed_epoch,owner,durable};
            ++qwen_frontier::owner_stats[3];
        } else frontier_owner={};
'''
 return source[:start]+code+source[start:]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='frontier-1-durable-owner-generation',control_service_mode=69,candidate_service_mode=69,control_frontier_mode=0,candidate_frontier_mode=1,all_fresh_owner_and_retirement_checks_preserved=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "frontier_options.h"\nextern "C" void qwen_frontier_owner_stats(std::uint64_t*);\n'+entry
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_service::mode=arm?69:5;','qwen_service::mode=69;qwen_frontier::mode=arm?1:0;')
 entry=once(entry,'if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))');entry=once(entry,'if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')
 marker='            row["service_mode"]=qwen_service::mode.load();'
 entry=once(entry,marker,'            std::uint64_t frontier[4]{};qwen_frontier_owner_stats(frontier);row["frontier_owner_totals"]=std::vector<std::uint64_t>(frontier,frontier+4);row["frontier_mode"]=qwen_frontier::mode.load();\n'+marker)
 lc=n['service_completion']['commands']['lifecycle'];require(lc[lc.index('-o')+1]in n['link_command'],'Actual qualified lifecycle provider required')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),lifecycle=(lc,transform(Path(lc[lc.index('-c')+1]).read_text()))),[Path(__file__),ROOT/'native/app/frontier_options.h',ROOT/'native/app/owner_checkpoint_certificate.h'])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier']=dict(scope=scope,actual_sources=sources,commands=jobs);r['service_completion']['actual_sources']['lifecycle']=sources['lifecycle'];r['service_completion']['commands']['lifecycle']=jobs['lifecycle']
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,positive_completion_and_all_owner_checks_preserved=True,unchanged_allocation_and_journal_generation_required=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

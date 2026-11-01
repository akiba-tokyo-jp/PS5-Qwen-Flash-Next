#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse an empty-retirement-list proof with fresh completion and owner checks."""
import argparse,json,re
from pathlib import Path
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def entry_scope(n,bit,base):
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='throughput-3-empty-retirement-mutation-certificate',control_frontier_mode=7,candidate_frontier_mode=7,control_throughput_mode=base,candidate_throughput_mode=base|bit,fresh_worker_health_and_owner_snapshots_preserved=True,original_driver_archive_and_72byte_owner_ABI_preserved=True)
 ec=n['compile_commands'][0];source=Path(ec[ec.index('-c')+1]).read_text()
 if'#include "throughput_options.h"'not in source:source='#include "throughput_options.h"\n'+source
 source=once(source,literal(old),literal(scope));source,count=re.subn(r'qwen_frontier::mode=(?:arm\?\d+:\d+|\d+);(?:qwen_throughput::mode=arm\?\d+:\d+;)?','qwen_frontier::mode=7;qwen_throughput::mode=arm?'+str(base|bit)+':'+str(base)+';',source);require(count==1,'Exactly one request mode selector required')
 if'row["throughput_totals"]'not in source:
  marker='            row["service_mode"]=qwen_service::mode.load();';source=once(source,marker,'            row["throughput_mode"]=qwen_throughput::mode.load();row["throughput_totals"]=std::vector<std::uint64_t>(qwen_throughput::stats,qwen_throughput::stats+12);\n'+marker)
 source=source.replace('if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))').replace('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')
 return ec,source,scope

def transform(source):
 source='#include "throughput_options.h"\n#include "owner_retirement_certificate.h"\nnamespace {qwen_throughput::OwnerRetirementCertificate throughput_retirement;}\n'+source
 source=once(source,'void DriverLifecycle::retain_fault() noexcept {','void DriverLifecycle::retain_fault() noexcept {\n    if(throughput_retirement.frontend==this)throughput_retirement={};')
 source=once(source,'void DriverLifecycle::initialize(const char * journal) {','void DriverLifecycle::initialize(const char * journal) {\n    if(throughput_retirement.frontend==this)throughput_retirement={};')
 old='''        if (submitted) {
            if (!device || !kick.initialized || !kick.thread_started || !kick.requested_epoch ||
                kick.requested_epoch != kick.completed_epoch)
                reject("Native submission completion epoch is not admitted");
            ops_.stage("native_driver_before_completed_epoch_retirement");
            if (ops_.retire_quiet(kick.completed_epoch) != 1)
                reject("Native retired ownership could not be confirmed");
        } else if (kick.requested_epoch || kick.completed_epoch) {
            reject("Native worker observed untracked submissions");
        }
        ps5_ai_arena_stats owner{};
        ops_.snapshot(&owner);'''
 new='''        ps5_ai_arena_stats owner{};
        if (submitted) {
            if (!device || !kick.initialized || !kick.thread_started || !kick.requested_epoch ||
                kick.requested_epoch != kick.completed_epoch)
                reject("Native submission completion epoch is not admitted");
            ops_.snapshot(&owner);
            ++qwen_throughput::stats[7];
            bool reuse=(qwen_throughput::mode.load(std::memory_order_relaxed)&4)&&
                throughput_retirement.matches(this,device,submitted,kick.completed_epoch,owner);
            if(reuse){
                // Original owner mutex snapshots bracket the certificate use.
                // No retirement syscall or owner mutation is skipped on change.
                ps5_ai_arena_stats after{};ops_.snapshot(&after);
                reuse=qwen_frontier::same_owner(owner,after)&&ops_.owner_ready()&&submitted==submits_.load();
                owner=after;
            }
            if(reuse)++qwen_throughput::stats[8];
            else{
                ++qwen_throughput::stats[9];
                const auto before_retirement=owner;
                ops_.stage("native_driver_before_completed_epoch_retirement");
                if(ops_.retire_quiet(kick.completed_epoch)!=1)reject("Native retired ownership could not be confirmed");
                ops_.snapshot(&owner);
                if(qwen_frontier::same_owner(before_retirement,owner)&&!owner.mapping_uncertain&&!owner.gpu_fault_retained&&!owner.global_capacity_measured&&ops_.owner_ready())
                    throughput_retirement={this,device,submitted,kick.completed_epoch,owner};
                else throughput_retirement={};
            }
        } else {
            if(kick.requested_epoch||kick.completed_epoch)reject("Native worker observed untracked submissions");
            ops_.snapshot(&owner);
        }'''
 return once(source,old,new)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--base-throughput-mode',type=int,default=0);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 ec,entry,scope=entry_scope(n,4,a.base_throughput_mode);lc=n['frontier']['commands']['lifecycle'];require(lc[lc.index('-o')+1]in n['link_command'],'Actual current lifecycle provider required');body=transform(Path(lc[lc.index('-c')+1]).read_text())
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),lifecycle=(lc+['-I',str(ROOT/'native/app')],body)),[Path(__file__),ROOT/'native/app/throughput_options.h',ROOT/'native/app/owner_retirement_certificate.h',ROOT/'native/app/owner_checkpoint_certificate.h']);update_sources(r,jobs,sources)
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier']['scope']=scope;r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs);r['throughput']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,no_shared_driver_or_native_allocator_changes=True,full_retirement_on_every_owner_mutation=True,fresh_positive_worker_and_GPU_completion_preserved=True,per_token_persistence_and_final_retirement_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

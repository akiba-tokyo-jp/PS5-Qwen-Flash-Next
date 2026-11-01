#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse only a positive same-device/submission/worker-epoch idle certificate."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
PREFIX='''#include "service_options.h"
namespace {struct ServiceIdleCertificate {const void*owner=nullptr;std::uintptr_t device=0;std::uint64_t submitted=0,epoch=0;}service_idle;std::uint64_t service_idle_stats[3]{};}
extern "C" void qwen_service_completion_stats(std::uint64_t*out){for(unsigned i=0;i<3;++i)out[i]=service_idle_stats[i];}
'''
def transform(source):
 source=PREFIX+source
 source=once(source,'void DriverLifecycle::initialize(const char * journal) {','void DriverLifecycle::initialize(const char * journal) {\n    if(service_idle.owner==this)service_idle={};')
 start=source.index('        if (device) {',source.index('void DriverLifecycle::finish_boundary'));end=source.index('\n        if (submitted != submits_.load())',start)
 original=source[start:end];require('ops_.device_wait_idle(device)'in original,'Positive original device idle required')
 code='''        if(device){
            ps5_ai_arena_kick_stats observed{};
            const bool reuse=(qwen_service::mode.load(std::memory_order_relaxed)&4)&&service_idle.owner==this&&service_idle.device==device&&service_idle.submitted==submitted&&service_idle.epoch&&
                !ops_.kick_snapshot(&observed)&&!observed.pending&&!observed.active&&!observed.submit_inflight&&!observed.fault_retained&&observed.log_healthy&&observed.initialized&&observed.thread_started&&
                observed.requested_epoch==service_idle.epoch&&observed.completed_epoch==service_idle.epoch&&ops_.owner_ready();
            if(reuse){++service_idle_stats[1];ops_.stage("native_driver_positive_device_idle_same_generation_reused");}
            else{++service_idle_stats[0];ops_.stage("native_driver_before_positive_device_idle");if(ops_.device_wait_idle(device))reject("Native device idle did not positively complete");ops_.stage("native_driver_device_idle_completed");}
        }'''
 source=source[:start]+code+source[end:]
 marker='        ops_.stage(end_producer ? "native_driver_producer_completed_resources_owned" : "native_driver_checkpoint_completed_producer_retained");'
 source=once(source,marker,'        if(device&&submitted&&kick.completed_epoch){service_idle={this,device,submitted,kick.completed_epoch};++service_idle_stats[2];}\n'+marker)
 return source
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--control-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='service-stage-3',control_service_mode=a.control_mode,candidate_service_mode=a.control_mode|4,positive_device_submission_and_worker_epoch_required=True,queue_lock_and_all_owner_checks_preserved=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_service_completion_stats(std::uint64_t*);\n'+entry;entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_service::mode=arm?'+str(old['candidate_service_mode'])+':'+str(old['control_service_mode'])+';','qwen_service::mode=arm?'+str(a.control_mode|4)+':'+str(a.control_mode)+';');entry=once(entry,'            row["service_mode"]=qwen_service::mode.load();','            std::uint64_t completed_scope[3]{};qwen_service_completion_stats(completed_scope);row["service_completion_totals"]=std::vector<std::uint64_t>(completed_scope,completed_scope+3);\n            row["service_mode"]=qwen_service::mode.load();')
 qualified=a.cache/'build/application-native-prefix-2595/receipt.private.json';base=json.loads(qualified.read_text());commands=[c for c in base['compile_commands']if'-c'in c and Path(c[c.index('-c')+1]).name=='driver_lifecycle.cpp'];require(len(commands)==1,'One qualified frontend compiler recipe required');lc=commands[0].copy();source=ROOT/'native/app/driver_lifecycle.cpp';expected=[r for r in base['application_sources']if Path(r['path']).name==source.name];require(len(expected)==1 and record(source)['sha256']==expected[0]['sha256'],'Exact preceding frontend source required');objects=[x for x in n['link_command']if Path(x).name.startswith('driver_lifecycle-')];require(len(objects)==1,'One actual frontend provider required');lc[lc.index('-c')+1]=str(source);lc[lc.index('-o')+1]=objects[0]
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),lifecycle=(lc,transform(source.read_text()))),[Path(__file__),source,qualified,ROOT/'native/app/service_options.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['service_completion']=dict(scope=scope,actual_sources=sources,commands=jobs);seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,queue_lock_and_owner_validation_preserved=True,positive_generation_certificate_required=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

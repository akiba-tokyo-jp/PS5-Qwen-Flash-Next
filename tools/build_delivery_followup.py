#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink independent bundle, queue, depth and fresh-metadata candidates."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal,recipes
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from audit_expert_all_q2_safety import body
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['cold_request']['scope']['mode']=='prefill32_indexed_streaming','Exact installed composition required');a.out.mkdir(parents=True,exist_ok=False)
    commands=dict(entry=prior['compile_commands'][0],owner=prior['all_Q2_optimized_monitor']['commands'][1],cache=prior['routing_sharing']['commands'][1])
    memory=[c for c in recipes(prior)if '-c'in c and '-o'in c and c[c.index('-c')+1].endswith('system_memory.cpp')and c[c.index('-o')+1]in prior['link_command']]
    require(len(memory)==1,'One actual selected memory provider required');commands['memory']=memory[0].copy();commands['memory'][1:1]=['-I',str(ROOT/'native/app')]
    source={k:Path(c[c.index('-c')+1]).read_text()for k,c in commands.items()}
    header=Path(prior['cold_request']['source_header']['path']);reader=header.read_text()
    # Wide metadata belongs to the one existing reader, not the producer stack.
    original='    bool upload_Q2_stream'+reader.split('    bool upload_Q2_stream',1)[1].split('    bool borrowed_window_contains',1)[0]
    require(original.startswith('    bool upload_Q2_stream'),'Exact streamed reader required')
    wide_method=original.replace('bool upload_Q2_stream','unsigned upload_delivery_wide').replace(',12>',',960>').replace('count>12','count>960')
    wide_method=wide_method.replace('std::array<SourceReadRequest,960>requests{};std::array<std::size_t,960>files{},skips{};',
        'auto&requests=delivery_requests_;auto&files=delivery_files_;auto&skips=delivery_skips_;')
    wide_method=wide_method.replace('completed();return true;','completed();return count/3;')
    # A failed wide eligibility screen leaves the original12-request path intact.
    marker='    bool borrowed_window_contains('
    reader=once(reader,marker,(ROOT/'native/app/delivery_bundle_source.inc').read_text()+'\n'+wide_method+'\n'+marker)
    reader=once(reader,'    mutable std::atomic<std::size_t> range_hint_',
        '    std::array<SourceReadRequest,960>delivery_requests_{};std::array<std::size_t,960>delivery_files_{},delivery_skips_{};\n    mutable std::atomic<std::size_t> range_hint_')
    (a.out/header.name).write_text(reader,newline='\n');(a.out/'device_buffer_budget.h').write_bytes(Path(prior['cold_request']['tightened_workspace_header']['path']).read_bytes())
    owner=source['owner'].replace('#include <streaming_read_pool.h>','#include <delivery_read_pool.h>').replace('qwen_app::StreamingReadPool','qwen_app::DeliveryReadPool')
    owner=once(owner,'    void stream(const std::array<qwen_app::SourceReadRequest,12>&requests', '    template<std::size_t N>void stream(const std::array<qwen_app::SourceReadRequest,N>&requests')
    owner=once(owner,'std::array<qwen_app::BoundedReadRequest,12>jobs{};','std::array<qwen_app::BoundedReadRequest,N>jobs{};')
    owner=once(owner,'    void cold_timing(', '    void delivery_depth(unsigned depth){require_metadata_idle();if(!quad_)throw std::runtime_error("Missing delivery pool");quad_->select_depth(depth);}\n    void cold_timing(')
    owner+='''
extern "C" void qwen_app_numeric_memory_select(bool);
namespace {unsigned delivery_mode=0;std::uint64_t delivery_bundle_groups=0,delivery_bundle_reads=0,delivery_wide_groups=0,delivery_wide_reads=0;}
extern "C" unsigned qwen_app_delivery_mode(){return delivery_mode;}
extern "C" void qwen_app_delivery_select(unsigned mode){
    required().require_completed_window();ops.require_metadata_idle();if(mode>5)throw std::runtime_error("Unknown finite delivery candidate");
    ops.delivery_depth(mode==3?2:(mode==4?3:4));qwen_app_numeric_memory_select(mode==5);delivery_mode=mode;
}
extern "C" void qwen_app_delivery_stats(std::uint64_t*out){out[0]=delivery_bundle_groups;out[1]=delivery_bundle_reads;out[2]=delivery_wide_groups;out[3]=delivery_wide_reads;}
extern "C" bool qwen_app_delivery_bundles(unsigned layer,const unsigned*experts,unsigned count,void*opaque,void(*consume)(void*,unsigned,unsigned,const void*,std::size_t)){
    required().require_completed_window();ops.require_metadata_idle();if(delivery_mode!=1)return false;
    if(!experts||!opaque||!consume||count<2||count>4||layer>=48)throw std::runtime_error("Bounded admitted bundle demands required");
    std::array<qwen_app::SourceReadRequest,4>requests{};std::array<qwen_app::SourceIdentity,4>identities{};std::array<int,4>indices{};
    for(unsigned i=0;i<count;++i){const int index=qwen_app_Q2_bundle_index(layer,experts[i]);if(index<0)return false;indices[i]=index;
        const bool current=index>=1024,extra=index>=512&&!current;
        if((current&&!Q2_current_verified)||(extra&&!Q2_extra_verified)||(!current&&!extra&&!Q2_bundle_verified))throw std::runtime_error("Unsealed delivery bundle");
        requests[i]={current?Q2_current_fd:(extra?Q2_extra_fd:Q2_bundle_fd),nullptr,1540096,std::uint64_t(index%512)*1540096};identities[i]=current?Q2_current_identity:(extra?Q2_extra_identity:Q2_bundle_identity);
    }
    const bool used=required().upload_delivery_bundles(requests,identities,count,[&](const auto&r,unsigned n,const auto&leases,const auto&before,const auto&use){ops.stream(r,n,leases,before,use);},[&](unsigned i,unsigned role,const void*p,std::size_t bytes){consume(opaque,i,role,p,bytes);});
    if(used){++delivery_bundle_groups;delivery_bundle_reads+=count;for(unsigned i=0;i<count;++i){++Q2_bundle_hits;if(indices[i]>=1024)++Q2_current_hits;else if(indices[i]>=512)++Q2_extra_hits;}}return used;
}
extern "C" unsigned qwen_app_delivery_wide(const void*const*addresses,const std::size_t*sizes,unsigned count,void*opaque,void(*consume)(void*,unsigned,const void*)){
    required().require_completed_window();ops.require_metadata_idle();if(delivery_mode!=2)return 0;
    if(!addresses||!sizes||!opaque||!consume||!count||count>960||count%3)throw std::runtime_error("Wide exact Expert demands required");
    std::array<std::uintptr_t,960>at{};std::array<std::size_t,960>bytes{};for(unsigned i=0;i<count;++i){at[i]=reinterpret_cast<std::uintptr_t>(addresses[i]);bytes[i]=sizes[i];}
    const auto used=required().upload_delivery_wide(at,bytes,count,[&](const auto&r,unsigned n,const auto&leases,const auto&before,const auto&use){ops.stream(r,n,leases,before,use);},[&](unsigned i,const void*p){consume(opaque,i,p);});
    if(used){++delivery_wide_groups;delivery_wide_reads+=used*3;}return used;
}
'''
    cache=source['cache'];cache='''#include <cstddef>
extern "C" unsigned qwen_app_delivery_mode();
extern "C" bool qwen_app_delivery_bundles(unsigned,const unsigned*,unsigned,void*,void(*)(void*,unsigned,unsigned,const void*,std::size_t));
extern "C" unsigned qwen_app_delivery_wide(const void*const*,const std::size_t*,unsigned,void*,void(*)(void*,unsigned,const void*));
'''+cache
    # Preserve consecutive larger bundle groups. Only isolated bundle demands
    # enter the additional four-lane path, so request-count savings remain.
    marker='            for(size_t cursor=0;cursor<chosen;){'
    cache=once(cache,marker,marker+'''
                if(qwen_app_delivery_mode()==1){
                    struct BundleJobs{Upload*upload;std::array<int,4>slots{};}jobs{&upload,{}};std::array<unsigned,4>singles{};unsigned number=0;
                    for(size_t at=cursor;at<chosen&&number<4;++at){const auto i=selected[at];const auto index=qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[i].expert));
                        if((at&&qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[selected[at-1]].expert))==index-1)||(at+1<chosen&&qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[selected[at+1]].expert))==index+1))break;
                        singles[number]=unsigned(fills[i].expert);jobs.slots[number++]=fills[i].slot;
                    }
                    if(number>=2&&qwen_app_delivery_bundles(unsigned(il),singles.data(),number,&jobs,[](void*opaque,unsigned item,unsigned role,const void*p,std::size_t size){
                        if(item>=4||role>=3)throw std::runtime_error("Bundle queue index is unowned");auto&j=*static_cast<BundleJobs*>(opaque);const int slot=j.slots[item];
                        if(slot<0||slot>=int(output_Q8_selected_slots))throw std::runtime_error("Bundle queue slot is unowned");auto*bank=j.upload->banks[role];const auto offset=std::size_t(slot)*bank->nb[2]+j.upload->residues[role];
                        if(offset>ggml_nbytes(bank)||size>ggml_nbytes(bank)-offset)throw std::runtime_error("Bundle queue scatter exceeds bank");ggml_backend_tensor_set(bank,p,offset,size);
                    })){for(unsigned j=0;j<number;++j){delivered[selected[cursor+j]]=true;bytes+=1536000;}cursor+=number;continue;}
                }
''')
    marker='            for(unsigned first=0;first<remaining;first+=4){'
    # One bounded wide attempt per layer, falling back without I/O if its
    # complete extents fail the original scheduling eligibility predicate.
    wide_cache=(ROOT/'native/app/streaming_q2_cache.inc').read_text()
    section=wide_cache[wide_cache.index('                struct StreamUpload'):wide_cache.index('\n            }\n        }')]
    section=section.replace(',12>',',960>').replace('addresses[12]','addresses[960]').replace('sizes[12]','sizes[960]').replace('if(id>=12)','if(id>=960)')
    section=section.replace('if(qwen_app_try_Q2_stream(addresses,sizes,count,&job,','if(qwen_app_delivery_wide(addresses,sizes,count,&job,')
    section=section.replace('delivered[available[first+e]]=true','delivered[available[first+e]]=true')
    cache=once(cache,marker,'''            if(qwen_app_delivery_mode()==2&&remaining>4){
                const unsigned first=0,experts=remaining,count=experts*3;
'''+section+'''
            }
            // Remove positively delivered demands before the original path.
            if(qwen_app_delivery_mode()==2){unsigned kept=0;for(unsigned i=0;i<remaining;++i)if(!delivered[available[i]])available[kept++]=available[i];remaining=kept;}
'''+marker)
    memory_source=source['memory'];memory_source='#include "numeric_memory_counter.h"\n#include <atomic>\n#include <cstring>\nnamespace {std::atomic<bool>numeric_memory_selected{false};std::array<qwen_app::NumericMemoryCounter,6>numeric_memory_names;}\nextern "C" void qwen_app_numeric_memory_select(bool enabled){numeric_memory_selected.store(enabled);}\n'+memory_source
    marker='std::uint32_t scalar(const char * name) {'
    memory_source=once(memory_source,marker,marker+'''
    if(numeric_memory_selected.load()){
        const char*names[]={"vm.stats.vm0.v_free_count","hw.pagesize","vm.stats.vm0.v_page_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_target","vm.stats.vm0.v_free_reserved"};
        unsigned index=0;while(index<6&&std::strcmp(names[index],name))++index;if(index==6)throw std::runtime_error("Unexpected numeric memory counter");
        return numeric_memory_names[index].value(name,[](const char*n,int*m,std::size_t*s){return sysctlnametomib(n,m,s);},[](const int*m,unsigned n,void*v,std::size_t*b){return sysctl(m,n,v,b,nullptr,0);});
    }
''')
    scope=dict(prior['cold_request']['scope'],mode='delivery_followup',candidate_modes=[0,1,2,3,4,5],numeric_names_only=True,maximum_source_lanes=4,maximum_known_role_reads=960,source_scratch_bytes=8<<20)
    entry='#include <cstdint>\nextern "C" unsigned qwen_app_delivery_mode();\nextern "C" void qwen_app_delivery_stats(std::uint64_t*);\n'+source['entry']
    entry=once(entry,literal(prior['cold_request']['scope']),literal(scope))
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t delivery_before[4]{};qwen_app_delivery_stats(delivery_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["cold_request_timing"]=', '            std::uint64_t delivery_after[4]{};qwen_app_delivery_stats(delivery_after);Json delivery_delta=Json::array();for(unsigned i=0;i<4;++i)delivery_delta.push_back(delivery_after[i]-delivery_before[i]);row["delivery_followup"]={{"mode",qwen_app_delivery_mode()},{"delta",delivery_delta},{"physical_and_kernel_guards_unchanged",true}};\n            row["cold_request_timing"]=')
    result,jobs,actual=link(a.parent,a.out,dict(entry=(commands['entry'],entry),owner=(commands['owner'],owner),cache=(commands['cache'],cache),memory=(commands['memory'],memory_source)),
        [Path(__file__),header,ROOT/'native/app/delivery_read_pool.h',ROOT/'native/app/delivery_bundle_source.inc',ROOT/'native/app/numeric_memory_counter.h',a.out/header.name,a.out/'device_buffer_budget.h'])
    for key in ('normal_performance','output_Q8_normal'):result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor']['actual_entry']=actual['entry'];result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=actual['entry']
    checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(entry,name)==body(source['entry'],name),'Original application guard changed: '+name);checks.append(name)
    result['cold_request'].update(scope=scope,actual_sources=actual,commands=jobs,source_header=record(a.out/header.name),tightened_workspace_header=record(a.out/'device_buffer_budget.h'),normal_validation_pending=True,production_adopted=False)
    result['delivery_followup']=dict(scope=scope,actual_sources=actual,commands=jobs,original_driver_and_reserves=True,original_memory_provider=record(Path(commands['memory'][commands['memory'].index('-c')+1])),modes={'0':'installed_control','1':'parallel_individual_bundles','2':'wide_known_demand_queue','3':'two_read_lanes','4':'three_read_lanes','5':'fresh_numeric_memory_counters'},normal_validation_pending=True)
    seal(result,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='delivery_followup_guard_audit',unchanged_application_guards=checks,original_memory_observation_order_and_predicates_preserved=True,source_identity_and_positive_completion_preserved=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print('Delivery follow-up candidates linked with unchanged GPU providers and fresh memory values.')


if __name__=='__main__':main()

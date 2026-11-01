#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare complete, immutable triplet coverage using the existing four read lanes."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','bundles','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());b=json.loads(a.bundles.read_text())
 require(b['completed']and b['active_Experts']==24576 and len(b['parts'])==71 and b['per_part']==348 and b['CPU_Direct_positively_retired']and b['original_sources_preserved']and b['quantized_bits_unchanged'],'Complete positively retired native pack required')
 require(sum(x['bytes']for x in b['parts'])==37849399296,'All active Expert bytes required');a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='throughput-1-all-Expert-immutable-triplet-coverage',control_frontier_mode=7,candidate_frontier_mode=7,control_throughput_mode=0,candidate_throughput_mode=1,bundle_coverage=24576,bundle_parts=71,bundle_read_lanes=4,original_weight_payloads_and_bytes_preserved=True,extra_weight_allocations=0)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "throughput_options.h"\n'+entry;entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_frontier::mode=arm?11:3;','qwen_frontier::mode=7;qwen_throughput::mode=arm?1:0;')
 marker='            row["service_mode"]=qwen_service::mode.load();';entry=once(entry,marker,'            row["throughput_mode"]=qwen_throughput::mode.load();row["throughput_totals"]=std::vector<std::uint64_t>(qwen_throughput::stats,qwen_throughput::stats+12);\n'+marker)
 # This is a byte/layout-only candidate; cross-arm full F32 and routes must remain exact.
 entry=once(entry,'if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))');entry=once(entry,'if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')
 oc=n['all_Q2_optimized_monitor']['commands'][1];require(oc[oc.index('-o')+1]in n['link_command'],'Current source owner required')
 dirs=[Path(oc[i+1])for i,v in enumerate(oc[:-1])if v=='-I'];oldreader=next(d/'speed-resident-source.private.h'for d in dirs if(d/'speed-resident-source.private.h').exists());reader=a.out/'throughput-reader.private.h';reader.write_text(once(oldreader.read_text(),'    void upload_Q2_bundle(int fd,','    #include "delivery_bundle_source.inc"\n    void upload_Q2_bundle(int fd,'),newline='\n')
 text='#pragma once\nstruct ThroughputBundlePart{const char*path;qwen_app::SourceIdentity identity;};\nstatic const ThroughputBundlePart throughput_parts[]={\n'
 for x in b['parts']:
  require(x['path'].startswith('/data/ai/native-moss-image-sft/PPSA99190/qwen-full-bundles-')and x['identity'][2:5]==[0o100444,0,0]and x['identity'][5]==x['bytes']and x['bytes']<=512<<20,'Exact read-only bounded pack identity required')
  text+='{'+json.dumps('/app0'+x['path'].split('/PPSA99190',1)[1])+',{'+','.join(str(v)+'ULL'for v in x['identity'])+'}},\n'
 header=a.out/'throughput-bundle-plan.private.h';header.write_text(text+'};\n',newline='\n')
 owner=Path(oc[oc.index('-c')+1]).read_text();owner='#include "throughput_options.h"\n'+owner;owner=once(owner,'#include "speed-resident-source.private.h"','#include '+json.dumps(str(reader).replace('\\','/')))
 marker='NativeReads ops;';addition=r'''
#include "throughput-bundle-plan.private.h"
std::array<int,71>throughput_fds=[](){std::array<int,71>r{};r.fill(-1);return r;}();
std::array<qwen_app::SourceIdentity,71>throughput_identities{};
bool throughput_bundle_selected(){return (qwen_throughput::mode.load(std::memory_order_relaxed)&1)!=0;}
void admit_throughput_bundles(void*scratch){
    for(unsigned i=0;i<71;++i){const auto&p=throughput_parts[i];auto&fd=throughput_fds[i];
        if(fd>=0||!scratch)throw std::runtime_error("New full bundle owner required");
        fd=ops.open_direct(p.path);if(fd<0||!(fcntl(fd,F_GETFL)&O_DIRECT))throw std::runtime_error("Read-only Direct full bundle required");
        const auto id=ops.identity(fd);for(unsigned j=1;j<10;++j)if(id[j]!=p.identity[j])throw std::runtime_error("Native-sealed full bundle identity differs");
        if(!id[0]||!id[1]||id[2]!=0100444||id[5]>(512ull<<20)||id[5]%65536)throw std::runtime_error("Full bundle seal geometry differs");
        const int named=ops.open_direct(p.path);if(named<0)throw std::runtime_error("Full bundle named identity unavailable");
        const bool same=ops.identity(named)==id;const bool closed=ops.close_file(named);
        if(!same||!closed||ops.read_at(fd,scratch,16384,id[5])!=0||ops.identity(fd)!=id)throw std::runtime_error("Full native seal handoff or EOF differs");
        throughput_identities[i]=id;
    }
}
unsigned upload_throughput_bundles(unsigned layer,const unsigned*experts,unsigned count,void*opaque,
        void(*consume)(void*,unsigned,unsigned,const void*,std::size_t)){
    required().require_completed_window();ops.require_metadata_idle();
    if(layer>=48||!experts||!count||count>5||!opaque||!consume)throw std::runtime_error("Full bundle demand escapes ownership");
    std::array<qwen_app::SourceReadRequest,4>requests{};std::array<qwen_app::SourceIdentity,4>identities{};
    const unsigned n=std::min(count,4u);
    for(unsigned i=0;i<n;++i){if(experts[i]>=512)throw std::runtime_error("Unknown full bundle Expert");const unsigned ordinal=layer*512+experts[i],part=ordinal/348;
        if(part>=71||throughput_fds[part]<0)throw std::runtime_error("Unadmitted full bundle part");
        requests[i]={throughput_fds[part],nullptr,1540096,std::uint64_t(ordinal%348)*1540096};identities[i]=throughput_identities[part];
    }
    const bool used=required().upload_delivery_bundles(requests,identities,n,[&](const auto&r,unsigned number,const auto&leases,const auto&before,const auto&use){
        std::array<qwen_app::SourceReadRequest,12>expanded{};std::copy(r.begin(),r.end(),expanded.begin());ops.stream(expanded,number,leases,before,use);
    },[&](unsigned item,unsigned role,const void*data,std::size_t bytes){consume(opaque,item,role,data,bytes);});
    if(!used)throw std::runtime_error("Full triplet delivery was not positively admitted");
    qwen_throughput::stats[0]+=n;++qwen_throughput::stats[1];qwen_throughput::stats[2]+=n;return n;
}
'''
 # required() is declared below the global source state; define upload after that declaration.
 admission,upload=addition.split('unsigned upload_throughput_bundles(',1);owner=once(owner,marker,marker+admission)
 point='extern "C" int qwen_app_Q2_bundle_index(unsigned layer,unsigned expert){';owner=once(owner,point,'unsigned upload_throughput_bundles('+upload+'\n'+point)
 owner=once(owner,'    admit_Q2_bundle(window);admit_Q2_extra(window);admit_Q2_current(window);','    admit_Q2_bundle(window);admit_Q2_extra(window);admit_Q2_current(window);admit_throughput_bundles(window);')
 owner=once(owner,'    device_budget.close_completed();\n    required().close_completed();','    device_budget.close_completed();\n    required().close_completed();\n    for(auto&fd:throughput_fds){if(fd<0||!ops.close_file(fd))throw std::runtime_error("Full bundle owner did not positively close");fd=-1;}')
 owner=once(owner,point,point+'\n    if(throughput_bundle_selected()){if(layer>=48||expert>=512)throw std::runtime_error("Full bundle index out of bounds");return 4096+int(layer*512+expert);}')
 marker='    const auto first=qwen_app_Q2_bundle_index(layer,experts[0]);';owner=once(owner,marker,'    if(throughput_bundle_selected()){const auto used=upload_throughput_bundles(layer,experts,count,opaque,consume);Q2_bundle_hits+=used;return used;}\n'+marker)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),owner=(oc+['-I',str(ROOT/'native/app')],owner)),[Path(__file__),ROOT/'native/app/throughput_options.h',ROOT/'native/app/delivery_bundle_source.inc',a.bundles,Path(b['raw']['path']),oldreader,reader,header]);update_sources(r,jobs,sources)
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier']['scope']=scope;r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs)
 r['throughput']=dict(scope=scope,actual_sources=sources,commands=jobs,bundles=record(a.bundles),reader=record(reader),plan=record(header));seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,original_weight_bits_and_fallback_preserved=True,native_full_SHA256_readback_and_readonly_identity_handoff=True,four_original_2MiB_read_leases=True,positive_completion_and_owner_validation_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()

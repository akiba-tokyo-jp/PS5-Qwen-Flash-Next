# SPDX-License-Identifier: MIT
"""Bounded physical adjacency merging without changed weights or GPU kernels."""
from build_speculative_batch_probe import once

def header_source(text):
    start=text.index('    void upload_Q2_bundle(')
    end=text.index('    bool borrowed_window_contains',start)
    method=text[start:end]
    method=once(method,'void upload_Q2_bundle(','void upload_Q2_bundle_group(')
    method=once(method,'std::uint64_t offset,','std::uint64_t offset,unsigned count,')
    method=once(method,'void(unsigned,const void*,std::size_t)','void(unsigned,unsigned,const void*,std::size_t)')
    method=once(method,'if(fd<0||!consume','if(count<1||count>5||fd<0||!consume')
    method=once(method,'stride>identity[5]-offset','count*stride>identity[5]-offset')
    method=once(method,'scratch_,stride,offset','scratch_,count*stride,offset')
    method=once(method,'std::int64_t(stride)','std::int64_t(count*stride)')
    method=once(method,'physical_read_bytes+=stride','physical_read_bytes+=count*stride')
    method=once(method,'stats_.bytes+=payload','stats_.bytes+=count*payload')
    method=once(method,'stats_.maximum_chunk,stride','stats_.maximum_chunk,count*stride')
    method=once(method,'consume(0,p,537600);consume(1,p+537600,537600);consume(2,p+1075200,460800);',
        'for(unsigned i=0;i<count;++i){const auto*q=p+i*stride;consume(i,0,q,537600);consume(i,1,q+537600,537600);consume(i,2,q+1075200,460800);}')
    return text[:end]+method+text[end:]

def owner_source(text):
    text='#include <source_io_occupancy.h>\nnamespace {qwen_app::SourceIOOccupancy source_occupancy;}\n'+text
    text=once(text,'        const auto begun=qwen_app::ProfileClock::now();','        source_occupancy.begin();\n        const auto begun=qwen_app::ProfileClock::now();')
    text=once(text,'        source_latency.completed(got,ns);return got;','        source_occupancy.end();source_latency.completed(got,ns);return got;')
    text=once(text,'int Q2_bundle_fd=-1;','bool Q2_adjacent_merge=false;std::uint64_t Q2_merged_calls_saved=0;\nint Q2_bundle_fd=-1;')
    return text+'''
extern "C" void qwen_app_select_Q2_adjacent(bool enabled){required().require_completed_window();ops.require_metadata_idle();Q2_adjacent_merge=enabled;}
extern "C" std::uint64_t qwen_app_Q2_merged_calls_saved(){return Q2_merged_calls_saved;}
extern "C" void qwen_app_source_io_occupancy(std::uint64_t*out,std::size_t count){
    if(!out||count!=7)throw std::runtime_error("Exact occupancy snapshot required");
    const auto s=source_occupancy.snapshot();if(s[6])throw std::runtime_error("Occupancy snapshot requires completed reads");
    std::copy(s.begin(),s.end(),out);
}
extern "C" int qwen_app_Q2_bundle_index(unsigned layer,unsigned expert){
    if(!Q2_bundle_enabled)return -1;const std::array<unsigned,2>key{layer,expert};
    const auto found=std::lower_bound(std::begin(Q2_bundle_keys),std::end(Q2_bundle_keys),key);
    return found==std::end(Q2_bundle_keys)||*found!=key?-1:int(found-std::begin(Q2_bundle_keys));
}
extern "C" unsigned qwen_app_try_Q2_bundle_group(unsigned layer,const unsigned*experts,unsigned count,void*opaque,
        void(*consume)(void*,unsigned,unsigned,const void*,std::size_t)){
    required().require_completed_window();ops.require_metadata_idle();
    if(!Q2_bundle_enabled||!Q2_bundle_verified||Q2_bundle_fd<0||layer>=48||!experts||!count||count>5||!opaque||!consume)
        throw std::runtime_error("Adjacent bundle group escaped its admitted owner");
    const auto first=qwen_app_Q2_bundle_index(layer,experts[0]);if(first<0)throw std::runtime_error("Bundle group is absent");
    unsigned n=1;if(Q2_adjacent_merge)while(n<count&&qwen_app_Q2_bundle_index(layer,experts[n])==first+int(n))++n;
    required().upload_Q2_bundle_group(Q2_bundle_fd,Q2_bundle_identity,std::uint64_t(first)*1540096,n,
        [&](unsigned item,unsigned role,const void*p,std::size_t size){consume(opaque,item,role,p,size);});
    Q2_bundle_hits+=n;Q2_merged_calls_saved+=n-1;return n;
}
'''

def cache_source(text):
    text='''#include <cstddef>
extern "C" int qwen_app_Q2_bundle_index(unsigned,unsigned);
extern "C" unsigned qwen_app_try_Q2_bundle_group(unsigned,const unsigned*,unsigned,void*,void(*)(void*,unsigned,unsigned,const void*,std::size_t));
'''+text
    start=text.index('            for(size_t i=0;i<fills.size();++i){upload.slot=')
    end=text.index('\n        }',start)
    original=text[start:end]
    callback=original[original.index('                        auto&u='):original.index('                    })){')]
    callback=callback.replace('auto&u=*static_cast<Upload*>(opaque);','auto&group=*static_cast<Group*>(opaque);auto&u=*group.upload;u.slot=group.slots[item];')
    replacement='''            struct Group{Upload*upload;std::array<int,5>slots{};};
            std::array<size_t,40>selected{};size_t chosen=0;
            for(size_t i=0;i<fills.size();++i)if(qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[i].expert))>=0)selected[chosen++]=i;
            for(size_t cursor=0;cursor<chosen;){
                Group group{&upload,{}};std::array<unsigned,5>experts{};
                const unsigned count=unsigned(std::min<size_t>(5,chosen-cursor));
                for(unsigned j=0;j<count;++j){const auto i=selected[cursor+j];experts[j]=unsigned(fills[i].expert);group.slots[j]=fills[i].slot;}
                const auto n=qwen_app_try_Q2_bundle_group(unsigned(il),experts.data(),count,&group,
                    [](void*opaque,unsigned item,unsigned role,const void*source,std::size_t size){
                        if(item>=5)throw std::runtime_error("Bundle group destination index is unowned");
'''+callback+'''
                    });
                if(!n||n>count)throw std::runtime_error("Bundle group completion count differs");
                for(unsigned j=0;j<n;++j){delivered[selected[cursor+j]]=true;bytes+=1536000;}cursor+=n;
            }'''
    return text[:start]+replacement+text[end:]

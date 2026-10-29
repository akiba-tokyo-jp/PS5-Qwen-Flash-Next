# SPDX-License-Identifier: MIT
"""Derive bounded four-demand delivery and a separate immutable extra pack."""
from build_speculative_batch_probe import once

def header_source(text):
 method='''    bool upload_Q2_four(const std::array<std::uintptr_t,4>&addresses,std::size_t bytes,
            const std::function<std::array<std::int64_t,4>(const std::array<SourceReadRequest,4>&)>&read,
            const std::function<void(unsigned,const void*)>&consume){
        require_completed_window();if(!read||!consume||(bytes!=537600&&bytes!=460800))return false;
        std::array<SourceReadRequest,4>requests{};std::array<std::size_t,4>files{},skips{};
        for(unsigned i=0;i<4;++i){const auto at=addresses[i];
            const auto range=candidate_range([&](const auto&r){return at>=r.at&&at<r.at+r.bytes;});
            if(range==ranges_.end()||bytes>range->bytes-(at-range->at))return false;
            files[i]=range->file;const auto offset=range->offset+at-range->at;
            if(offset>=files_[files[i]].bytes||bytes>files_[files[i]].bytes-offset)return false;
            skips[i]=offset%model_read_alignment;const auto requested=std::size_t(rounded(skips[i]+bytes));
            if(requested>model_read_window/4||offset-skips[i]+requested>files_[files[i]].bytes)return false;
            requests[i]={-1,static_cast<unsigned char*>(scratch_)+i*(model_read_window/4),requested,offset-skips[i]};
        }
        for(unsigned i=0;i<4;++i)for(unsigned j=0;j<i;++j)
            if(!source_schedule_parallel(files_[files[i]].identity,requests[i].offset,requests[i].bytes,
                files_[files[j]].identity,requests[j].offset,requests[j].bytes))return false;
        if(ops_.system_headroom()<model_read_system_reserve+model_read_flexible_metadata_margin)
            fail("Four-demand source cannot preserve original reserves");
        for(unsigned i=0;i<4;++i)requests[i].fd=handle(files[i]);
        busy_=true;pending_windows_=4;
        try{std::array<std::int64_t,4>got{};{ProfileScope timing(stats_.read_ns);got=read(requests);}
            for(unsigned i=0;i<4;++i){if(got[i]!=std::int64_t(requests[i].bytes)||ops_.identity(requests[i].fd)!=files_[files[i]].identity)
                    fail("Four-demand read was short or changed identity");
                ++stats_.physical_read_calls;stats_.physical_read_bytes+=requests[i].bytes;
                stats_.maximum_chunk=std::max<std::uint64_t>(stats_.maximum_chunk,requests[i].bytes);}
            stats_.bytes+=4*bytes;stats_.chunks+=4;++stats_.parallel_batches;consumer_started_=ProfileClock::now();
            for(unsigned i=0;i<4;++i)consume(i,static_cast<unsigned char*>(requests[i].target)+skips[i]);completed();return true;
        }catch(...){failed_=true;throw;}
    }
'''
 return once(text,'    bool borrowed_window_contains(const void *pointer,std::size_t bytes) {',method+'    bool borrowed_window_contains(const void *pointer,std::size_t bytes) {')

def owner_source(text):
 text='#include <bounded_read_pool.h>\n#include "Q2-extra-bundle-plan.private.h"\nnamespace {bool Q2_quad_mode=false,Q2_extra_mode=false;std::uint64_t Q2_quad_batches=0,Q2_quad_peak=0;}\n'+text
 text=once(text,'    std::unique_ptr<qwen_app::PairedSourceIO> parallel_;','    std::unique_ptr<qwen_app::PairedSourceIO> parallel_;\n    std::unique_ptr<qwen_app::BoundedReadPool> quad_;')
 text=once(text,'    void require_metadata_idle() {if(parallel_)parallel_->require_completed();}',
  '    void require_metadata_idle() {if(parallel_)parallel_->require_completed();if(quad_)quad_->require_completed();}')
 text=once(text,'        parallel_->start();','''        parallel_->start();
        quad_=std::make_unique<qwen_app::BoundedReadPool>([this](const qwen_app::BoundedReadRequest&r){return read_at(r.fd,r.target,r.bytes,r.offset);});quad_->start();''')
 text=once(text,'        parallel_->stop_completed(); parallel_.reset();','        if(!quad_)throw std::runtime_error("Four-demand worker owner is absent");quad_->stop_completed();quad_.reset();\n        parallel_->stop_completed(); parallel_.reset();')
 text=once(text,'    std::array<std::int64_t, 2> read_pair(','''    std::array<std::int64_t,4> read_four(const std::array<qwen_app::SourceReadRequest,4>&requests){
        if(!Q2_quad_mode||!selected_schedule_||!quad_)throw std::runtime_error("Four-demand owner is not admitted");
        std::array<qwen_app::BoundedReadRequest,4>jobs{};for(unsigned i=0;i<4;++i)jobs[i]={requests[i].fd,requests[i].target,requests[i].bytes,requests[i].offset};
        const auto result=quad_->read(jobs,4);Q2_quad_peak=std::max<std::uint64_t>(Q2_quad_peak,quad_->maximum_inflight());return result;
    }
    std::array<std::int64_t, 2> read_pair(''')
 text=once(text,'        source_occupancy.begin();','        if(!Q2_quad_mode)source_occupancy.begin();')
 text=once(text,'        source_occupancy.end();source_latency.completed(got,ns);return got;','        if(!Q2_quad_mode)source_occupancy.end();source_latency.completed(got,ns);return got;')
 start=text.index('int Q2_bundle_fd=-1;');end=text.index('\nstd::unique_ptr<qwen_app::ResidentMappedSourceReader> reader;',start)
 original=text[start:end];clone=original[original.index('qwen_app::SourceIdentity Q2_bundle_identity'):]
 clone='int Q2_extra_fd=-1;bool Q2_extra_verified=false;\n'+clone
 clone=clone.replace('Q2_bundle','Q2_extra').replace('admit_Q2_bundle','admit_Q2_extra')
 text=text[:end]+'\n'+clone+text[end:]
 text=once(text,'    admit_Q2_bundle(window);','    admit_Q2_bundle(window);admit_Q2_extra(window);')
 text=once(text,'    Q2_bundle_fd=-1;Q2_bundle_verified=Q2_bundle_enabled=false;',
  '    Q2_bundle_fd=-1;Q2_bundle_verified=Q2_bundle_enabled=false;\n    if(!Q2_extra_verified||Q2_extra_fd<0||!ops.close_file(Q2_extra_fd))throw std::runtime_error("Extra bundle did not positively close");Q2_extra_fd=-1;Q2_extra_verified=Q2_extra_mode=false;')
 old='''    return found==std::end(Q2_bundle_keys)||*found!=key?-1:int(found-std::begin(Q2_bundle_keys));'''
 text=once(text,old,'''    if(found!=std::end(Q2_bundle_keys)&&*found==key)return int(found-std::begin(Q2_bundle_keys));
    if(!Q2_extra_mode)return -1;const auto extra=std::lower_bound(std::begin(Q2_extra_keys),std::end(Q2_extra_keys),key);
    return extra==std::end(Q2_extra_keys)||*extra!=key?-1:512+int(extra-std::begin(Q2_extra_keys));''')
 text=once(text,'    required().upload_Q2_bundle_group(Q2_bundle_fd,Q2_bundle_identity,std::uint64_t(first)*1540096,n,',
  '    const bool extra=first>=512;\n    required().upload_Q2_bundle_group(extra?Q2_extra_fd:Q2_bundle_fd,extra?Q2_extra_identity:Q2_bundle_identity,std::uint64_t(first%512)*1540096,n,')
 return text+'''
extern "C" void qwen_app_select_Q2_IO_reduction(unsigned mode){
    required().require_completed_window();ops.require_metadata_idle();if(mode>3||!Q2_extra_verified)throw std::runtime_error("Unknown or unsealed I/O reduction mode");Q2_extra_mode=mode==1;Q2_quad_mode=mode==3;
}
extern "C" bool qwen_app_Q2_quad_enabled(){return Q2_quad_mode;}
extern "C" void qwen_app_Q2_quad_stats(std::uint64_t*out){if(!out)throw std::runtime_error("Missing quad counters");out[0]=Q2_quad_batches;out[1]=Q2_quad_peak;}
extern "C" bool qwen_app_try_Q2_quad(const void*const*addresses,std::size_t bytes,void*opaque,void(*consume)(void*,unsigned,const void*)){
    if(!Q2_quad_mode)return false;required().require_completed_window();ops.require_metadata_idle();
    if(!addresses||!opaque||!consume)throw std::runtime_error("Missing four-demand ownership");
    std::array<std::uintptr_t,4>at{};for(unsigned i=0;i<4;++i)at[i]=reinterpret_cast<std::uintptr_t>(addresses[i]);
    const bool used=required().upload_Q2_four(at,bytes,[&](const std::array<qwen_app::SourceReadRequest,4>&r){return ops.read_four(r);},
        [&](unsigned i,const void*p){consume(opaque,i,p);});if(used)++Q2_quad_batches;return used;
}
'''

def cache_source(text):
 text=once(text,'#include "candidate_expert_policy.h"','#include "candidate_expert_policy.h"\n#define QWEN_TEMPORAL_BASE_PROVIDED 1\n#include <expert_temporal_probation.h>')
 text=once(text,'qwen_app::ExpertPolicy policy;','qwen_app::TemporalProbationPolicy policy;')
 text='''#include <cstddef>
extern "C" bool qwen_app_Q2_quad_enabled();
extern "C" bool qwen_app_try_Q2_quad(const void*const*,std::size_t,void*,void(*)(void*,unsigned,const void*));
'''+text
 marker='            for(size_t cursor=0;cursor<chosen;){'
 text=once(text,marker,'''            std::sort(selected.begin(),selected.begin()+chosen,[&](size_t a,size_t b){return qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[a].expert))<qwen_app_Q2_bundle_index(unsigned(il),unsigned(fills[b].expert));});
'''+marker)
 marker='                // Queue only the next known miss while the producer consumes'
 text=once(text,marker,'''                if(qwen_app_Q2_quad_enabled()&&n==1&&i+3<fills.size()){
                    bool eligible=true;for(unsigned j=0;j<4;++j)if(delivered[i+j])eligible=false;
                    for(unsigned j=0;j<3;++j)if(fills[i+j+1].expert==fills[i+j].expert+1&&fills[i+j+1].slot==fills[i+j].slot+1)eligible=false;
                    if(eligible){struct Upload{ggml_tensor*bank;size_t bytes;std::array<int32_t,4>slots;};Upload job{bank,expert_size,{}};
                        const void*addresses[4];for(unsigned j=0;j<4;++j){addresses[j]=static_cast<const uint8_t*>(w->data)+fills[i+j].expert*expert_size;job.slots[j]=fills[i+j].slot;}
                        ggml_backend_synchronize(backend);
                        if(qwen_app_try_Q2_quad(addresses,expert_size,&job,[](void*opaque,unsigned item,const void*p){auto&u=*static_cast<Upload*>(opaque);
                            if(item>=4||u.slots[item]<0||u.slots[item]>=867)throw std::runtime_error("Four-demand slot is unowned");
                            const auto offset=size_t(u.slots[item])*u.bytes;if(offset>ggml_nbytes(u.bank)||u.bytes>ggml_nbytes(u.bank)-offset)throw std::runtime_error("Four-demand scatter exceeds its bank");
                            ggml_backend_tensor_set(u.bank,p,offset,u.bytes);})) {bytes+=4*expert_size;i+=4;continue;}
                    }
                }
'''+marker)
 return text+'''
extern "C" void qwen_app_select_Q2_temporal(unsigned window){
    if(!resident_reuse_enabled||!resident_reuse_owner||resident_reuse_thread!=std::this_thread::get_id()||(window!=0&&window!=144))throw std::runtime_error("Temporal selection requires the idle retained producer");
    qwen_app::temporal_probation_window=window;
}
'''

# SPDX-License-Identifier: MIT
"""Derive a bounded one-read/three-consumer Q2 bundle delivery path."""
from build_speculative_batch_probe import once

def reader_header(text):
 method='''    void upload_Q2_bundle(int fd,const SourceIdentity&identity,std::uint64_t offset,
            const std::function<void(unsigned,const void*,std::size_t)>&consume){
        require_completed_window();
        constexpr std::size_t stride=1540096,payload=1536000;
        if(fd<0||!consume||!identity[0]||!identity[1]||identity[5]>(512ull<<20)||
           offset%model_read_alignment||offset>identity[5]||stride>identity[5]-offset||
           ops_.identity(fd)!=identity||ops_.system_headroom()<model_read_system_reserve+model_read_flexible_metadata_margin)
            fail("Bundle read escaped its immutable admitted source or reserve");
        busy_=true;pending_windows_=1;
        try{
            std::int64_t got;
            {ProfileScope timing(stats_.read_ns);got=ops_.read_at(fd,scratch_,stride,offset);}
            if(got!=std::int64_t(stride)||ops_.identity(fd)!=identity)
                fail("Immutable bundle read was short or changed identity");
            ++stats_.physical_read_calls;stats_.physical_read_bytes+=stride;
            stats_.bytes+=payload;++stats_.chunks;stats_.maximum_chunk=std::max<std::uint64_t>(stats_.maximum_chunk,stride);
            consumer_started_=ProfileClock::now();
            const auto*p=static_cast<const unsigned char*>(scratch_);
            consume(0,p,537600);consume(1,p+537600,537600);consume(2,p+1075200,460800);
            completed();
        }catch(...){failed_=true;throw;}
    }
'''
 return once(text,'    bool borrowed_window_contains(const void *pointer,std::size_t bytes) {',method+'    bool borrowed_window_contains(const void *pointer,std::size_t bytes) {')

def cache_source(text):
 text='''#include <cstddef>
extern "C" bool qwen_app_Q2_bundle_enabled();
extern "C" bool qwen_app_try_Q2_bundle(unsigned,unsigned,void*,void(*)(void*,unsigned,const void*,std::size_t));
'''+text
 marker='        std::array<bool,40> delivered{};'
 text=once(text,marker,marker+'''
        const bool bundle_refill=qwen_app_Q2_bundle_enabled();
        if(bundle_refill){
            if(six_refill||fills.size()>delivered.size()||g.banks.size()!=3||l.experts.size()!=3)
                throw std::runtime_error("Q2 bundles require the original bounded three-role cache");
            struct Upload{std::array<ggml_tensor*,3>banks{};std::array<size_t,3>residues{};int slot=-1;};
            Upload upload;std::array<bool,3>seen{};
            for(unsigned ip=0;ip<3;++ip){const auto*w=l.experts[ip];unsigned role;
                if(strstr(w->name,"ffn_gate_exps.weight"))role=0;
                else if(strstr(w->name,"ffn_up_exps.weight"))role=1;
                else if(strstr(w->name,"ffn_down_exps.weight"))role=2;
                else throw std::runtime_error("Unknown bundle role");
                const size_t size=role==2?460800:537600;
                if(seen[role]||w->nb[2]!=size||g.banks[ip]->nb[2]!=size||w->ne[2]!=512||
                   w->type!=(role==2?GGML_TYPE_Q2_0:GGML_TYPE_Q2_K))
                    throw std::runtime_error("Actual Q2 bundle tensor geometry differs");
                seen[role]=true;upload.banks[role]=g.banks[ip];upload.residues[role]=bindings.at(w).cached->view_offs;
            }
            for(size_t i=0;i<fills.size();++i){upload.slot=fills[i].slot;
                if(qwen_app_try_Q2_bundle(unsigned(il),unsigned(fills[i].expert),&upload,
                    [](void*opaque,unsigned role,const void*source,std::size_t size){
                        auto&u=*static_cast<Upload*>(opaque);if(role>2||u.slot<0||u.slot>=867)
                            throw std::runtime_error("Bundle destination slot is unowned");
                        auto*bank=u.banks[role];const auto offset=size_t(u.slot)*bank->nb[2]+u.residues[role];
                        if(offset>ggml_nbytes(bank)||size>ggml_nbytes(bank)-offset)
                            throw std::runtime_error("Bundle destination exceeds its owned bank");
                        ggml_backend_tensor_set(bank,source,offset,size);
                    })){delivered[i]=true;bytes+=1536000;}
            }
        }
''')
 text=text.replace('if(six_refill&&delivered[i])','if((six_refill||bundle_refill)&&delivered[i])')
 text=text.replace('(!six_refill||!delivered[i+n])','(!(six_refill||bundle_refill)||!delivered[i+n])')
 text=text.replace('(!six_refill||!delivered[i+1])','(!(six_refill||bundle_refill)||!delivered[i+1])')
 text=once(text,'n == 1 && i + 1 < fills.size() && qwen_app_model_source_pair_enabled(expert_size)',
  'n == 1 && i + 1 < fills.size() && (!(six_refill||bundle_refill)||!delivered[i+1]) && qwen_app_model_source_pair_enabled(expert_size)')
 return text

def owner_source(text):
 text='''#include "Q2-bundle-plan.private.h"
extern "C" {
#include "hash/sha256/sha256.h"
}
'''+text
 marker='NativeReads ops;'
 extra='''
int Q2_bundle_fd=-1;bool Q2_bundle_verified=false,Q2_bundle_enabled=false;
qwen_app::SourceIdentity Q2_bundle_identity{};std::uint64_t Q2_bundle_hits=0;
void admit_Q2_bundle(void*scratch){
    if(Q2_bundle_fd>=0||Q2_bundle_verified||!scratch)throw std::runtime_error("Bundle source already owns a lifetime");
    Q2_bundle_fd=ops.open_direct(Q2_bundle_path);
    if(Q2_bundle_fd<0||!(fcntl(Q2_bundle_fd,F_GETFL)&O_DIRECT))throw std::runtime_error("Immutable Direct bundle source required");
    const auto current=ops.identity(Q2_bundle_fd);
    if(!current[0]||!current[1])throw std::runtime_error("Bundle identity is absent");
    // Only the already qualified title nullfs device number may translate.
    for(unsigned i=1;i<10;++i)if(current[i]!=Q2_bundle_expected_identity[i])
        throw std::runtime_error("Immutable bundle identity differs");
    // Use the application's qualified descriptor ABI; O_NOFOLLOW plus a
    // second descriptor binds the named inode independently of the first fd.
    const auto require_named=[&]{
        const int named=ops.open_direct(Q2_bundle_path);
        if(named<0)throw std::runtime_error("Bundle named inode cannot reopen without following links");
        const auto key=ops.identity(named);const bool closed=ops.close_file(named);
        if(!closed||key!=current)throw std::runtime_error("Bundle named inode or descriptor retirement differs");
    };
    require_named();
    sha256_t whole;sha256_init(&whole);
    for(std::uint64_t at=0;at<current[5];){
        if(ops.system_headroom()<qwen_app::model_read_system_reserve+qwen_app::model_read_flexible_metadata_margin)
            throw std::runtime_error("Bundle integrity cannot retain original reserves");
        const auto n=std::size_t(std::min<std::uint64_t>(qwen_app::model_read_window,current[5]-at));
        const auto rounded=(n+16383)&~std::size_t(16383);
        if(ops.read_at(Q2_bundle_fd,scratch,rounded,at)!=std::int64_t(n)||ops.identity(Q2_bundle_fd)!=current)
            throw std::runtime_error("Bundle complete hash read was short or unstable");
        sha256_update(&whole,static_cast<const unsigned char*>(scratch),n);at+=n;
    }
    unsigned char digest[32];sha256_final(&whole,digest);char hex[65]{};
    for(unsigned i=0;i<32;++i){hex[2*i]="0123456789abcdef"[digest[i]>>4];hex[2*i+1]="0123456789abcdef"[digest[i]&15];}
    if(std::strcmp(hex,Q2_bundle_SHA256)||ops.read_at(Q2_bundle_fd,scratch,16384,current[5])!=0||ops.identity(Q2_bundle_fd)!=current)
        throw std::runtime_error("Complete immutable bundle SHA256/EOF differs");
    require_named();Q2_bundle_identity=current;Q2_bundle_verified=true;
}
'''
 text=once(text,marker,marker+extra)
 text=once(text,'    reader->preflight();','    reader->preflight();\n    admit_Q2_bundle(window);')
 text=once(text,'    required().close_completed();','    required().close_completed();\n    if(!Q2_bundle_verified||Q2_bundle_fd<0||!ops.close_file(Q2_bundle_fd))throw std::runtime_error("Bundle source did not positively close");\n    Q2_bundle_fd=-1;Q2_bundle_verified=Q2_bundle_enabled=false;')
 return text+'''
extern "C" void qwen_app_select_Q2_bundle(bool enabled){
    required().require_completed_window();ops.require_metadata_idle();
    if(!Q2_bundle_verified||Q2_bundle_fd<0)throw std::runtime_error("Bundle source is not positively admitted");
    Q2_bundle_enabled=enabled;
}
extern "C" bool qwen_app_Q2_bundle_enabled(){return Q2_bundle_enabled;}
extern "C" std::uint64_t qwen_app_Q2_bundle_hits(){return Q2_bundle_hits;}
extern "C" bool qwen_app_try_Q2_bundle(unsigned layer,unsigned expert,void*opaque,
        void(*consume)(void*,unsigned,const void*,std::size_t)){
    if(!Q2_bundle_enabled)return false;
    required().require_completed_window();ops.require_metadata_idle();
    if(!Q2_bundle_verified||Q2_bundle_fd<0||layer>=48||expert>=512||!opaque||!consume)
        throw std::runtime_error("Bundle dispatch escaped its exact owner or geometry");
    const std::array<unsigned,2>key{layer,expert};
    const auto found=std::lower_bound(std::begin(Q2_bundle_keys),std::end(Q2_bundle_keys),key);
    if(found==std::end(Q2_bundle_keys)||*found!=key)return false;
    const auto index=std::size_t(found-std::begin(Q2_bundle_keys));
    required().upload_Q2_bundle(Q2_bundle_fd,Q2_bundle_identity,index*1540096ull,
        [&](unsigned role,const void*p,std::size_t n){consume(opaque,role,p,n);});
    ++Q2_bundle_hits;return true;
}
'''

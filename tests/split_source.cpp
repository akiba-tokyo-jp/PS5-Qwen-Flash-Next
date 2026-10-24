// SPDX-License-Identifier: MIT
// Pattern data exercises logical 512 MiB boundaries without large host buffers.
#include "mapped_source.h"
#include <iostream>
#include <map>
using namespace qwen_app;
static void check(bool b,const char *m){if(!b)throw std::runtime_error(m);}
template<class F> static void rejected(F f){bool caught=false;try{f();}catch(const std::exception&){caught=true;}check(caught,"Unsafe split operation was admitted");}
struct Ops final:SourceReadOps {
    std::vector<SourceFile> files;
    std::map<int,std::size_t> fds;
    unsigned opens=0,closes=0,reads=0,live=0,peak=0,fail_read=0;
    bool changed=false,low=false;
    static unsigned char pattern(std::uint64_t at){return static_cast<unsigned char>((at*13+at/251)%239);}
    void setup(unsigned parts=3) {
        for(unsigned i=0;i<parts;++i){const auto bytes=i+1==parts?12345ull:model_source_part_bytes;
            SourceIdentity id{1,i+1,0100644,0,0,bytes,100,0,100,0};
            files.push_back({"part-"+std::to_string(i),bytes,id});fds[10+int(i)]=i;}
    }
    SourceIdentity identity(int fd)override{auto x=files.at(fds.at(fd)).identity;if(changed)++x[8];return x;}
    int open_direct(const std::string&p)override{for(std::size_t i=0;i<files.size();++i)if(files[i].path==p){const int fd=100+int(++opens);fds[fd]=i;peak=std::max(peak,++live);return fd;}return-1;}
    bool close_file(int fd)override{fds.erase(fd);++closes;--live;return true;}
    std::int64_t read_at(int fd,void*out,std::size_t n,std::uint64_t at)override{
        ++reads;check(n<=model_read_window&&n%model_read_alignment==0&&at%model_read_alignment==0,"Unaligned split I/O");
        check(reinterpret_cast<std::uintptr_t>(out)%model_read_alignment==0,"Unaligned split destination");
        const auto part=fds.at(fd);check(at<files[part].bytes,"Split read exceeded its actual file");
        const auto count=std::min<std::uint64_t>(n,files[part].bytes-at);
        for(std::size_t i=0;i<count;++i)static_cast<unsigned char*>(out)[i]=pattern(part*model_source_part_bytes+at+i);
        return std::int64_t(count)-(fail_read==reads?1:0);
    }
    std::uint64_t system_headroom()override{return low?0:512ull<<20;}
};
static LogicalSourceFile logical(const Ops&o){std::uint64_t total=0;std::vector<std::size_t>parts;for(std::size_t i=0;i<o.files.size();++i){total+=o.files[i].bytes;parts.push_back(i);}return{o.files[0].path,total,parts};}
static void bytes_equal(const void*p,std::uint64_t at,std::size_t n){for(std::size_t i=0;i<n;++i)check(static_cast<const unsigned char*>(p)[i]==Ops::pattern(at+i),"Original bytes changed at a split boundary");}
static constexpr std::uintptr_t base=1ull<<40;
int main(){try{
    std::vector<unsigned char>storage(model_read_window+model_read_alignment);
    const auto raw=reinterpret_cast<std::uintptr_t>(storage.data());void*scratch=reinterpret_cast<void*>((raw+16383)&~std::uintptr_t(16383));
    {
        Ops o;o.setup();auto l=logical(o);MappedSourceReader r(o.files,o,scratch,{l});
        check(r.logical_file_bytes(10)==l.bytes&&o.identity(10)[5]==model_source_part_bytes,"Logical size altered physical identity");
        r.register_mapping(base,l.bytes,10);
        check(r.contains_metadata(base+model_source_part_bytes-13,30),"Contiguous logical boundary was rejected");
        const auto at=model_source_part_bytes-123;std::size_t done=0;
        while(done<2000){std::size_t copied=0;const auto*p=r.prepare(base+at+done,2000-done,copied);check(copied>0,"Split copy made no progress");bytes_equal(p,at+done,copied);done+=copied;r.completed();}
        check(done==2000,"Split CPU copy did not cover the exact logical range");
        const std::array<std::uint64_t,2>offsets{model_source_part_bytes-1002,model_source_part_bytes*2-48};
        unsigned consumed=0;const std::size_t n=3276800;
        // The second crossing must stay inside the actual final source tail.
        const std::array<std::uintptr_t,2>addresses{base+offsets[0],base+model_source_part_bytes-48};
        r.upload_pair(addresses,n,[&](unsigned i,const void*p){bytes_equal(p,addresses[i]-base,n);++consumed;});
        check(consumed==2&&r.stats().physical_read_calls>=6,"Crossing windows omitted data or physical reads");
        auto windows=r.prepare_pair({base+model_source_part_bytes*2-48,base+model_source_part_bytes*2+16},1000);
        bytes_equal(windows[0],model_source_part_bytes*2-48,1000);bytes_equal(windows[1],model_source_part_bytes*2+16,1000);r.completed();
        windows=r.prepare_pair({base+l.bytes-100,base+l.bytes-123},100);
        bytes_equal(windows[0],l.bytes-100,100);bytes_equal(windows[1],l.bytes-123,100);r.completed();
        rejected([&]{r.contains_metadata(base+l.bytes-10,11);});
        r.before_unmap(base,l.bytes);r.after_unmap(base,l.bytes);r.close_completed();check(o.live==0&&o.peak<=8,"Split descriptors escaped their bound");
    }
    for(unsigned fault=0;fault<6;++fault){
        Ops o;o.setup();auto l=logical(o);MappedSourceReader r(o.files,o,scratch,{l});r.register_mapping(base,l.bytes,10);
        if(fault<3)o.fail_read=fault+1;
        if(fault==3)o.changed=true;
        if(fault==4)o.low=true;
        rejected([&]{r.upload_pair({base+model_source_part_bytes-123,base+model_source_part_bytes-456},2000,
            [&](unsigned,const void*){if(fault==5)throw std::runtime_error("Consumer completion failed");});});
        rejected([&]{r.close_completed();});check(o.closes==0,"Failed split backing was released");
    }
    for(unsigned fault=0;fault<6;++fault){Ops o;o.setup();auto l=logical(o);
        if(fault==0)l.parts[1]=0;if(fault==1)l.parts.pop_back();if(fault==2)++l.bytes;
        if(fault==3)l.path="unowned";if(fault==4)l.parts[1]=999;if(fault==5){--o.files[0].bytes;--o.files[0].identity[5];--l.bytes;}
        rejected([&]{MappedSourceReader r(o.files,o,scratch,{l});});
    }
    {
        Ops o;o.setup();auto l=logical(o);MappedSourceReader r(o.files,o,scratch,{l});
        const auto span=(l.bytes+16383)&~std::uint64_t(16383);r.register_mapping(base,l.bytes,10);r.register_mapping(base+span,l.bytes,10);
        rejected([&]{r.contains_metadata(base+l.bytes-1,std::size_t(span-l.bytes+2));});
        r.after_unmap(base,l.bytes);r.after_unmap(base+span,l.bytes);r.close_completed();
    }
    {
        Ops o;o.setup();auto l=logical(o);MappedSourceReader r(o.files,o,scratch,{l});r.register_mapping(base,l.bytes,10);
        const auto hole=3*model_read_alignment;
        r.after_unmap(base+hole,model_read_alignment);
        check(!r.contains_metadata(base+hole+16,1),"Retired interior bytes were admitted");
        rejected([&]{r.contains_metadata(base+hole-16,32);});
        check(r.contains_metadata(base+hole+model_read_alignment,32),"Owned bytes after an interior retirement were rejected");
        r.after_unmap(base,hole);r.after_unmap(base+hole+model_read_alignment,l.bytes-hole-model_read_alignment);r.close_completed();
    }
    {
        Ops o;o.setup(711);auto l=logical(o);MappedSourceReader r(o.files,o,scratch,{l});r.register_mapping(base,l.bytes,10);
        for(unsigned i=0;i<20;++i){std::size_t copied=0;const auto*p=r.prepare(base+i*model_source_part_bytes,16,copied);bytes_equal(p,i*model_source_part_bytes,copied);r.completed();}
        check(o.peak==8,"Physical split sources lost the eight-descriptor cache");r.after_unmap(base,l.bytes);r.close_completed();
    }
    std::cout<<"Split logical sizes, exact boundary/EOF bytes, 711 parts, eight descriptors and fault retention passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}

// SPDX-License-Identifier: MIT
// Completed real source keys, exact replay ordering, finite leases and refusal.
#include "mapped_source.h"
#include <map>
#include <iostream>
using namespace qwen_app;
static void check(bool value,const char * message){if(!value)throw std::runtime_error(message);}
template<class F> static void rejects(F f){bool yes=false;try{f();}catch(const std::exception &){yes=true;}check(yes,"An unsafe trace continuation was accepted");}
struct Ops:SourceReadOps {
    std::vector<SourceFile> files;
    std::map<int,unsigned> fds;
    unsigned opened=0,closed=0,reads=0;bool changed=false;
    std::uint64_t available=512ull<<20;
    Ops(){for(unsigned i=0;i<2;++i){const auto bytes=128ull<<20;files.push_back({"sealed-"+std::to_string(i),bytes,{1,i+1,0100644,0,0,bytes,123,0,123,0}});fds[10+int(i)]=i;}}
    SourceIdentity identity(int fd)override{auto value=files.at(fds.at(fd)).identity;if(changed)++value[8];return value;}
    int open_direct(const std::string & path)override{for(unsigned i=0;i<2;++i)if(path==files[i].path){int fd=100+int(++opened);fds[fd]=i;return fd;}return -1;}
    bool close_file(int fd)override{++closed;return fds.erase(fd)==1;}
    std::uint64_t system_headroom()override{return available;}
    std::int64_t read_at(int fd,void *,std::size_t bytes,std::uint64_t offset)override{++reads;check(fds.count(fd)&&offset+bytes<=files[fds.at(fd)].bytes,"Invalid replay extent");return std::int64_t(bytes);}
    SourcePipelineTimes pipeline_pair(const std::array<SourceReadRequest,2> & requests,const std::array<std::uint64_t,2> & expected,
            const std::function<void(unsigned)> & before,const std::function<void(unsigned,const void*)> & consume)override{
        for(unsigned i=0;i<2;++i){before(i);check(read_at(requests[i].fd,requests[i].target,requests[i].bytes,requests[i].offset)==std::int64_t(expected[i]),"Short source");consume(i,requests[i].target);}return{};
    }
};
struct Fixture {
    static constexpr std::uintptr_t a=512ull<<30,b=a+(256ull<<20);
    static constexpr std::size_t bytes=3276800;
    Ops ops;std::vector<unsigned char> buffer;
    void * scratch;
    MappedSourceReader reader;
    Fixture():buffer(model_read_window+model_read_alignment),scratch(reinterpret_cast<void *>((reinterpret_cast<std::uintptr_t>(buffer.data())+model_read_alignment-1)&~std::uintptr_t(model_read_alignment-1))),reader(ops.files,ops,scratch){
        reader.register_mapping(a,ops.files[0].bytes,10);reader.register_mapping(b,ops.files[1].bytes,11);reader.enable_completed_pair_trace();
    }
    void fill(unsigned count=32){for(unsigned i=0;i<(count-1)*512+1;++i){const auto offset=(i/512)*131072+(i%512)*16384;reader.upload_pair({a+4096+offset,b+8192+offset},bytes,[](unsigned,const void*){});}}
};
int main(){try{
    {Fixture f;f.fill(33);unsigned calls=0;const auto before=f.reader.stats();
     f.reader.replay_completed_pair_trace([&](unsigned round,unsigned mode,unsigned index,const auto & r,const auto & expected,const auto & key){
        check(round==calls/128&&mode==((round%2)?3-(calls%128)/32:(calls%128)/32)&&index==calls%32,"Trace order changed");
        check(key.files[0]==0&&key.files[1]==1&&key.bytes==Fixture::bytes,"Trace file or byte key changed");
        check(key.completed_ordinal==index*512,"The bounded trace is not spread across completed work");
        check(key.offsets[0]==4096+index*131072&&key.offsets[1]==8192+index*131072,"Trace captured an uncompleted or extra key");
        for(unsigned i=0;i<2;++i){check(r[i].bytes==3293184&&r[i].offset==index*131072&&expected[i]==r[i].bytes,"Alignment or exact count changed");
            check(r[i].target==static_cast<unsigned char*>(f.scratch)+i*(model_read_window/2),"The diagnostic allocated another window");}
        check(f.ops.opened-f.ops.closed<=8,"Descriptor budget exceeded");++calls;
     });
     check(calls==384&&f.reader.stats().bytes==before.bytes&&f.reader.stats().completed_windows==before.completed_windows,"Diagnostic polluted inference counters");
     f.reader.require_completed_window();rejects([&]{f.reader.replay_completed_pair_trace([](auto,auto,auto,const auto&,const auto&,const auto&){});});}
    {Fixture f;f.fill(31);unsigned calls=0;rejects([&]{f.reader.replay_completed_pair_trace([&](auto,auto,auto,const auto&,const auto&,const auto&){++calls;});});check(!calls,"Incomplete trace was replayed");}
    {Fixture f;f.fill();unsigned calls=0;rejects([&]{f.reader.replay_completed_pair_trace([&](auto,auto,auto,const auto&,const auto&,const auto&){++calls;throw std::runtime_error("Injected consumer failure");});});
     check(calls==1&&!f.ops.closed,"Failed read lease was closed");rejects([&]{f.reader.require_completed_window();});}
    {Fixture f;f.fill();f.ops.available=0;unsigned calls=0;rejects([&]{f.reader.replay_completed_pair_trace([&](auto,auto,auto,const auto&,const auto&,const auto&){++calls;});});check(!calls,"The reserve was bypassed");}
    {Fixture f;f.fill();f.ops.changed=true;unsigned calls=0;rejects([&]{f.reader.replay_completed_pair_trace([&](auto,auto,auto,const auto&,const auto&,const auto&){++calls;});});check(!calls,"An altered file was replayed");}
    {Fixture f;f.fill();rejects([&]{f.reader.replay_completed_pair_trace([&](auto,auto,auto,const auto&,const auto&,const auto&){f.reader.close_completed();});});check(!f.ops.closed,"An active source lease was closed");}
    std::cout<<"Completed trace capture, bounded replay, identity/reserve and failed-lease controls passed\n";
}catch(const std::exception & e){std::cerr<<e.what()<<'\n';return 1;}}

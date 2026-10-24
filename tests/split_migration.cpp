// SPDX-License-Identifier: MIT
#include "split_migration.h"
#include <cstring>
#include <iostream>
#include <vector>
using namespace qwen_app;
static void check(bool v,const char*m){if(!v)throw std::runtime_error(m);}
struct Ops final:SplitMigrationOps {
    std::vector<unsigned char>pending;unsigned mutations=0,writes=0,reads=0,truncates=0;
    bool published=false,flushed=false,changed=false;std::string fault,stage;std::uint64_t expected=0,new_size=0;
    explicit Ops(std::string f=""):fault(std::move(f)){}
    bool source_unchanged()override{return !changed&&fault!="source_changed";}
    void guard(const char*s,std::uint64_t,std::size_t)override{stage=s;if(fault==stage)throw std::runtime_error("Guard refused");}
    static unsigned char pattern(std::uint64_t at){return static_cast<unsigned char>((at*17+at/311)%251);}
    std::int64_t read_source(void*p,std::size_t n,std::uint64_t at)override{
        ++reads;const auto count=std::min<std::uint64_t>(n,expected-at);
        for(std::size_t i=0;i<count;++i)static_cast<unsigned char*>(p)[i]=pattern(at+i);
        return std::int64_t(count)-(fault=="source_short"?1:0);
    }
    bool create_pending(std::uint64_t n)override{++mutations;pending.resize(n);return fault!="create_unknown";}
    std::int64_t write_pending(void*p,std::size_t n,std::uint64_t at)override{
        ++writes;check(at+n<=pending.size(),"Pending write escaped its bound");std::memcpy(pending.data()+at,p,n);return std::int64_t(n)-(fault=="write_short"?1:0);}
    bool flush_and_open_readback()override{flushed=true;return fault!="flush_unknown";}
    std::int64_t read_pending(void*p,std::size_t n,std::uint64_t at)override{
        check(flushed,"Readback preceded durability");const auto count=std::min<std::uint64_t>(n,pending.size()-at);
        std::memcpy(p,pending.data()+at,count);if(fault=="readback_corrupt")static_cast<unsigned char*>(p)[0]^=1;
        return std::int64_t(count)-(fault=="readback_short"?1:0);
    }
    bool pending_unchanged()override{return fault!="pending_changed";}
    bool publish_verified_pending(const std::string&d)override{check(flushed&&d.size()==64,"Unverified publication");published=true;return fault!="publish_unknown";}
    bool truncate_source_once(std::uint64_t n)override{++truncates;check(published&&truncates==1,"Unverified or repeated source truncation");new_size=n;return fault!="truncate_unknown";}
    bool flush_and_record_source(std::uint64_t n)override{return new_size==n&&fault!="record_unknown";}
};
int main(){try{
    std::vector<unsigned char>storage(split_migration_window_bytes+16384);const auto at=reinterpret_cast<std::uintptr_t>(storage.data());void*buffer=reinterpret_cast<void*>((at+16383)&~std::uintptr_t(16383));
    for(const auto bytes:{1ull,12345ull,(8ull<<20)+33}){
        Ops o;o.expected=split_migration_part_bytes+bytes;const auto r=migrate_verified_tail(o,buffer,o.expected);
        check(r.part_bytes==bytes&&r.new_source_bytes==split_migration_part_bytes&&o.truncates==1,"Tail geometry or publication ordering changed");
        for(std::size_t i=0;i<o.pending.size();++i)check(o.pending[i]==Ops::pattern(split_migration_part_bytes+i),"Exact original tail bytes changed");
    }
    const std::vector<std::string>faults={"source_changed","create_pending","create_unknown","read_source","source_short","write_pending","write_short","flush_pending","flush_unknown","read_pending","readback_corrupt","readback_short","pending_changed","publish_verified","publish_unknown","truncate_verified_source","truncate_unknown","flush_truncated_source","record_unknown"};
    for(const auto&fault:faults){Ops o(fault);o.expected=split_migration_part_bytes+12345;bool refused=false;
        try{migrate_verified_tail(o,buffer,o.expected);}catch(const std::exception&){refused=true;}
        check(refused,"Fault did not refuse migration");
        const bool late=fault=="truncate_unknown"||fault=="flush_truncated_source"||fault=="record_unknown";
        check(o.truncates==(late?1u:0u),"A failure lost or repeated source truncation");
        if(fault=="source_changed")check(o.mutations==0,"Changed source created output");
    }
    std::cout<<"Exact tail copy/full SHA256/readback/publication/truncation and 19 fault controls passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}

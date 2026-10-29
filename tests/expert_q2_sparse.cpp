// SPDX-License-Identifier: MIT
#include <mapped_source.h>
#include <cstdlib>
#include <iostream>
#include <map>
using namespace qwen_app;
void check(bool ok){if(!ok)throw std::runtime_error("Composite source check failed");}
struct Ops:SourceReadOps{
    std::vector<SourceFile> files;
    std::map<int,std::size_t> descriptors;int next=1;
    SourceIdentity identity(int fd)override{return files.at(descriptors.at(fd)).identity;}
    int open_direct(const std::string&path)override{
        for(std::size_t i=0;i<files.size();++i)if(files[i].path==path){descriptors[next]=i;return next++;}return -1;
    }
    bool close_file(int fd)override{return descriptors.erase(fd)==1;}
    std::int64_t read_at(int fd,void*target,std::size_t bytes,std::uint64_t offset)override{
        const auto i=descriptors.at(fd);check(offset%16384==0&&bytes%16384==0&&bytes<=model_read_window&&reinterpret_cast<std::uintptr_t>(target)%16384==0);
        const auto n=std::min<std::uint64_t>(bytes,files[i].bytes-offset);
        for(std::size_t j=0;j<n;++j)static_cast<unsigned char*>(target)[j]=(offset+j+i*17)%251;
        return n;
    }
    std::uint64_t system_headroom()override{return 512ull<<20;}
};
int main(){
    Ops ops;
    for(const auto&row:std::vector<std::pair<std::string,std::uint64_t>>{{"head",512ull<<20},{"tail",1000},{"retained",65536}}){
        SourceIdentity id{1,ops.files.size()+1,0100644,0,0,row.second,1,0,1,0};ops.files.push_back({row.first,row.second,id});}
    const std::uint64_t bytes=(512ull<<20)+32768+1000;
    std::vector<LogicalSourceFile> logical{{"head",bytes,{0,1}}};
    std::vector<ExpertQ2SourceSegments> plans{{"head",{{0,12345,0,0},{12345,30000,2,777},{42345,(512ull<<20)-42345,0,42345},{512ull<<20,32768,2,0},{(512ull<<20)+32768,1000,1,0}}}};
    std::vector<unsigned char> storage(model_read_window+16384);
    void*scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(storage.data())+16383)&~std::uintptr_t(16383));
    MappedSourceReader reader(ops.files,ops,scratch,logical,plans);const auto fd=ops.open_direct("head");
    constexpr std::uintptr_t base=0x100000000;reader.register_mapping(base,bytes,fd);
    for(const auto window:std::vector<std::pair<std::uint64_t,std::size_t>>{{10000,50000},{12345,30000},{(512ull<<20)-500,34268}}){
        std::size_t done=0;
        while(done<window.second){std::size_t copied=0;const auto start=window.first+done;
            const auto*data=static_cast<const unsigned char*>(reader.prepare(base+start,window.second-done,copied));check(copied>0);
            for(std::size_t i=0;i<copied;++i){const auto at=start+i;
                const auto expected=at>=(512ull<<20)+32768?(at-(512ull<<20)-32768+17)%251:
                    at>=(512ull<<20)?(at-(512ull<<20)+34)%251:
                    at>=12345&&at<42345?(at-12345+777+34)%251:at%251;
                check(data[i]==expected);}
            reader.completed();done+=copied;
        }
    }
#if defined(EXPERT_Q2_PAIR_CASES)
    const auto expected=[](std::uint64_t at){return
        at>=(512ull<<20)+32768?(at-(512ull<<20)-32768+17)%251:
        at>=(512ull<<20)?(at-(512ull<<20)+34)%251:
        at>=12345&&at<42345?(at-12345+777+34)%251:at%251;};
    struct Pair{std::array<std::uint64_t,2>at;std::size_t bytes;};
    for(const auto&pair:std::vector<Pair>{{{10000,12344},50000},{{(512ull<<20)-500,(512ull<<20)+32768-500},1000},
            {{41345,(512ull<<20)+32768-700},1000}}){
        const std::array<std::uintptr_t,2>addresses{base+pair.at[0],base+pair.at[1]};
        const auto verify=[&](unsigned arm,const void*window){
            const auto*data=static_cast<const unsigned char*>(window);
            for(std::size_t i=0;i<pair.bytes;++i)check(data[i]==expected(pair.at[arm]+i));};
        const auto windows=reader.prepare_pair(addresses,pair.bytes);verify(0,windows[0]);verify(1,windows[1]);reader.completed();
        unsigned consumed=0;reader.upload_pair(addresses,pair.bytes,[&](unsigned arm,const void*window){check(arm==consumed++);verify(arm,window);});
        check(consumed==2);
    }
#endif
    reader.before_unmap(base,bytes);reader.after_unmap(base,bytes);reader.close_completed();check(ops.close_file(fd));
    unsigned refused=0;
    for(unsigned bad=0;bad<8;++bad){auto changed=plans;
        if(bad==0)changed[0].segments[1].logical_offset++;
        if(bad==1)changed[0].segments[1].bytes++;
        if(bad==2)changed[0].segments[1].physical_offset=65536;
        if(bad==3)changed[0].segments[1].bytes=0;
        if(bad==4)changed[0].path="unknown";
        if(bad==5)changed.push_back(changed[0]);
        if(bad==6)changed[0].segments[1].physical=3;
        if(bad==7)changed[0].segments.pop_back();
        try{MappedSourceReader invalid(ops.files,ops,scratch,logical,changed);}
        catch(const std::exception&){++refused;}
    }
    check(refused==8);
    std::cout<<"{\"composite_original_and_retained_bytes_exact\":true,\"boundary_and_retirement_checks\":true,\"invalid_plans_refused\":8}\n";
}

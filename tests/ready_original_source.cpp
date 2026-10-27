// SPDX-License-Identifier: MIT
// Actual source/role/two-call owners with metadata callbacks only. Addresses
// are never dereferenced; no physical file, weights, learned model or GPU runs.
#include "ready_original_source.h"
#include "ready_expert_execution.h"
#include "model_integrity.h"
#include <atomic>
#include <fstream>
#include <iostream>
#include <map>
extern "C" {
#include "hash/sha256/sha256.h"
}
using namespace qwen_app;using Json=nlohmann::json;
void check(bool good){if(!good)throw std::runtime_error("Original source control failed");}
namespace qwen_app {std::string sha256_metadata_bytes(const std::string &text) {
    sha256_t h;sha256_init(&h);sha256_update(&h,reinterpret_cast<const unsigned char *>(text.data()),text.size());unsigned char raw[32];sha256_final(&h,raw);
    std::string out;for(auto b:raw){out+="0123456789abcdef"[b>>4];out+="0123456789abcdef"[b&15];}return out;
}}
struct Ops final:SourceReadOps {
    const ReadyOriginalPlan &plan;std::string scenario;std::mutex mutex;std::condition_variable changed;
    std::map<int,unsigned> descriptors;unsigned next=100,opens=0,closes=0,peak_fd=0,reads=0,active=0,peak=0,arrived=0,expected=1,verified=0,lease_reads=0;
    ReadyExpertWave *wave=nullptr;
    Ops(const ReadyOriginalPlan &p,std::string s):plan(p),scenario(std::move(s)){}
    SourceIdentity identity(int fd)override {std::lock_guard<std::mutex> lock(mutex);auto r=plan.files.at(descriptors.at(fd)).identity;if(scenario=="identity")++r[1];return r;}
    int open_direct(const std::string &name)override {
        std::lock_guard<std::mutex> lock(mutex);
        const auto it=std::find_if(plan.files.begin(),plan.files.end(),[&](const auto &f){return f.path==name;});check(it!=plan.files.end());
        const int fd=next++;descriptors[fd]=unsigned(it-plan.files.begin());++opens;peak_fd=std::max<unsigned>(peak_fd,descriptors.size());return fd;
    }
    bool close_file(int fd)override {std::lock_guard<std::mutex> lock(mutex);check(descriptors.erase(fd)==1);++closes;return scenario!="close";}
    std::int64_t read_at(int fd,void *,std::size_t bytes,std::uint64_t offset)override {
        std::unique_lock<std::mutex> lock(mutex);const auto &f=plan.files.at(descriptors.at(fd));check(offset%16384==0&&bytes==padded_bank_stride&&offset+bytes<=f.bytes);
        ++reads;++active;++arrived;peak=std::max(peak,active);if(wave->snapshot().GPU_pending)++lease_reads;changed.notify_all();
        check(changed.wait_for(lock,std::chrono::seconds(3),[&]{return arrived==expected;}));--active;
        if(scenario=="read-exception")throw std::runtime_error("Known metadata read exception");
        return scenario=="short"?bytes-16384:bytes;
    }
    std::uint64_t system_headroom()override{return scenario=="memory"?0:256u<<20;}
    static Ops *current;
    static void stage(const char *text) {
        if(std::string(text).find("ready_original_batch_before ")==0){std::lock_guard<std::mutex> lock(current->mutex);current->expected=std::string(text).find("calls=2")!=std::string::npos?2:1;current->arrived=0;}
    }
    static bool verify(const ReadyOriginalMatrix &,const void *,void *opaque){auto &o=*static_cast<Ops *>(opaque);++o.verified;return o.scenario!="byte-proof";}
};
Ops *Ops::current=nullptr;
struct Graph {
    Ops *ops;ReadyExpertWave *wave;ReadyExecutionMode mode;unsigned calls=0;
    static bool complete(ReadyGraphPhase phase,std::uint64_t,const std::array<bool,10>&selected,void *opaque) {
        auto &g=*static_cast<Graph *>(opaque);++g.calls;check(g.wave->snapshot().GPU_pending);
        for(unsigned i=0;i<10;++i)check(selected[i]==(phase==ReadyGraphPhase::complete_serial||phase==ReadyGraphPhase::original_reduction||
            (phase==ReadyGraphPhase::first_group?i%2==0:i%2==1)));
        if(g.ops->scenario=="GPU-refusal")return false;
        if(g.mode==ReadyExecutionMode::split_overlap&&phase==ReadyGraphPhase::first_group) {
            const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(3);
            while(g.wave->snapshot().role_returns!=30){check(std::chrono::steady_clock::now()<deadline);std::this_thread::yield();}
        }
        return true;
    }
};
int main(int argc,char **argv) {try {
    check(argc==3);std::ifstream f(argv[1]);std::string raw((std::istreambuf_iterator<char>(f)),{});const std::string scenario=argv[2];
    auto plan=parse_ready_original_plan(raw,sha256_metadata_bytes(raw));unsigned refused=0;
    const auto reject=[&](const Json &p,const std::string &hash="") {const auto text=p.dump();try{(void)parse_ready_original_plan(text,hash.empty()?sha256_metadata_bytes(text):hash);}
        catch(const std::exception &){++refused;return;}throw std::runtime_error("Altered original plan was admitted");};
    if(scenario=="parser") {
        const auto p=Json::parse(raw);
        for(const auto &key:{"schema","layer","experts","slots","files","matrices","lineage","origin"}){auto q=p;q.erase(key);reject(q);}
        for(const auto &value:Json::array({48u,-1,0.0,true})){auto q=p;q["layer"]=value;reject(q);}
        {auto q=p;q["experts"][1]=q["experts"][0];reject(q);q=p;q["slots"][1]=0u;reject(q);}
        for(const auto &key:{"source","offset","residue","raw","envelope"}){auto q=p;q["matrices"][0][key]=nullptr;reject(q);}
        {auto q=p;q["matrices"][1]=q["matrices"][0];reject(q);q=p;q["files"][0]["identity"][5]=1u;reject(q);q=p;q["files"][0]["path"]="/data/../unowned";reject(q);}
        reject(p,std::string(64,'0'));
#ifdef QWEN_READY_ORIGINAL_PLAN
        const auto *compiled=compiled_ready_original_plan();check(compiled&&compiled->sha256==plan.sha256&&compiled->experts==plan.experts&&compiled==compiled_ready_original_plan());
#else
        check(compiled_ready_original_plan()==nullptr);
#endif
        std::cout<<Json{{"passed",true},{"refusals",refused},{"PS5_operations",0},{"file_reads",0},{"GPU_calls",0}}.dump()<<'\n';return 0;
    }
    SplitBankBackings banks{};
    for(unsigned group=0;group<2;++group)for(unsigned role=0;role<3;++role)banks[group][role]={
        reinterpret_cast<void *>((group?0x20000000000ull:0x10000000000ull)+role*split_bank_planes[group]*padded_bank_stride),
        split_bank_planes[group]*padded_bank_stride,32,7,group?22u:11u};
    auto *wave=new ReadyExpertWave(plan.experts,plan.slots,validate_split_bank_backings(banks),plan.layer,1,7,26);
    auto *ops=new Ops(plan,scenario);ops->wave=wave;Ops::current=ops;const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
    auto *source=new ReadyOriginalSource(plan,banks,*ops,Ops::verify,ops,Ops::stage,deadline);auto *execution=new ReadyExpertExecution;
    const auto mode=scenario=="one-graph"?ReadyExecutionMode::one_graph_serial:scenario=="split-serial"?ReadyExecutionMode::split_serial:ReadyExecutionMode::split_overlap;
    Graph graphs{ops,wave,mode};const bool good=scenario=="one-graph"||scenario=="split-serial"||scenario=="split-overlap";
    try{execution->run(*wave,mode,ReadyOriginalSource::fill,source,{Graph::complete,&graphs},26,deadline);check(good);}
    catch(const std::exception &){if(good)throw;++refused;source->stop_new_work();execution->retain_and_join_returned_source(deadline);check(execution->snapshot().failed&&execution->snapshot().owners_must_be_retained);}
    if(good) {
        const auto report=source->completed_report();check(report.at("Direct_read_calls")==30&&report.at("two_call_batches")>0u&&
            wave->snapshot().unique_experts==10&&ops->reads==30&&ops->verified==30&&ops->peak==2&&ops->peak_fd<=8&&ops->descriptors.empty()&&ops->opens==ops->closes);
        check(ops->lease_reads==(mode==ReadyExecutionMode::split_overlap?15u:0u));delete source;
    }else {bool completed=false;try{(void)source->completed_report();completed=true;}catch(const std::runtime_error &){}check(!completed);}
    std::cout<<Json{{"passed",true},{"refusals",refused},{"metadata_reads",ops->reads},{"peak_two_call_depth",ops->peak},{"peak_descriptor_cache",ops->peak_fd},
        {"reads_during_metadata_GPU_lease",ops->lease_reads},{"PS5_operations",0},{"file_reads",0},{"GPU_calls",0}}.dump()<<'\n';
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}

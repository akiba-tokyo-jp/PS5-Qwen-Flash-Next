// SPDX-License-Identifier: MIT
#include "metadata_memory_probe.h"
#include "metadata_memory_policy.h"
#include <fstream>
#include <functional>
#include <iostream>
using Probe=qwen_app::MetadataMemoryProbe;
static Probe::Sample sample() {
    Probe::Sample s;s.memory={435159040,16384,138739,4000,898,2974,206};
    s.monotonic_ns=1;s.heap_mapped=32u<<20;s.heap_peak=20u<<20;return s;
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    std::ifstream input(argv[1]);const auto policy=nlohmann::json::parse(input);
    qwen_app::require_metadata_memory_policy(policy);
    unsigned refused=0;
    const auto reject=[&](const std::function<void()> &f){try{f();return false;}catch(...){++refused;return true;}};
    Probe full;full.enable();
    for(std::size_t i=0;i<Probe::capacity;++i) {
        auto s=sample();s.monotonic_ns+=i;s.direct_reads=i/5;s.direct_bytes=s.direct_reads*(1u<<20);
        full.record(i/5,i%5,s);
    }
    if(!full.complete()||full.size()!=380||!reject([&]{full.record(76,0,sample());})||full.complete())return 3;
    if(!reject([&]{Probe p;p.record(0,0,sample());})||!reject([&]{Probe p;p.enable();p.enable();})||
       !reject([&]{Probe p;p.enable();p.record(0,1,sample());})||
       !reject([&]{Probe p;p.enable();auto s=sample();s.memory.kernel_free=1153;p.record(0,0,s);})||
       !reject([&]{Probe p;p.enable();auto s=sample();s.monotonic_ns=0;p.record(0,0,s);})||
       !reject([&]{Probe p;p.enable();auto s=sample();s.direct_bytes=513ull<<20;p.record(0,0,s);})||
       !reject([&]{Probe p;p.enable();auto s=sample();s.monotonic_ns=2;p.record(0,0,s);p.record(0,1,sample());})||
       !reject([&]{Probe p;p.enable();auto s=sample();s.direct_reads=1;p.record(0,0,s);p.record(0,1,sample());})||
       !reject([&]{Probe p;p.enable();p.at(0);}))return 4;
    const auto bad_policy=[&](const std::function<void(nlohmann::json &)> &edit) {
        auto p=policy;edit(p);return reject([&]{qwen_app::require_metadata_memory_policy(p);});
    };
    for(auto it=policy.at("native_metadata_memory_diagnostic").begin();it!=policy.at("native_metadata_memory_diagnostic").end();++it)
        if(!bad_policy([&](auto &p){p["native_metadata_memory_diagnostic"].erase(it.key());}))return 5;
    for(const char *key:{"maximum_files","phases_per_file","maximum_records","GPU_calls","virtual_source_calls"})
        if(!bad_policy([&](auto &p){p["native_metadata_memory_diagnostic"][key]=1.0;}))return 6;
    for(const char *key:{"native_prefix_validation","native_model_checkpoint_validation","native_source_stage_memory_diagnostic"})
        if(!bad_policy([&](auto &p){p[key]=nlohmann::json::object();}))return 7;
    if(!bad_policy([](auto &p){p.erase("native_direct_metadata");})||
       !bad_policy([](auto &p){p.erase("native_source_schedule");})||
       !bad_policy([](auto &p){p["native_metadata_memory_diagnostic"]["CPU_only"]=false;})||
       !bad_policy([](auto &p){p["native_metadata_memory_diagnostic"]["extra"]=true;}))return 8;
    std::cout<<"{\"all_380_records_exact\":true,\"refusals\":"<<refused<<",\"fixed_storage_bytes\":"<<sizeof(Probe)<<",\"PS5_operations\":0}"<<std::endl;
}

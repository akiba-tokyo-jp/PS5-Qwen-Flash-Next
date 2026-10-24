// SPDX-License-Identifier: MIT
// The actual patched cache upload loop with synchronous-lifetime API doubles.
#include "mapped_source_bridge.h"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>
static void check(bool ok,const char * message) { if(!ok)throw std::runtime_error(message); }
struct ggml_tensor { void * data; std::size_t nb[3]; std::size_t bytes; };
struct Fill { int expert,slot; };
struct Layer { std::vector<ggml_tensor *> experts; };
struct Group { std::vector<ggml_tensor *> banks; };
static std::array<unsigned char,8u<<20> window;
static bool enabled=true,leased=false;
static unsigned pairs=0,completions=0,writes=0,async_writes=0,syncs=0,lease_writes=0,throw_at=0;
static void reset(bool on) { enabled=on;leased=false;pairs=completions=writes=async_writes=syncs=lease_writes=throw_at=0; }
extern "C" bool qwen_app_model_source_pair_enabled(std::size_t bytes) { return enabled&&bytes&&bytes<=(4u<<20)-16384; }
extern "C" void qwen_app_model_source_pair(const void * first,const void * second,std::size_t bytes,const void ** result) {
    check(!leased&&enabled&&syncs>pairs,"A source pair was unqualified, unsynchronized or reused early");
    leased=true;lease_writes=0;++pairs;
    std::memcpy(window.data(),first,bytes);std::memcpy(window.data()+(4u<<20),second,bytes);
    result[0]=window.data();result[1]=window.data()+(4u<<20);
}
extern "C" void qwen_app_model_source_chunk_completed() {
    check(leased&&lease_writes==2,"Pair published before both consumers completed");
    leased=false;++completions;
}
static void ggml_backend_synchronize(int) { check(!leased,"Synchronization attempted after source reuse");++syncs; }
static void ggml_backend_tensor_set(ggml_tensor * bank,const void * source,std::size_t offset,std::size_t bytes) {
    check(leased&&offset<=bank->bytes&&bytes<=bank->bytes-offset,"An invalid synchronous cache write occurred");
    check(source==window.data()||source==window.data()+(4u<<20),"The paired write lost its owned window");
    if(++writes==throw_at)throw std::runtime_error("Injected synchronous consumer failure");
    std::memcpy(static_cast<unsigned char *>(bank->data)+offset,source,bytes);++lease_writes;
}
static void ggml_backend_tensor_set_async(int,ggml_tensor * bank,const void * source,std::size_t offset,std::size_t bytes) {
    check(!leased&&offset<=bank->bytes&&bytes<=bank->bytes-offset,"A paired window escaped to deferred async copy");
    std::memcpy(static_cast<unsigned char *>(bank->data)+offset,source,bytes);++async_writes;
}
#include "actual_paired_cache_loop.h"
int main() {
    try {
        const std::vector<Fill> fills{{2,1},{5,3},{9,7},{10,8},{50,0}};
        for(auto size:{std::size_t(37),std::size_t(16384)})for(bool on:{false,true}) {
            reset(on);
            std::array<std::vector<unsigned char>,3> weights,banks;
            std::array<ggml_tensor,3> sources{},destinations{};Layer layer;Group group;
            for(unsigned role=0;role<3;++role) {
                weights[role].resize(512*size);banks[role].assign(53*size,0xcc);
                for(std::size_t i=0;i<weights[role].size();++i)weights[role][i]=(i*17+7*role)%251;
                sources[role]={weights[role].data(),{0,0,size},weights[role].size()};
                destinations[role]={banks[role].data(),{0,0,size},banks[role].size()};
                layer.experts.push_back(&sources[role]);group.banks.push_back(&destinations[role]);
            }
            check(actual_cache_upload_loop(1,layer,group,fills)==3*5*size,"Expert upload byte accounting changed");
            for(unsigned role=0;role<3;++role)for(unsigned slot=0;slot<53;++slot) {
                int expert=-1;for(const auto & fill:fills)if(fill.slot==int(slot))expert=fill.expert;
                for(std::size_t i=0;i<size;++i)
                    check(banks[role][slot*size+i]==(expert<0?0xcc:weights[role][expert*size+i]),
                        "Actual cache loop changed expert bits or an unselected slot");
            }
            check(!leased&&pairs==completions,"The cache loop leaked a consumed source lease");
            if(on)check(pairs==3&&writes==6&&async_writes==6,"Paired/contiguous/odd paths were not all exercised");
            else check(!pairs&&async_writes==12,"The unpaired control path changed");
        }
        for(unsigned fail:{1u,2u}) {
            reset(true);throw_at=fail;
            std::vector<unsigned char> weights(512*37),bank(53*37);
            ggml_tensor source{weights.data(),{0,0,37},weights.size()},destination{bank.data(),{0,0,37},bank.size()};
            bool threw=false;
            try {actual_cache_upload_loop(1,Layer{{&source}},Group{{&destination}},fills);}
            catch(const std::runtime_error &){threw=true;}
            check(threw&&leased&&pairs==1&&!completions&&writes==fail&&!async_writes,
                "Failed consumer released backing, retried, or submitted another upload");
        }
        std::cout<<"Actual cache-loop byte parity, contiguous/odd/control paths and retained failed consumers passed\n";
    } catch(const std::exception & error){std::cerr<<error.what()<<'\n';return 1;}
}

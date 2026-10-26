// SPDX-License-Identifier: MIT
#include "device_state_admission.h"
#if defined(QWEN_DEVICE_STATE_FIXTURE) && QWEN_DEVICE_STATE_FIXTURE
#include "direct_integrity.h"
#include "device_buffer_budget.h"
#include "mapped_source_bridge.h"
#include "mapped_source.h"
#include "system_memory.h"
#include "native_gpu.h"
#include "profile_clock.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "llama.h"
#include "llama-context.h"
#include "llama-io.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <cstdlib>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
// Produced from exactly the source qualified by the host fixture. A private
// namespace avoids changing the linked engine's existing state-copy classes.
#include "native_device_state_io.inc"
extern "C" {
void qwen_native_stage(const char *);
void qwen_native_driver_checkpoint();
}
namespace qwen_app { namespace {
using namespace qwen_device_state_fixture;
constexpr std::size_t page=16384,window_bytes=2u<<20;
void check(bool value,const char *message){if(!value)throw std::runtime_error(message);}
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now().time_since_epoch()).count();}
SourceIdentity identity(int fd) {
    struct stat s{};check(!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_ino&&s.st_size>0,"Device-state source identity refused");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
std::uint32_t pattern(std::uint64_t index,unsigned seed){return 0x3f000001u+std::uint32_t((index*37+(index>>7)*13+seed)%0x700000u);}
struct Fixture {
    ggml_backend_t backend=nullptr;ggml_context *ctx=nullptr;ggml_backend_buffer_t original=nullptr;
    ggml_tensor *root=nullptr,*state=nullptr;llama_memory_buffers storage;
    std::array<std::uint32_t,window_bytes/4> window{};
    std::array<std::uint8_t,16> metadata{};std::uint64_t started=0;unsigned checked=0;
    void boundary(){check(now()-started<120000000000ull,"Device-state finite deadline exceeded; owners retained");(void)admit_native_system_memory();}
    void complete(){ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();boundary();}
    void fill(unsigned seed) {
        for(std::uint64_t offset=0;offset<device_state_fixture_bytes;offset+=window_bytes) {
            boundary();const auto bytes=std::min<std::uint64_t>(window_bytes,device_state_fixture_bytes-offset);
            for(std::size_t i=0;i<bytes/4;++i)window[i]=pattern(offset/4+i,seed);
            ggml_backend_tensor_set(state,window.data(),offset,bytes);
        }
        complete();
    }
    void verify(unsigned seed) {
        for(std::uint64_t offset=0;offset<device_state_fixture_bytes;offset+=window_bytes) {
            boundary();const auto bytes=std::min<std::uint64_t>(window_bytes,device_state_fixture_bytes-offset);
            ggml_backend_tensor_get(state,window.data(),offset,bytes);
            for(std::size_t i=0;i<bytes/4;++i)check(window[i]==pattern(offset/4+i,seed),"Device checkpoint did not restore original F32 bits");
        }
        for(const auto offset:{std::uint64_t(0),device_state_fixture_bytes+page}) {
            ggml_backend_tensor_get(root,window.data(),offset,page);
            for(std::size_t i=0;i<page/4;++i)check(window[i]==0xa7a7a7a7u,"Device-state source-view canary changed");
        }
        ++checked;complete();
    }
    void save(bool split,unsigned seed) {
        boundary();fill(seed);qwen_native_stage("device_state_before_capture owners_pinned=1");
        {
            llama_io_write_device writer(metadata.data(),metadata.size(),storage);
            const std::uint32_t header[4]={0xaf143cd8,0,29,53};writer.write(header,8);
            const auto half=device_state_fixture_bytes/2;
            writer.write_tensor(state,0,split?half:device_state_fixture_bytes);
            if(split)writer.write_tensor(state,half,half);
            writer.write(header+2,8);check(writer.n_bytes()==metadata.size(),"Device-state metadata size differs");
        }
        complete();qwen_native_stage("device_state_capture_copies_completed owners_pinned=1");
        check(storage.size()==1&&storage.begin()->second.total_size==device_state_fixture_bytes&&storage.begin()->second.buf,
            "Device-state saved allocation scope differs");
    }
    void restore(unsigned pieces,bool discard) {
        boundary();qwen_native_stage("device_state_before_restore owners_pinned=1");
        {
            llama_io_read_device reader(metadata.data(),metadata.size(),storage);std::uint32_t header[4]{};reader.read(header,8);
            std::uint64_t offset=0;
            for(unsigned i=0;i<pieces;++i) {
                const auto remaining=device_state_fixture_bytes-offset;
                const auto bytes=i+1==pieces?remaining:(remaining/(pieces-i)/page)*page;
                check(bytes&&bytes%4==0,"Device-state restore partition refused");reader.read_tensor(state,offset,bytes);offset+=bytes;
            }
            reader.read(header+2,8);check(reader.n_bytes()==metadata.size()&&header[0]==0xaf143cd8&&header[1]==0&&header[2]==29&&header[3]==53,
                "Device-state metadata roundtrip differs");if(discard)reader.discard();
        }
        complete();qwen_native_stage(discard?"device_state_restore_discarded_without_copy":"device_state_restore_copies_completed owners_pinned=1");
    }
};
} // namespace
bool device_state_fixture_linked(){return true;}
nlohmann::json admit_device_state_fixture(const nlohmann::json &policy,const std::string &journal) {
    require_device_state_policy(policy,false);const auto &p=policy.at("native_device_state_validation");const auto &source=p.at("source");
    (void)admit_native_startup_memory();
    auto *f=new Fixture;f->started=now();
    const auto path=source.at("path").get<std::string>();verify_native_startup_file_direct(path,source.at("bytes"),source.at("sha256"),30);
    const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);check(fd>=0,"Device-state source owner unavailable");
    const auto original_identity=identity(fd);check(original_identity[5]==source.at("bytes"),"Device-state source size differs");
    start_native_model_sources({{path,original_identity[5],original_identity}});
    for(const auto *name:{"GGML_VK_BOUNDED_STAGING","GGML_VK_DISABLE_ASYNC","GGML_VK_SERIALIZE_SUBMISSIONS","GGML_VK_MAX_NODES_PER_SUBMIT"})
        check(!setenv(name,"1",1),"Device-state requires the qualified serialized Vulkan policy");
    (void)admit_native_startup_memory();qwen_native_gpu_initialize(journal.c_str());qwen_native_driver_begin();
    llama_backend_init();enforce_native_model_compute_limits();f->backend=ggml_backend_vk_init(0);check(f->backend,"Device-state backend unavailable");
    ggml_init_params params{};params.no_alloc=true;params.mem_size=4*ggml_tensor_overhead();f->ctx=ggml_init(params);check(f->ctx,"Device-state metadata refused");
    f->root=ggml_new_tensor_1d(f->ctx,GGML_TYPE_F32,(device_state_fixture_bytes+2*page)/4);
    f->state=ggml_view_1d(f->ctx,f->root,device_state_fixture_bytes/4,page);
    f->original=ggml_backend_alloc_ctx_tensors(f->ctx,f->backend);check(f->original,"Device-state source allocation refused");
    check(ggml_backend_buffer_get_size(f->original)<=140ull<<20,"Device-state source allocation exceeds priced bound");
    f->complete();std::fill(f->window.begin(),f->window.end(),0xa7a7a7a7u);
    ggml_backend_tensor_set(f->root,f->window.data(),0,page);ggml_backend_tensor_set(f->root,f->window.data(),device_state_fixture_bytes+page,page);f->complete();
    nlohmann::json cases=nlohmann::json::array();
    for(unsigned n=0;n<8;++n) {
        const bool split=n%2==0,discard=n==7;const unsigned pieces=1+n%3,seed=17+n;
        const auto previous=f->storage.empty()?nullptr:f->storage.begin()->second.buf.get();
        f->save(split,seed);const auto held=f->storage.begin()->second.buf.get();
        check(!previous||previous==held,"Same-size device snapshot unexpectedly replaced its buffer");
        f->fill(91+n);f->restore(pieces,discard);f->verify(discard?91+n:seed);
        check(f->storage.begin()->second.buf.get()==held,"Device-state restore replaced its pinned saved owner");
        cases.push_back({{"case",n},{"capture_pieces",split?2:1},{"restore_pieces",pieces},{"discard",discard},{"F32_bits_exact",true},{"canaries_intact",true}});
        qwen_native_stage("device_state_case_exact_and_positive_completion");
    }
    f->complete();f->storage.clear();f->complete();
    ggml_backend_buffer_free(f->original);ggml_free(f->ctx);ggml_backend_free(f->backend);qwen_native_driver_checkpoint();
    check(identity(fd)==original_identity&&!close(fd),"Device-state source identity or close refused");stop_native_model_sources();
    const auto ledger=native_model_device_stats();check(!ledger.live,"Device-state backing remains live");
    check(f->checked==8,"Device-state cohort incomplete");
    const auto result=nlohmann::json{{"schema","ps5-qwen-device-state-fixture-result-v1"},{"cases",cases},
        {"state_bytes",device_state_fixture_bytes},{"all_F32_bits_exact",true},{"canaries_intact",true},
        {"all_copy_owners_retired",true},{"device_ledger_peak_bytes",ledger.peak},{"device_ledger_live_bytes",ledger.live},
        {"source_IO_completed_and_worker_stopped",true},{"CPU_transfer_window_bytes",window_bytes},{"host_full_state_payload_allocated",false},
        {"model_loaded",false},{"model_state_completeness_qualified",false},{"queue_submission_count_not_inferred",true}};
    delete f;return result;
}
}
#else
namespace qwen_app {
bool device_state_fixture_linked(){return false;}
nlohmann::json admit_device_state_fixture(const nlohmann::json &,const std::string &){throw std::runtime_error("Device-state fixture inputs are not linked");}
}
#endif

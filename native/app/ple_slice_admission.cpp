// SPDX-License-Identifier: MIT
#include "ple_slice_admission.h"
#include "ple_convolution_graph.h"
#include "device_buffer_budget.h"
#include "mapped_source.h"
#include "mapped_source_bridge.h"
#include "native_gpu.h"
#include "profile_clock.h"
#include "direct_integrity.h"
#include "system_memory.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "llama.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>
extern "C" void qwen_native_stage(const char *);
namespace qwen_app { namespace {
using Json=nlohmann::json;
struct SourceAdmission {bool attempted=false,ready=false,consumed=false;std::thread::id producer;std::string binding;};
SourceAdmission source_admission;
constexpr std::size_t channels=PLE_fixture_channels,guard=PLE_fixture_guard,maximum_payload=PLE_fixture_payload_cap;
void check(bool ok,const char *text){if(!ok)throw std::runtime_error(text);}
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now().time_since_epoch()).count();}
struct PLEFixture {
    ggml_backend_t backend=nullptr;ggml_context *context=nullptr;ggml_backend_buffer_t buffer=nullptr;
    ggml_tensor *history_root=nullptr,*kernel_root=nullptr;
    std::array<ggml_tensor *,4> outputs{};std::array<ggml_cgraph *,4> graphs{};
    std::array<std::uint64_t,4> construction_ns{};
    std::array<unsigned,4> copy_nodes{};
    std::vector<unsigned char> history,kernel,readback;
    std::vector<float> reference;
    unsigned tokens=0,completed_graphs=0;double maximum_error=0;
    const std::thread::id producer=std::this_thread::get_id();
    void prepare(ggml_backend_t active,unsigned width) {
        check(active&&ggml_backend_is_vk(active)&&width>=1&&width<=4,"PLE fixture requires one actual Vulkan backend");
        backend=active;tokens=width;
        history.assign(2*guard+(9+tokens)*channels*4,0xa7);kernel.assign(2*guard+4*channels*2,0xa7);
        readback.resize(2*guard+tokens*channels*4);
        for(std::size_t i=0;i<(9+tokens)*channels;++i) {
            const float value=float(int(i%97)-48)/12288.0f;std::memcpy(history.data()+guard+i*4,&value,4);
        }
        for(std::size_t i=0;i<4*channels;++i) {
            const std::uint16_t bits=std::uint16_t((i&1?0x8000:0)|0x3b00|((i*37)%1024));
            std::memcpy(kernel.data()+guard+i*2,&bits,2);
        }
        context=ggml_init({PLE_fixture_context_bytes(),nullptr,true});
        check(context,"PLE fixture metadata allocation refused");
        history_root=ggml_new_tensor_1d(context,GGML_TYPE_F32,history.size()/4);
        kernel_root=ggml_new_tensor_1d(context,GGML_TYPE_BF16,kernel.size()/2);
        auto *padded=ggml_view_3d(context,history_root,9+tokens,channels,1,(9+tokens)*4,(9+tokens)*channels*4,guard);
        auto *weights=ggml_view_2d(context,kernel_root,4,channels,8,guard);
        ggml_set_input(history_root);ggml_set_input(kernel_root);
        for(unsigned mode=0;mode<4;++mode) {
            const auto begin=now();
            const auto built=build_PLE_convolution_fixture(context,padded,weights,tokens,static_cast<PLESliceMode>(mode));
            outputs[mode]=built.output_root;graphs[mode]=built.graph;copy_nodes[mode]=built.CONT_nodes;
            construction_ns[mode]=now()-begin;
            for(int i=0;i<ggml_graph_n_nodes(graphs[mode]);++i) {
                auto *node=ggml_graph_node(graphs[mode],i);
                check(ggml_backend_dev_supports_op(ggml_backend_get_device(backend),node),"PLE graph operation is unsupported before device allocation");
            }
            check(copy_nodes[mode]==8-4*unsigned(bool(mode&1))-4*unsigned(bool(mode&2)),"PLE graph copy count changed");
        }
        buffer=ggml_backend_alloc_ctx_tensors(context,backend);check(buffer,"PLE fixture device allocation refused");
        check(ggml_backend_buffer_get_size(buffer)<=maximum_payload,"PLE fixture exceeds its bounded payload allocation");
        ggml_backend_tensor_set(history_root,history.data(),0,history.size());ggml_backend_tensor_set(kernel_root,kernel.data(),0,kernel.size());
        std::fill(readback.begin(),readback.end(),0xa7);
        for(auto *out:outputs)ggml_backend_tensor_set(out,readback.data(),0,readback.size());
        ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();
    }
    double expected(unsigned channel,unsigned token)const {
        double sum=0;
        for(unsigned k=0;k<4;++k) {
            float input,weight;std::uint16_t b;
            std::memcpy(&input,history.data()+guard+4*(channel*(9+tokens)+k*3+token),4);
            std::memcpy(&b,kernel.data()+guard+2*(channel*4+k),2);
            const std::uint32_t bits=std::uint32_t(b)<<16;std::memcpy(&weight,&bits,4);sum+=double(input)*weight;
        }
        return sum/(1.0+std::exp(-sum));
    }
    std::uint64_t run(unsigned mode) {
        check(std::this_thread::get_id()==producer&&mode<4,"PLE fixture GPU producer changed");
        (void)admit_native_system_memory();
        const auto binding=" width="+std::to_string(tokens)+" mode="+std::to_string(mode)+" ordinal="+std::to_string(completed_graphs+1);
        qwen_native_stage(("PLE_fixture_graph_before"+binding+" GPU_backing_pinned=1").c_str());
        const auto begin=now();
        check(ggml_backend_graph_compute(backend,graphs[mode])==GGML_STATUS_SUCCESS,"PLE graph failed; all backing retained");
        ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();
        ggml_backend_tensor_get(outputs[mode],readback.data(),0,readback.size());qwen_native_driver_checkpoint();
        const auto end=now();check(end>begin&&end-begin<=120000000000ull,"PLE fixture graph clock refused");
        const auto elapsed=end-begin;
        qwen_native_stage(("PLE_fixture_graph_and_readback_returned"+binding+" elapsed_ns="+std::to_string(elapsed)+" GPU_completion_checked=1").c_str());
        for(unsigned i=0;i<guard;++i)check(readback[i]==0xa7&&readback[readback.size()-1-i]==0xa7,"PLE output canary changed");
        if(reference.empty())reference.resize(tokens*channels);
        for(unsigned token=0;token<tokens;++token)for(unsigned channel=0;channel<channels;++channel) {
            const auto index=token*channels+channel;float actual;std::memcpy(&actual,readback.data()+guard+index*4,4);
            const auto ref=expected(channel,token),error=std::abs(double(actual)-ref);
            check(std::isfinite(actual)&&error<=1e-5+1e-5*std::abs(ref),"PLE F64 convolution reference differs");
            maximum_error=std::max(maximum_error,error);
            if(!completed_graphs)reference[index]=actual;
            else check(!std::memcmp(reference.data()+index,&actual,4),"PLE original/candidate F32 convolution bits differ");
        }
        ++completed_graphs;return elapsed;
    }
    void close_completed() {
        ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();
        std::vector<unsigned char> original(history.size());ggml_backend_tensor_get(history_root,original.data(),0,original.size());
        check(original==history,"PLE original F32 history or input canaries changed");
        original.resize(kernel.size());ggml_backend_tensor_get(kernel_root,original.data(),0,original.size());
        check(original==kernel,"PLE original BF16 kernel or input canaries changed");
        ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();
        ggml_backend_buffer_free(buffer);ggml_free(context);qwen_native_driver_checkpoint();
        buffer=nullptr;context=nullptr;
    }
};
}
void prepare_PLE_source_owner(const Json &policy) {
    require_PLE_slice_policy(policy,false);
    check(!source_admission.attempted,"PLE source owner cannot prepare twice or retry");
    source_admission.attempted=true;source_admission.producer=std::this_thread::get_id();
    source_admission.binding=Json::array({policy.at("native_PLE_slice_validation"),policy.at("native_shader_storage")}).dump();
    const bool explicit_source=PLE_slice_explicit_source(policy);
    const auto &file=explicit_source?policy.at("native_PLE_slice_validation").at("source_guard"):
        policy.at("native_shader_storage").at("external_file");
    const auto path=file.at("path").get<std::string>();
    const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);check(fd>=0,"PLE fixture source guard descriptor refused");
    struct stat s{};check(!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_size>0&&std::uint64_t(s.st_size)==file.at("bytes"),"PLE fixture source guard identity differs");
    const std::array<std::uint64_t,10> identity{{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
        std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),
        std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)}};
    require_PLE_source_identity(identity,file.at("bytes").get<std::uint64_t>());
    check(!close(fd),"PLE fixture source guard descriptor close refused");
    if(explicit_source) {
        qwen_native_stage("PLE_source_whole_integrity_before_GPU_not_started");
        verify_native_startup_file_direct(path,file.at("bytes").get<std::uint64_t>(),file.at("sha256").get<std::string>(),30);
        qwen_native_stage("PLE_source_whole_integrity_returned_GPU_not_started");
    }
    start_native_model_sources({{path,identity[5],identity}});
    const auto source=native_model_source_stats();
    check(source.physical_read_calls==2&&!source.worker_read_ns,"PLE CPU source preflight did not return its two bounded reads");
    source_admission.ready=true;
    qwen_native_stage("PLE_source_owner_CPU_preflight_completed_GPU_not_started");
}
Json admit_PLE_slice_fixture(const Json &policy,const std::string &journal) {
    require_PLE_slice_policy(policy,false);
    check(!PLE_slice_CPU_bootstrap(policy),"CPU-only shader bootstrap cannot initialize a GPU fixture");
    const bool smoke=PLE_slice_smoke(policy),explicit_source=PLE_slice_explicit_source(policy);
    check(qwen_native_gpu_frontend_linked()&&ggml_app_bounded_device_buffers_hooks()&&ggml_app_bounded_workspace_hooks(),
        "PLE fixture requires the actual native frontend and bounded device/workspace hooks");
    check(!setenv("MESA_SHADER_CACHE_DISABLE","true",1),"PLE fixture requires disabled persistent caches");
    for(const auto *key:{"GGML_VK_BOUNDED_STAGING","GGML_VK_DISABLE_ASYNC","GGML_VK_SERIALIZE_SUBMISSIONS","GGML_VK_MAX_NODES_PER_SUBMIT"})
        check(!setenv(key,"1",1),"PLE fixture requires the existing serialized Vulkan profile");
    if(!source_admission.attempted)prepare_PLE_source_owner(policy);
    check(source_admission.ready&&!source_admission.consumed&&source_admission.producer==std::this_thread::get_id()&&
        source_admission.binding==Json::array({policy.at("native_PLE_slice_validation"),policy.at("native_shader_storage")}).dump(),"PLE requires its exact completed CPU source owner");
    source_admission.consumed=true;
    (void)admit_native_startup_memory();qwen_native_gpu_initialize(journal.c_str());qwen_native_driver_begin();
    llama_backend_init();enforce_native_model_compute_limits();
    auto *backend=ggml_backend_vk_init(0);check(backend&&ggml_backend_is_vk(backend),"PLE Vulkan backend unavailable");
    Json widths=Json::array();unsigned total_graphs=0;double maximum_error=0;const auto begun=now();
    for(unsigned width=1;width<=(smoke?1u:4u);++width) {
        check(now()-begun<120000000000ull,"PLE finite cohort deadline exceeded before preparation");
        // Raw ownership deliberately survives exceptions. The ordinary OS close
        // remains responsible for all failed or unknown GPU/resource completion.
        auto *f=new PLEFixture;f->prepare(backend,width);Json batches=Json::array(),warmups=Json::array();
        for(unsigned mode=0;mode<4;++mode) {
            check(now()-begun<120000000000ull,"PLE finite cohort deadline exceeded; backing retained");
            warmups.push_back({{"mode",mode},{"ordinal",mode+1},{"graph_completion_and_readback_ns",f->run(mode)}});
        }
        for(unsigned candidate=1;candidate<=3;++candidate)for(unsigned round=0;round<(smoke?0u:8u);++round)for(unsigned arm=0;arm<2;++arm) {
            check(now()-begun<120000000000ull,"PLE finite cohort deadline exceeded; backing retained");
            const unsigned mode=(round+arm)%2?candidate:0;
            const auto ordinal=f->completed_graphs+1;const auto elapsed=f->run(mode);
            batches.push_back({{"candidate",candidate},{"round",round},{"mode",mode},{"ordinal",ordinal},{"graph_completion_and_readback_ns",elapsed}});
        }
        check(f->completed_graphs==(smoke?4u:52u),"PLE width cohort is incomplete");
        f->close_completed();total_graphs+=f->completed_graphs;maximum_error=std::max(maximum_error,f->maximum_error);
        widths.push_back({{"tokens",width},{"graph_construction_ns",f->construction_ns},{"CONT_nodes",f->copy_nodes},{"warmups",warmups},{"batches",batches},
            {"raw_device_buffer_cap_bytes",maximum_payload},{"all_operations_on_single_Vulkan_backend",true}});
        delete f;
    }
    ggml_backend_free(backend);qwen_native_driver_checkpoint();const auto ledger=native_model_device_stats();
    check(total_graphs==(smoke?4u:208u)&&!ledger.live,"PLE fixture GPU/ledger cohort did not complete");
    const auto source=native_model_source_stats();stop_native_model_sources();
    return {{"schema",smoke?"ps5-qwen-PLE-slice-smoke-v1":explicit_source?"ps5-qwen-PLE-slice-paired-fixture-v2":"ps5-qwen-PLE-slice-fixture-v1"},{"widths",widths},{"GPU_graphs",total_graphs},
        {"maximum_absolute_error",maximum_error},{"F64_reference_passed",true},{"all_F32_outputs_bit_exact",true},
        {"input_and_output_canaries_intact",true},{"original_BF16_to_F32_casts_preserved",true},
        {"timed_scope","graph_compute_synchronization_driver_checkpoints_and_output_readback"},
        {"graph_construction_measured_separately",true},{"common_final_output_copy_in_all_arms",true},
        {"numerical_data","deterministic_original_shapes_not_model_weights"},{"device_ledger_peak_bytes",ledger.peak},
        {"device_ledger_live_bytes",ledger.live},{"model_loaded",false},{"source_preflight_read_calls",source.physical_read_calls},
        {"source_preflight_read_bytes",source.physical_read_bytes},{"existing_source_scratch_bytes",model_read_window},
        {"source_worker_read_ns",source.worker_read_ns},
        {"source_guard_current_full_SHA256_checked",explicit_source},{"source_guard_bytes_not_used_for_numerics",true},
        {"driver_final_epoch_retirement_requires_caller",true}};
}
}

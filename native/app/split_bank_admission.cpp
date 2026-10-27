// SPDX-License-Identifier: MIT
#include "split_bank_admission.h"
#include "split_bank_allocation.h"
#include "padded_bank_layout.h"
#include "indexed_vector.h"
#include "device_buffer_budget.h"
#include "direct_integrity.h"
#include "mapped_source.h"
#include "system_memory.h"
#include "native_gpu.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
#include "llama.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_native_stage(const char *);
}
namespace qwen_app {namespace {
using Json=nlohmann::json;
using Identity=std::array<std::uint64_t,10>;
void check(bool good,const char *message){if(!good)throw std::runtime_error(message);}
Identity identity(int fd) {
    struct stat s{};check(!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_ino&&s.st_size==split_bank_pack_bytes&&!(s.st_mode&0022),"Split original pack identity refused");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
std::string digest(const void *data,std::size_t bytes) {
    sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char *>(data),bytes);
    unsigned char raw[32];sha256_final(&h,raw);std::string text;
    for(const auto b:raw){text+="0123456789abcdef"[b>>4];text+="0123456789abcdef"[b&15];}return text;
}
struct Matrix {std::uint64_t offset;unsigned residue;const char *raw,*envelope;};
// Original vector-bank group zero: layer zero, experts 0 and 257. The paired
// roles are gate, up, down, matching the existing qualified pack's byte hashes.
constexpr std::array<Matrix,6> matrices{{
    {4210688,2784,"d078e826bc9af5874b09a11d72da5afd1ef0ea526c92afb0823c21b2343ccf94","a7860aefe9ada5e7abc8f7ee60208534dd382779a1670e06e4f5981d70750078"},
    {14090240,2784,"9d5c49abe64e05751aafa4f9db91682c77a71fee414f09dfc08a605961e847ce","93d0b3f9b5cb7161388be0b6b8292395b1ce3d101e09aef4ab9d46252850b776"},
    {7503872,2784,"ae84d1de690d0a627967c7b8a108062428605b2a111105e4ec689ddef16842dc","2c5ce2fdbaf299e0ce254332ade85ea280aeb47136e497b090afa4d27f87701a"},
    {17383424,2784,"bc51fe9700a6c80b16f6a131aa358d55f1a67cb533436517f41a66d9b4d97418","0ff87036f608eb3c96d09355432c1eaf87aad5591a404ce8e73dd68c9671d25a"},
    {10797056,1632,"31f2e953692f1784b76a50761146b28394f0a768f5f0e0da3ff55aa374660ddc","9c473d2fbc2a25045c5db2fcf1bcd70c21002983773b14de7570a55faf75368b"},
    {20676608,1632,"a5949679890a798b9df50a2c1c77a75475b0ec6efcea3de02f39eaeac9e98656","f62d473879d8a482e03f3d5cece08d06cacd3b13ed5d0a94e55175ed5ada23af"}
}};
struct Fixture {
    ggml_backend_t backend=nullptr;int fd=-1;Identity source{};
    SplitBankAllocation allocation;unsigned reads=0,graphs=0;std::uint64_t non_exact=0;
    double maximum_error=0,maximum_normalized_error=0;Json cases=Json::array();
    const std::chrono::steady_clock::time_point deadline=std::chrono::steady_clock::now()+std::chrono::seconds(120);
    void bounded(){check(std::chrono::steady_clock::now()<deadline,"Split backing finite deadline exceeded; owners retained");(void)admit_native_system_memory();}
    static int use(const SplitBankBackings &banks,const SplitBankRoots &roots,void *opaque) {
        static_cast<Fixture *>(opaque)->run(banks,roots);return 0;
    }
    void verify(const unsigned char *base,const Matrix &m) {
        check(digest(base,padded_bank_stride)==m.envelope&&digest(base+m.residue,bank_expert_bytes)==m.raw,"Split original BF16 envelope or matrix differs");
    }
    void run(const SplitBankBackings &banks,const SplitBankRoots &roots) {
        const auto owners=validate_split_bank_backings(banks);check(owners[0][0]!=owners[1][0],"Split actual group owners alias");
        const auto alignment=banks[0][0].descriptor_alignment;
        for(const auto &group:banks)for(const auto &bank:group)check(bank.descriptor_alignment==alignment,"Split descriptor alignments differ");
        configure_padded_index_layout(true,alignment);configure_bf16_indexed_vector(true);set_bf16_indexed_vector_scope(true);
        ggml_init_params params{};params.no_alloc=true;params.mem_size=ggml_tensor_overhead()*90+6*ggml_graph_overhead_custom(16,false);
        auto *ctx=ggml_init(params);check(ctx,"Split graph metadata allocation refused");
        std::array<std::array<ggml_tensor *,3>,2> inputs{},ids{},outputs{};
        std::array<std::array<ggml_cgraph *,3>,2> graph{};
        for(unsigned group=0;group<2;++group)for(unsigned role=0;role<3;++role) {
            const auto k=role==2?640:2560,n=role==2?2560:640;const auto &m=matrices[role*2+group];
            // Tensor storage uses all physical planes; the indexed shape only
            // exposes this group's original 26 or 27 active experts.
            auto *view=ggml_view_3d(ctx,roots[group][role],k,n,split_bank_active[group],k*2,padded_bank_stride,m.residue);
            inputs[group][role]=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,k,10,1);ggml_set_input(inputs[group][role]);
            ids[group][role]=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,10,1);ggml_set_input(ids[group][role]);
            auto *out=ggml_mul_mat_id(ctx,view,inputs[group][role],ids[group][role]);outputs[group][role]=out;ggml_set_output(out);
            graph[group][role]=ggml_new_graph_custom(ctx,16,false);ggml_build_forward_expand(graph[group][role],out);
        }
        bounded();auto *buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);check(buffer,"Split graph working allocation refused");
        ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();
        for(unsigned group=0;group<2;++group)for(unsigned role=0;role<3;++role) {
            bounded();const auto global=group?52u:0u;const auto &m=matrices[role*2+group];
            const auto slot=split_padded_slot(global,m.residue,alignment);check(slot.group==group,"Split global slot remap differs");
            auto *root=static_cast<unsigned char *>(banks[group][role].destination);auto *base=root+slot.envelope.aligned_write_offset;
            const bool before=slot.local_slot>0,after=slot.envelope.aligned_write_offset+padded_bank_stride+bank_read_alignment<=banks[group][role].bytes;
            if(before)std::memset(base-bank_read_alignment,0xa7,bank_read_alignment);
            if(after)std::memset(base+padded_bank_stride,0xa7,bank_read_alignment);
            check(identity(fd)==source,"Split pack changed before Direct read");
            qwen_native_stage(("split_bank_Direct_before group="+std::to_string(group)+" role="+std::to_string(role)+" offset="+std::to_string(m.offset)+" bytes="+std::to_string(padded_bank_stride)).c_str());
            const auto got=pread(fd,base,padded_bank_stride,m.offset);++reads;
            qwen_native_stage("split_bank_Direct_returned");
            check(got==static_cast<ssize_t>(padded_bank_stride)&&identity(fd)==source,"Split original Direct read did not return exact bytes");verify(base,m);
            const unsigned k=role==2?640:2560,n=role==2?2560:640;
            std::vector<float> input(std::size_t(k)*10),actual(std::size_t(n)*10),prior;
            std::vector<double> reference(n);
            for(unsigned col=0;col<k;++col) {
                const auto value=float(int(col%13)-6)/12288.0f;
                if(ggml_bf16_to_fp32(ggml_fp32_to_bf16(value))!=value)++non_exact;
                for(unsigned v=0;v<10;++v)input[std::size_t(v)*k+col]=value;
            }
            for(unsigned row=0;row<n;++row)for(unsigned col=0;col<k;++col) {
                std::uint16_t bits;std::memcpy(&bits,base+m.residue+(std::size_t(row)*k+col)*2,2);
                const auto wide=std::uint32_t(bits)<<16;float weight;std::memcpy(&weight,&wide,4);
                check(std::isfinite(weight),"Split original BF16 weight is nonfinite");reference[row]+=double(weight)*input[col];
            }
            std::array<std::int32_t,10> selected{};selected.fill(slot.local_slot);
            ggml_backend_tensor_set(inputs[group][role],input.data(),0,input.size()*4);
            ggml_backend_tensor_set(ids[group][role],selected.data(),0,sizeof(selected));
            double error=0,normalized_error=0;
            for(unsigned repeat=0;repeat<2;++repeat) {
                bounded();const auto paths=gpu_path_stats();qwen_native_stage("split_bank_graph_before_submission");
                check(ggml_backend_graph_compute(backend,graph[group][role])==GGML_STATUS_SUCCESS,"Split GPU graph completion refused; owners retained");
                ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();++graphs;
                qwen_native_stage("split_bank_graph_positive_idle_and_epoch_returned");
                const auto completed=gpu_path_stats();check(completed.bf16_vector==paths.bf16_vector+1&&completed.bf16_matrix==paths.bf16_matrix,"Split indexed vector dispatch changed");
                ggml_backend_tensor_get(outputs[group][role],actual.data(),0,actual.size()*4);
                for(unsigned v=0;v<10;++v)for(unsigned row=0;row<n;++row) {
                    const auto value=actual[std::size_t(v)*n+row];const auto difference=std::abs(double(value)-reference[row]);
                    const auto tolerance=1e-5+1e-5*std::abs(reference[row]);
                    check(std::isfinite(value)&&difference<=tolerance,"Split F64 matrix reference differs");
                    error=std::max(error,difference);normalized_error=std::max(normalized_error,difference/tolerance);
                }
                if(!repeat)prior=actual;else check(!std::memcmp(prior.data(),actual.data(),actual.size()*4),"Split repeated F32 output differs in bits");
                verify(base,m);
                for(unsigned j=0;j<bank_read_alignment;++j) {
                    if(before)check(base[-int(j)-1]==0xa7,"Split preceding canary differs");
                    if(after)check(base[padded_bank_stride+j]==0xa7,"Split following canary differs");
                }
            }
            maximum_error=std::max(maximum_error,error);maximum_normalized_error=std::max(maximum_normalized_error,normalized_error);
            cases.push_back({{"group",group},{"role",role},{"global_slot",global},{"local_slot",slot.local_slot},
                {"columns",k},{"rows",n},{"residue",m.residue},{"original_raw_sha256",m.raw},{"original_envelope_sha256",m.envelope},
                {"GPU_graphs",2},{"F64_reference_passed",true},{"maximum_absolute_error",error},{"maximum_normalized_error",normalized_error},
                {"reference_absolute_tolerance",1e-5},{"reference_relative_tolerance",1e-5},{"same_F32_outputs_bit_exact",true},
                {"preceding_canary_checked",before},{"following_canary_checked",after},{"whole_envelope_unchanged_after_GPU",true}});
        }
        set_bf16_indexed_vector_scope(false);configure_bf16_indexed_vector(false);configure_padded_index_layout(false);
        ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();ggml_backend_buffer_free(buffer);ggml_free(ctx);qwen_native_driver_checkpoint();
    }
};
} // namespace
Json admit_split_bank_backing(const Json &policy,const std::string &journal,bool &GPU_started) {
    require_split_bank_policy(policy,true,false,false);
    check(!GPU_started,"Split GPU initialization may only be attempted once");
    for(const auto *key:{"GGML_VK_BOUNDED_STAGING","GGML_VK_DISABLE_ASYNC","GGML_VK_SERIALIZE_SUBMISSIONS","GGML_VK_MAX_NODES_PER_SUBMIT"})
        check(!setenv(key,"1",1),"Split backing requires the original serialized Vulkan policy");
    verify_native_startup_file_direct(split_bank_pack_path,split_bank_pack_bytes,split_bank_pack_sha256,30);
    auto *f=new Fixture;f->fd=open(split_bank_pack_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);
    check(f->fd>=0&&(fcntl(f->fd,F_GETFL)&O_DIRECT),"Split original Direct descriptor refused");f->source=identity(f->fd);
    start_native_model_sources({{split_bank_pack_path,split_bank_pack_bytes,f->source}});
    const auto before_GPU=admit_native_startup_memory();GPU_started=true;
    qwen_native_stage("split_bank_CPU_source_owner_completed_before_GPU_initialization");
    qwen_native_gpu_initialize(journal.c_str());qwen_native_driver_begin();llama_backend_init();
    enforce_native_model_compute_limits();f->backend=ggml_backend_vk_init(0);check(f->backend,"Split original Vulkan backend unavailable");
    f->allocation.prepare(f->backend);f->allocation.with_owned_backings(Fixture::use,f);f->allocation.close_completed();
    check(identity(f->fd)==f->source&&!close(f->fd),"Split original pack identity or close differs");f->fd=-1;
    ggml_backend_synchronize(f->backend);qwen_native_driver_checkpoint();ggml_backend_free(f->backend);qwen_native_driver_checkpoint();
    const auto ledger=native_model_device_stats();check(!ledger.live,"Split device resources remain live");stop_native_model_sources();
    check(f->reads==6&&f->graphs==12&&f->cases.size()==6&&f->non_exact>0,"Split finite backing cohort is incomplete");
    Json result={{"schema","ps5-qwen-split-bank-result-v1"},{"cases",f->cases},{"mapped_Direct_read_calls",f->reads},{"GPU_graphs",f->graphs},
        {"independent_actual_VkDeviceMemory_groups",2},{"contiguous_roles_per_actual_group",3},{"nested_strong_backing_leases",6},
        {"conservative_cache_charge_bytes",f->allocation.charged_bytes()},{"maximum_absolute_error",f->maximum_error},
        {"maximum_normalized_error",f->maximum_normalized_error},
        {"non_BF16_exact_F32_input_values",f->non_exact},{"original_pack_SHA256_checked",true},{"source_pack_sha256",split_bank_pack_sha256},
        {"all_original_raw_and_envelope_SHA256_checked",true},{"positive_resource_retirement",true},{"all_started_IO_closed",true},
        {"source_workers",0},{"model_loaded",false},{"GPU_IO_overlap_tested",false},{"generation_speed_measured",false},
        {"device_ledger_peak_bytes",ledger.peak},{"device_ledger_live_bytes",ledger.live},
        {"kernel_free_after_CPU_source_before_GPU",before_GPU.kernel_free},{"kernel_startup_target_pages",before_GPU.kernel_target}};
    delete f;return result;
}
}

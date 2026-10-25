// SPDX-License-Identifier: MIT
#include "padded_bank_layout.h"
#include "padded_bank_bridge.h"
#include "padded_bank.h"
#include "indexed_vector.h"
#include "indexed_vector_admission.h"
#include "system_memory.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
namespace {
constexpr std::array<std::int32_t,10> selected{{52,0,26,0,51,1,52,13,25,42}};
using Identity=std::array<std::uint64_t,10>;
Identity identity(int fd) {
    struct stat st{};
    if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_size!=(512ll<<20))
        throw std::runtime_error("Padded layout requires the sealed first physical part");
    return {std::uint64_t(st.st_dev),std::uint64_t(st.st_ino),std::uint64_t(st.st_mode),
        std::uint64_t(st.st_uid),std::uint64_t(st.st_gid),std::uint64_t(st.st_size),
        std::uint64_t(st.st_mtim.tv_sec),std::uint64_t(st.st_mtim.tv_nsec),
        std::uint64_t(st.st_ctim.tv_sec),std::uint64_t(st.st_ctim.tv_nsec)};
}
std::string digest(const void *data,std::size_t bytes) {
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,static_cast<const unsigned char *>(data),bytes);
    unsigned char raw[32];sha256_final(&hash,raw);std::string text;
    for(auto value:raw){text+="0123456789abcdef"[value>>4];text+="0123456789abcdef"[value&15];}
    return text;
}
struct RouteReset {
    ~RouteReset(){set_bf16_indexed_vector_scope(false);configure_bf16_indexed_vector(false);
        configure_padded_index_layout(false);}
};
struct Session {
    const std::string &path,&expected_hash;PaddedLayoutResult &result;
    std::vector<std::uint16_t> &positive,&negative;
    ggml_backend_t backend;ggml_tensor *input;
    const std::array<ggml_tensor *,30> &outputs;
    const std::array<ggml_cgraph *,30> &graphs;
    unsigned columns,rows,vectors;void (*checkpoint)();void (*stage)(const char *);
    std::chrono::steady_clock::time_point deadline;
    void bounded() const {
        if(std::chrono::steady_clock::now()>deadline)
            throw std::runtime_error("Padded layout finite CPU deadline exceeded; backing retained");
    }
    void read_once(void *target) {
        if(!positive.empty())return;
        stage("padded_layout_open_before_native_call");
        const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);
        stage("padded_layout_open_native_call_returned");
        if(fd<0)throw std::runtime_error("Padded layout source open refused; no retry");
        const auto before=identity(fd);const auto mode=fcntl(fd,F_GETFL);
        if(mode<0||(mode&O_ACCMODE)!=O_RDONLY||!(mode&O_DIRECT))
            throw std::runtime_error("Padded layout source descriptor refused; descriptor retained");
        (void)admit_native_system_memory();stage("padded_layout_read_before_native_call");
        const auto count=pread(fd,target,padded_bank_stride,131072);
        stage("padded_layout_read_native_call_returned");++result.Direct_reads;
        if(identity(fd)!=before)throw std::runtime_error("Padded layout source changed; descriptor retained");
        stage("padded_layout_close_before_native_call");const int closed=close(fd);
        stage("padded_layout_close_native_call_returned");
        if(closed)throw std::runtime_error("Padded layout source close refused; backing retained");
        result.all_IO_closed=true;
        if(count!=static_cast<ssize_t>(padded_bank_stride)||digest(target,padded_bank_stride)!=expected_hash)
            throw std::runtime_error("Padded layout exact Direct bytes refused; no retry");
        positive.resize(padded_bank_stride/2);negative.resize(positive.size());
        std::memcpy(positive.data(),target,padded_bank_stride);
        for(std::size_t i=0;i<positive.size();++i) {
            if((positive[i]&0x7f80u)==0x7f80u)
                throw std::runtime_error("Padded layout source contains nonfinite BF16");
            negative[i]=positive[i]^0x8000u;
        }
    }
};
int fill_and_check(void *target,std::size_t bytes,std::uint64_t flags,std::size_t alignment,void *opaque) {
    auto &s=*static_cast<Session *>(opaque);auto &r=s.result;RouteReset reset;
    if(bytes!=padded_bank_tensor_bytes||reinterpret_cast<std::uintptr_t>(target)%bank_read_alignment)
        throw std::invalid_argument("Padded layout exact owned mapping refused");
    configure_padded_index_layout(true,alignment);
    for(const auto residue:original_bank_residues)
        (void)padded_bank_slot(52,residue,bytes,alignment);
    r.memory_flags=flags;r.descriptor_alignment=alignment;s.read_once(target);
    auto *bank=static_cast<std::uint8_t *>(target);
    // Each aligned read may write one extra alignment block. The unused 54th
    // plane separates the last active slot from any neighbouring allocation.
    for(unsigned slot=0;slot<padded_bank_active_slots;++slot)
        std::memcpy(bank+slot*padded_bank_stride,(slot%2?s.negative:s.positive).data(),padded_bank_stride);
    std::memset(bank+padded_bank_active_slots*padded_bank_stride,0x5a,bank_read_alignment);
    std::vector<float> inputs(std::size_t(s.columns)*s.vectors),actual(std::size_t(s.rows)*10);
    std::vector<double> grouped(std::size_t(s.rows)*13),expected(actual.size());
    for(unsigned layout=0;layout<original_bank_residues.size();++layout) {
        s.bounded();const auto residue=original_bank_residues[layout];
        auto &report=r.cases.emplace_back();report.columns=s.columns;report.rows=s.rows;
        report.input_vectors=s.vectors;report.residue=residue;
        std::fill(grouped.begin(),grouped.end(),0.0);
        // Inputs repeat every 13 columns. Accumulating exact BF16 values by
        // residue avoids ten redundant conversions per original weight.
        for(unsigned row=0;row<s.rows;++row)for(unsigned col=0;col<s.columns;++col) {
            ggml_bf16_t bf;std::memcpy(&bf,&s.positive[residue/2+std::size_t(row)*s.columns+col],2);
            grouped[std::size_t(row)*13+col%13]+=double(ggml_bf16_to_fp32(bf));
        }
        for(unsigned strategy=0;strategy<3;++strategy) {
            s.bounded();const bool non_dyadic=strategy==2,vector=strategy!=0;
            for(unsigned v=0;v<s.vectors;++v)for(unsigned col=0;col<s.columns;++col) {
                const auto value=indexed_fixture_input(col,v,non_dyadic)/16;
                inputs[std::size_t(v)*s.columns+col]=value;
                if(non_dyadic&&ggml_bf16_to_fp32(ggml_fp32_to_bf16(value))!=value)
                    ++report.non_BF16_exact_F32_inputs;
            }
            for(unsigned slot=0;slot<10;++slot)for(unsigned row=0;row<s.rows;++row) {
                double sum=0;
                for(unsigned mod=0;mod<13;++mod)
                    sum+=grouped[std::size_t(row)*13+mod]*inputs[std::size_t(slot%s.vectors)*s.columns+mod];
                expected[std::size_t(slot)*s.rows+row]=selected[slot]%2?-sum:sum;
            }
            auto *output=s.outputs[layout];
            if(!qwen_app_padded_index_layout(output))
                throw std::runtime_error("Padded layout did not reach the exact vector predicate");
            configure_bf16_indexed_vector(vector);set_bf16_indexed_vector_scope(true);
            if(!ggml_backend_dev_supports_op(ggml_backend_get_device(s.backend),output))
                throw std::runtime_error("Padded layout GPU operation unsupported");
            ggml_backend_tensor_set(s.input,inputs.data(),0,inputs.size()*4);
            const auto before=gpu_path_stats();s.stage("padded_layout_before_finite_graph");
            if(ggml_backend_graph_compute(s.backend,s.graphs[layout])!=GGML_STATUS_SUCCESS)
                throw std::runtime_error("Padded layout GPU completion failed; backing retained");
            ggml_backend_synchronize(s.backend);s.checkpoint();
            const auto after=gpu_path_stats();
            if(after.bf16_matrix-before.bf16_matrix!=(vector?0u:1u)||
               after.bf16_vector-before.bf16_vector!=(vector?1u:0u))
                throw std::runtime_error("Padded layout selected shader counter refused");
            ggml_backend_tensor_get(output,actual.data(),0,actual.size()*4);
            for(std::size_t i=0;i<actual.size();++i) {
                const auto error=std::abs(double(actual[i])-expected[i]);
                if(!std::isfinite(actual[i])||!std::isfinite(expected[i])||error>1e-6)
                    throw std::runtime_error("Padded layout BF16/F32 numerical refusal; backing retained");
                report.maximum_absolute_error=std::max(report.maximum_absolute_error,error);
            }
            if(strategy==0)report.matrix_passed=true;
            else if(strategy==1)report.vector_passed=true;
            else report.non_dyadic_vector_passed=report.non_BF16_exact_F32_inputs>0;
            ++r.GPU_graphs;s.stage("padded_layout_numerics_and_positive_completion_passed");
        }
        report.padding_intact=true;
        for(std::size_t i=0;i<bank_read_alignment;++i)
            if(bank[padded_bank_active_slots*padded_bank_stride+i]!=0x5a)report.padding_intact=false;
        for(unsigned slot=0;slot<padded_bank_active_slots;++slot)
            if(std::memcmp(bank+slot*padded_bank_stride,(slot%2?s.negative:s.positive).data(),padded_bank_stride))
                report.padding_intact=false;
        if(!report.padding_intact||!report.non_dyadic_vector_passed)
            throw std::runtime_error("Padded layout allocation/padding or F32 coverage refused");
    }
    r.eligible=true;return 0;
}
}
PaddedLayoutResult admit_padded_bank_layout(const std::string &path,const std::string &hash,
    void (*checkpoint)(),void (*stage)(const char *)) {
    if(!checkpoint||!stage||path.empty()||hash.size()!=64||hash.find_first_not_of("0123456789abcdef")!=std::string::npos)
        throw std::invalid_argument("Padded layout requires immutable source and completion hooks");
    PaddedLayoutResult result;std::vector<std::uint16_t> positive,negative;
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(120);
    for(unsigned shape=0;shape<4;++shape) {
        const unsigned k=shape<2?2560:640,n=shape<2?640:2560,v=shape%2?10:1;
        auto *backend=ggml_backend_vk_init(0);if(!backend)throw std::runtime_error("Padded layout backend unavailable");
        ggml_init_params p{};p.no_alloc=true;
        p.mem_size=ggml_tensor_overhead()*70+30*ggml_graph_overhead_custom(16,false);
        auto *ctx=ggml_init(p);if(!ctx)throw std::runtime_error("Padded layout metadata unavailable");
        auto *a=ggml_new_tensor_3d(ctx,GGML_TYPE_BF16,k,n,padded_bank_physical_slots);
        a->nb[2]=padded_bank_stride;a->nb[3]=padded_bank_stride*padded_bank_physical_slots;
        auto *b=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,k,v,1);
        auto *ids=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,10,1);
        ggml_set_input(a);ggml_set_input(b);ggml_set_input(ids);
        std::array<ggml_tensor *,30> outputs{};std::array<ggml_cgraph *,30> graphs{};
        for(unsigned i=0;i<original_bank_residues.size();++i) {
            auto *view=ggml_view_3d(ctx,a,k,n,padded_bank_active_slots,k*2,padded_bank_stride,original_bank_residues[i]);
            outputs[i]=ggml_mul_mat_id(ctx,view,b,ids);ggml_set_output(outputs[i]);
            graphs[i]=ggml_new_graph_custom(ctx,16,false);ggml_build_forward_expand(graphs[i],outputs[i]);
        }
        auto *buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);
        if(!buffer)throw std::runtime_error("Padded layout device allocation failed");
        ggml_backend_synchronize(backend);checkpoint();
        ggml_backend_tensor_set(ids,selected.data(),0,sizeof(selected));
        Session session{path,hash,result,positive,negative,backend,b,outputs,graphs,k,n,v,checkpoint,stage,deadline};
        stage("padded_layout_before_synchronous_owned_lease");
        const int admitted=ggml_app_vk_probe_owned_bank(a,fill_and_check,&session);
        stage("padded_layout_synchronous_owned_lease_returned");
        if(admitted!=0)throw std::runtime_error("Padded layout real owned mapping unavailable");
        ggml_backend_synchronize(backend);checkpoint();
        ggml_backend_buffer_free(buffer);ggml_free(ctx);ggml_backend_free(backend);checkpoint();
        stage("padded_layout_shape_resources_positively_retired");
    }
    if(result.cases.size()!=120||result.GPU_graphs!=360||result.Direct_reads!=1||!result.all_IO_closed)
        throw std::runtime_error("Padded layout finite coverage incomplete");
    result.positive_retirement=true;return result;
}
}

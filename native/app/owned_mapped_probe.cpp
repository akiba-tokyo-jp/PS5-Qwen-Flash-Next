// SPDX-License-Identifier: MIT
#include "owned_mapped_probe.h"
#include "mapped_copy.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
#include "system_memory.h"
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
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
namespace {
using Identity=std::array<std::uint64_t,10>;
Identity identity(int fd) {
    struct stat s{};
    if(fstat(fd,&s)||!S_ISREG(s.st_mode)||s.st_size!=(512ll<<20))
        throw std::runtime_error("Owned probe requires the sealed first physical part");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
        std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
std::string digest(const void *data,std::size_t bytes) {
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,static_cast<const unsigned char *>(data),bytes);
    unsigned char raw[32];sha256_final(&hash,raw);std::string text;
    for(auto v:raw){text+="0123456789abcdef"[v>>4];text+="0123456789abcdef"[v&15];}
    return text;
}
struct Session {
    const std::string &path,&expected_hash;OwnedMappedProbe &result;
    ggml_backend_t backend;ggml_cgraph *graph;ggml_tensor *input,*output;
    void (*checkpoint)();void (*stage)(const char *);
    std::vector<std::uint16_t> reference;
    std::array<float,2560> inputs{};
    std::array<float,640> actual{};
    std::array<double,640> expected{};
    void compute() {
        stage("owned_probe_before_finite_graph");
        if(ggml_backend_graph_compute(backend,graph)!=GGML_STATUS_SUCCESS)
            throw std::runtime_error("Owned probe GPU completion failed; backing retained");
        ggml_backend_synchronize(backend);checkpoint();
        ggml_backend_tensor_get(output,actual.data(),0,sizeof(actual));
        for(std::size_t i=0;i<actual.size();++i) {
            const auto error=std::abs(double(actual[i])-expected[i]);
            if(!std::isfinite(actual[i])||!std::isfinite(expected[i])||error>1e-5+1e-5*std::abs(expected[i]))
                throw std::runtime_error("Owned probe original BF16 matvec reference failed; backing retained");
            result.maximum_absolute_error=std::max(result.maximum_absolute_error,error);
        }
        ++result.graphs;stage("owned_probe_graph_numerics_and_positive_retirement_passed");
    }
};
int fill_owned_mapping(void *target,std::size_t bytes,std::uint64_t flags,void *opaque) {
    auto &s=*static_cast<Session *>(opaque);auto &r=s.result;
    if(bytes!=owned_probe_bytes||reinterpret_cast<std::uintptr_t>(target)%16384)
        throw std::invalid_argument("Owned probe exact mapping alignment refused");
    r.memory_flags=flags;(void)admit_native_system_memory();
    s.stage("owned_probe_open_before_native_call");
    const int fd=open(s.path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);
    s.stage("owned_probe_open_native_call_returned");
    if(fd<0)throw std::runtime_error("Owned probe source open refused; no retry");
    const auto before=identity(fd);const auto mode=fcntl(fd,F_GETFL);
    if(mode<0||(mode&O_ACCMODE)!=O_RDONLY||!(mode&O_DIRECT))
        throw std::runtime_error("Owned probe source mode refused; descriptor retained");
    (void)admit_native_system_memory();
    s.stage("owned_probe_read_before_native_call");
    const auto count=pread(fd,target,bytes,131072);const int saved_errno=errno;
    s.stage("owned_probe_read_native_call_returned");
    r.read_result=static_cast<int>(count);r.read_errno=count<0?saved_errno:0;
    if(identity(fd)!=before)throw std::runtime_error("Owned probe source identity changed; descriptor retained");
    s.stage("owned_probe_close_before_native_call");const int closed=close(fd);
    s.stage("owned_probe_close_native_call_returned");
    if(closed)throw std::runtime_error("Owned probe source close refused; backing retained");
    r.all_IO_returned=true;
    if(count<0&&(saved_errno==EINVAL||saved_errno==EFAULT||saved_errno==ENOTSUP))return 1;
    if(count!=static_cast<ssize_t>(bytes)||digest(target,bytes)!=s.expected_hash)
        throw std::runtime_error("Owned probe exact source bytes failed; backing retained");
    r.eligible=true;s.reference.resize(bytes/2);std::memcpy(s.reference.data(),target,bytes);
    for(unsigned col=0;col<2560;++col)s.inputs[col]=float(int(col%13)-6)/1024;
    for(unsigned row=0;row<640;++row)for(unsigned col=0;col<2560;++col) {
        ggml_bf16_t value;std::memcpy(&value,&s.reference[std::size_t(row)*2560+col],2);
        const float weight=ggml_bf16_to_fp32(value);
        if(!std::isfinite(weight))throw std::runtime_error("Owned probe source contains nonfinite BF16");
        s.expected[row]+=double(weight)*s.inputs[col];
    }
    ggml_backend_tensor_set(s.input,s.inputs.data(),0,sizeof(s.inputs));s.compute();
    constexpr std::array<bool,6> order{{false,true,true,false,false,true}};
    for(unsigned block=0;block<order.size();++block) {
        s.stage("owned_probe_copy_block_started");
        configure_mapped_copy(order[block]);set_mapped_copy_scope(order[block]);
        const auto start=std::chrono::steady_clock::now();
        for(unsigned repeat=0;repeat<5;++repeat) {
            if(order[block]) {
                if(!try_streaming_mapped_copy(target,s.reference.data(),bytes))
                    throw std::runtime_error("Owned mapped streaming copy unexpectedly refused");
            } else std::memcpy(target,s.reference.data(),bytes);
        }
        const auto elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        set_mapped_copy_scope(false);configure_mapped_copy(false);
        if(!std::isfinite(elapsed)||elapsed<=0||elapsed>2000||std::memcmp(target,s.reference.data(),bytes))
            throw std::runtime_error("Owned copy byte equality or bounded timing failed; backing retained");
        r.copies[block]={order[block],elapsed,true};s.compute();
    }
    r.GPU_numerics=true;return 0;
}
}
OwnedMappedProbe admit_owned_mapped_probe(const std::string &path,const std::string &expected_hash,
    void (*checkpoint)(),void (*stage)(const char *)) {
    if(!checkpoint||!stage||path.empty()||expected_hash.size()!=64||
       expected_hash.find_first_not_of("0123456789abcdef")!=std::string::npos)
        throw std::invalid_argument("Owned probe requires exact immutable source and completion hooks");
    OwnedMappedProbe r;
    auto *backend=ggml_backend_vk_init(0);if(!backend)throw std::runtime_error("Owned probe backend unavailable");
    ggml_init_params p{};p.no_alloc=true;p.mem_size=ggml_tensor_overhead()*4+ggml_graph_overhead_custom(8,false);
    auto *context=ggml_init(p);if(!context)throw std::runtime_error("Owned probe CPU metadata unavailable");
    auto *a=ggml_new_tensor_2d(context,GGML_TYPE_BF16,2560,640);
    auto *b=ggml_new_tensor_1d(context,GGML_TYPE_F32,2560);auto *out=ggml_mul_mat(context,a,b);
    ggml_set_input(a);ggml_set_input(b);ggml_set_output(out);
    auto *graph=ggml_new_graph_custom(context,8,false);ggml_build_forward_expand(graph,out);
    if(!ggml_backend_dev_supports_op(ggml_backend_get_device(backend),out))
        throw std::runtime_error("Owned probe BF16 matvec unsupported");
    auto *buffer=ggml_backend_alloc_ctx_tensors(context,backend);
    if(!buffer)throw std::runtime_error("Owned probe real device buffer allocation failed");
    ggml_backend_synchronize(backend);checkpoint();
    Session session{path,expected_hash,r,backend,graph,b,out,checkpoint,stage};
    stage("owned_probe_before_synchronous_owned_lease");
    const int result=ggml_app_vk_probe_owned_matvec(a,fill_owned_mapping,&session);
    stage("owned_probe_synchronous_owned_lease_returned");
    if(result!=0&&result!=1)throw std::runtime_error("Owned probe lease result invalid");
    if(result==0&&(!r.eligible||!r.GPU_numerics||r.graphs!=7||!r.all_IO_returned))
        throw std::runtime_error("Owned probe incomplete positive result; backing retained");
    ggml_backend_synchronize(backend);checkpoint();
    ggml_backend_buffer_free(buffer);ggml_free(context);ggml_backend_free(backend);checkpoint();
    r.retired=true;stage("owned_probe_known_result_and_positive_resource_retirement_passed");return r;
}
}

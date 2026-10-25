// SPDX-License-Identifier: MIT
#include "palette_gpu_admission.h"
#include "palette_gpu_dispatch.h"
#include "bf16_palette.h"
#include "direct_integrity.h"
#include "model_integrity.h"
#include "profile_clock.h"
#include "system_memory.h"
#include "native_gpu.h"
#include <algorithm>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
}
extern "C" void qwen_native_stage(const char *);
namespace qwen_app {
namespace {
using Json=nlohmann::json;
constexpr unsigned matrix_bytes=3276800;
alignas(16384)unsigned char pack_tail[16384];
void check(bool value,const char *message){if(!value)throw std::runtime_error(message);}
std::string hash(const unsigned char *data,std::size_t bytes) {
    check(data&&bytes>0&&bytes<=PaletteGpuDispatch::buffer_bytes,"Palette hash bounds differ");
    sha256_t h;sha256_init(&h);sha256_update(&h,data,bytes);unsigned char digest[32];sha256_final(&h,digest);
    std::string result;result.reserve(64);
    for(auto value:digest){result.push_back("0123456789abcdef"[value>>4]);result.push_back("0123456789abcdef"[value&15]);}
    return result;
}
std::vector<std::uint32_t> shader(const Json &entry) {
    const auto path=entry.at("path").get<std::string>();const auto bytes=entry.at("bytes").get<std::size_t>();
    verify_native_startup_file_direct(path,bytes,entry.at("sha256"),10);
    std::vector<std::uint32_t> words(bytes/4);std::ifstream file(path,std::ios::binary);
    check(bool(file.read(reinterpret_cast<char *>(words.data()),bytes))&&file.peek()==std::char_traits<char>::eof(),"Palette SPIRV read differs");
    check(hash(reinterpret_cast<const unsigned char *>(words.data()),bytes)==entry.at("sha256"),"Palette SPIRV changed after verification");
    return words;
}
std::array<std::uint64_t,10> identity(int fd) {
    struct stat s{};check(fstat(fd,&s)==0&&S_ISREG(s.st_mode)&&s.st_size>0,"Palette pack descriptor is invalid");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
}
Json admit_palette_gpu(const Json &policy,const std::string &journal) {
    require_palette_gpu_policy(policy,false);const auto &p=policy.at("native_palette_validation");
    const auto &pack=p.at("pack");const auto path=pack.at("path").get<std::string>();
    qwen_native_stage("palette_before_full_Direct_pack_integrity");
    verify_native_startup_file_direct(path,pack.at("bytes"),pack.at("sha256"),30);
    const auto copy=shader(p.at("shaders").at("copy")),palette=shader(p.at("shaders").at("palette"));
    const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);
    check(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)==O_DIRECT,"Palette Direct source descriptor is unavailable");
    const auto original=identity(fd);check(original[5]==pack.at("bytes"),"Palette pack size changed");
    const auto tail_offset=original[5]&~std::uint64_t(16383);
    qwen_native_stage("palette_pack_EOF_read_before");
    const auto tail=pread(fd,pack_tail,sizeof(pack_tail),static_cast<off_t>(tail_offset));
    qwen_native_stage("palette_pack_EOF_read_returned");
    check(tail==static_cast<ssize_t>(original[5]-tail_offset)&&identity(fd)==original,"Palette complete pack EOF or identity differs");
    (void)admit_native_startup_memory();
    qwen_native_gpu_initialize(journal.c_str());qwen_native_driver_begin();
    auto *gpu=new PaletteGpuDispatch(copy.data(),copy.size()*4,palette.data(),palette.size()*4);
    std::vector<unsigned char> patterns(65536*2),encoded(qwen_palette_bound(65536));
    for(unsigned i=0;i<65536;++i){patterns[2*i]=static_cast<unsigned char>(i);patterns[2*i+1]=static_cast<unsigned char>(i>>8);}
    const auto encoded_size=qwen_palette_encode(patterns.data(),patterns.size(),encoded.data(),encoded.size());
    check(encoded_size>0,"Palette all-pattern control encoding failed");
    unsigned dispatches=0;
    for(unsigned mode=0;mode<2;++mode) {
        const auto &input=mode?encoded:patterns;const auto bytes=mode?encoded_size:patterns.size();
        std::memcpy(gpu->source(),input.data(),bytes);std::memset(gpu->target(),0xa5,patterns.size()+16);
        qwen_palette_plan plan{};
        if(mode)check(qwen_palette_prepare(gpu->source(),bytes,gpu->target(),patterns.size(),&plan)!=0,"Palette all-pattern prevalidation failed");
        gpu->dispatch(mode!=0,65536,static_cast<std::uint32_t>(bytes));++dispatches;
        check(std::memcmp(gpu->target(),patterns.data(),patterns.size())==0,"Palette all65536 BF16 GPU bits differ");
        for(unsigned i=0;i<16;++i)check(gpu->target()[patterns.size()+i]==0xa5,"Palette all-pattern output canary changed");
    }
    qwen_native_stage("palette_all65536_BF16_patterns_GPU_exact");
    Json rounds=Json::array();const auto begun=ProfileClock::now();
    for(unsigned round=0;round<6;++round)for(unsigned sample=0;sample<9;++sample)for(unsigned order=0;order<2;++order) {
        check(profile_elapsed_ns(begun)<120000000000ull,"Palette finite cohort deadline exceeded");
        const unsigned mode=(round+order)%2;const auto &item=p.at("samples").at(sample);
        const auto &e=item.at(mode?"encoded":"raw");
        (void)admit_native_system_memory();check(identity(fd)==original,"Palette source identity changed before read");
        const auto bytes=e.at("bytes").get<std::size_t>(),requested=e.at("requested").get<std::size_t>();
        const auto offset=e.at("offset").get<std::uint64_t>();
        std::memset(gpu->target(),0xa5,matrix_bytes+16);
        const auto started=ProfileClock::now();qwen_native_stage("palette_matrix_Direct_read_before");
        const auto got=pread(fd,gpu->source(),requested,static_cast<off_t>(offset));
        qwen_native_stage("palette_matrix_Direct_read_returned");
        check(got==static_cast<ssize_t>(requested),"Palette matrix read did not return exact bytes");
        const auto read_ns=profile_elapsed_ns(started);
        qwen_palette_plan plan{};
        if(mode)check(qwen_palette_prepare(gpu->source(),bytes,gpu->target(),matrix_bytes,&plan)!=0,"Palette original matrix prevalidation failed");
        const auto dispatch_ns=gpu->dispatch(mode!=0,matrix_bytes/2,static_cast<std::uint32_t>(bytes));++dispatches;
        const auto delivery_ns=mode?profile_elapsed_ns(started):read_ns;
        check(hash(gpu->source(),bytes)==e.at("sha256"),"Palette original input SHA256 differs");
        check(hash(gpu->target(),matrix_bytes)==item.at("raw").at("sha256"),"Palette original GPU output SHA256 differs");
        for(unsigned i=0;i<16;++i)check(gpu->target()[matrix_bytes+i]==0xa5,"Palette original output canary changed");
        check(identity(fd)==original,"Palette source identity changed after read");
        rounds.push_back({{"round",round},{"sample",sample},{"mode",mode},{"read_ns",read_ns},{"dispatch_completion_ns",dispatch_ns},{"delivery_ns",delivery_ns},{"physical_bytes",requested},{"original_SHA256_exact",true}});
    }
    check(close(fd)==0,"Palette source close did not complete");
    check(dispatches==110,"Palette fixed dispatch count differs");
    return {{"schema","ps5-qwen-exact-palette-GPU-result-v1"},{"passed",true},
        {"all65536_BF16_patterns_exact",true},{"original_matrix_deliveries",108},{"GPU_dispatches",dispatches},
        {"rounds",rounds},{"model_loaded",false},{"full_model_inference",false},{"quantization",false},
        {"live_GPU_buffer_bytes",2*PaletteGpuDispatch::buffer_bytes},{"device_lifetime","retained until ordinary OS close"},
        {"raw_delivery_includes_copy_check",false},{"palette_delivery_includes_validation_dispatch_fence",true},
        {"all_fences_positively_completed",true},{"source_file_closed",true},{"automatic_retries",0}};
}
}

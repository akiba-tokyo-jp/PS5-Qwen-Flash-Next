// SPDX-License-Identifier: MIT
// Lossless application-resource storage. No model bytes, Vulkan calls or caches.
#include "shader_assets.h"
#include "model_cpu_budget.h"
#include "system_memory.h"
#include "profile_clock.h"
#include "../thirdparty/zlib/zlib.h"
#include <ps5platform/heap.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <thread>
extern "C" {
#include "hash/sha256/sha256.h"
}
#if defined(QWEN_NATIVE_PLATFORM)
static_assert(sizeof(z_stream)==112,"The native inflate provider requires the LP64 z_stream ABI");
static_assert(sizeof(uInt)==4,"The native inflate provider requires 32-bit counters");
#endif
namespace {
constexpr std::size_t maximum_shader=1u<<20,maximum_scratch=1u<<20;
constexpr unsigned char packed_magic[8]={'Q','W','S','P','V','0','0','1'};
constexpr unsigned char shuffled_magic[8]={'Q','W','S','P','V','0','0','2'};
const qwen_shader_asset *assets=nullptr;std::size_t asset_count=0;
const qwen_shader_lookup *lookups=nullptr;std::size_t lookup_count=0;
std::atomic<bool> registration_fault{false},initialized{false},failed{false},active{false};
std::atomic<std::uint64_t> decoded_calls{0},raw_calls{0},verified_assets{0};
std::atomic<std::uint64_t> verified_lookups{0};
std::mutex codec_mutex;std::thread::id lease_owner;
void *output=nullptr,*ordered=nullptr;std::size_t output_bytes=0;std::string registry_hash;
z_stream stream{};
struct Allocation {void *pointer=nullptr;std::size_t bytes=0;};
std::array<Allocation,8> scratch{};std::atomic<std::size_t> scratch_bytes{0};
bool allocator_fault=false;
[[noreturn]] void fail(const char *message){failed.store(true);throw std::runtime_error(message);}
void heap_admission() {
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    if(heap.libc_fallbacks||heap.mapped_bytes>qwen_app::maximum_model_CPU_heap_bytes||
       heap.peak_bytes>qwen_app::maximum_model_CPU_heap_bytes)
        fail("Shader storage must retain the existing tracked CPU heap budget");
}
voidpf allocate_codec(voidpf,uInt count,uInt bytes) {
    if(!count||!bytes||std::size_t(bytes)>maximum_scratch/count){allocator_fault=true;return nullptr;}
    const auto needed=std::size_t(count)*bytes;
    auto slot=std::find_if(scratch.begin(),scratch.end(),[](const auto &v){return !v.pointer;});
    if(slot==scratch.end()||needed>maximum_scratch-scratch_bytes.load()){allocator_fault=true;return nullptr;}
    void *pointer=ps5_heap_calloc(count,bytes);
    if(!pointer||!ps5_heap_owns(pointer)){allocator_fault=true;return nullptr;}
    *slot={pointer,needed};scratch_bytes+=needed;return pointer;
}
void release_codec(voidpf,voidpf pointer) {
    const auto slot=std::find_if(scratch.begin(),scratch.end(),[&](const auto &v){return v.pointer==pointer;});
    if(slot==scratch.end()||!pointer||!ps5_heap_owns(pointer)){allocator_fault=true;return;}
    ps5_heap_free(pointer);scratch_bytes-=slot->bytes;*slot={};
}
std::array<unsigned char,32> digest(const void *data,std::size_t bytes) {
    sha256_t state;sha256_init(&state);sha256_update(&state,static_cast<const unsigned char*>(data),bytes);
    std::array<unsigned char,32> value{};sha256_final(&state,value.data());return value;
}
std::uint32_t u32(const unsigned char *p){return std::uint32_t(p[0])|(std::uint32_t(p[1])<<8)|(std::uint32_t(p[2])<<16)|(std::uint32_t(p[3])<<24);}
std::string identity() {
    sha256_t hash;sha256_init(&hash);
    static constexpr unsigned char prefix[]="ps5-qwen-shader-storage-v1";
    sha256_update(&hash,prefix,sizeof(prefix));
    for(std::size_t i=0;i<asset_count;++i) {
        const auto &a=assets[i];
        if(!a.name||!a.storage||!a.original_bytes||a.original_bytes>maximum_shader||a.original_bytes%4||
           !a.storage_bytes||a.storage_bytes>maximum_shader||a.storage_bytes%4)
            fail("Shader resource metadata exceeds its immutable bounded contract");
        std::size_t length=0;while(length<=256&&a.name[length])++length;
        if(!length||length>256)fail("Shader resource name exceeds its bound");
        sha256_update(&hash,reinterpret_cast<const unsigned char*>(a.name),length+1);
        unsigned char size[8];for(unsigned j=0;j<8;++j)size[j]=static_cast<unsigned char>(std::uint64_t(a.original_bytes)>>(8*j));
        sha256_update(&hash,size,sizeof(size));sha256_update(&hash,a.original_sha256,sizeof(a.original_sha256));
    }
    unsigned char value[32];sha256_final(&hash,value);std::string result;
    for(auto v:value){result.push_back("0123456789abcdef"[v>>4]);result.push_back("0123456789abcdef"[v&15]);}
    return result;
}
void acquire() {
    if(failed.load())fail("Shader codec is quarantined; no retry");
    const auto started=qwen_app::ProfileClock::now();
    while(!codec_mutex.try_lock()) {
        if(failed.load()||qwen_app::profile_elapsed_ns(started)>10000000000ull)
            fail("Shader codec completion is unknown; its owner and backing are retained");
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    if(failed.load()) {codec_mutex.unlock();fail("Shader codec is quarantined; no retry");}
    lease_owner=std::this_thread::get_id();active.store(true);
}
}
extern "C" void qwen_app_register_shader_assets(const qwen_shader_asset *items,std::size_t count) {
    if(assets||!items||!count||count>8192){registration_fault.store(true);return;}
    assets=items;asset_count=count;
}
extern "C" void qwen_app_register_shader_lookups(const qwen_shader_lookup *items,std::size_t count) {
    if(lookups||!items||!count||count>65536){registration_fault.store(true);return;}
    lookups=items;lookup_count=count;
}
namespace qwen_app {
bool native_shader_assets_registered(){return assets||registration_fault.load();}
void initialize_native_shader_assets() {
    if(initialized.load()||registration_fault.load()||!assets||!asset_count||!lookups||!lookup_count||failed.load())
        fail("A fresh immutable shader-resource registry is required");
    (void)qualified_system_headroom(observe_native_system_memory());
    heap_admission();registry_hash=identity();
    for(std::size_t i=0;i<asset_count;++i)output_bytes=std::max(output_bytes,assets[i].original_bytes);
    output=ps5_heap_memalign(16,output_bytes);
    if(!output||!ps5_heap_owns(output))fail("The bounded shader decoder must use the existing Direct CPU heap");
    ordered=ps5_heap_memalign(16,output_bytes);
    if(!ordered||!ps5_heap_owns(ordered))fail("Reversible shader ordering must retain its bounded tracked Direct buffer");
    stream.zalloc=allocate_codec;stream.zfree=release_codec;stream.opaque=nullptr;
    if(inflateInit(&stream)!=Z_OK||allocator_fault)fail("Native shader inflate ABI or scratch admission failed");
    for(std::size_t i=0;i<lookup_count;++i) {
        const auto &v=lookups[i];
        if(!v.observed_data||!v.observed_size||*v.observed_data!=v.expected_data||*v.observed_size!=v.expected_size)
            fail("Shader lookup relocation or stored length changed");
        ++verified_lookups;
    }
    heap_admission();initialized.store(true);
}
ShaderAssetStats native_shader_asset_stats() {
    ShaderAssetStats s;s.assets=asset_count;s.initialized=initialized.load();s.active_lease=active.load();s.failed=failed.load();
    s.decoded_calls=decoded_calls.load();s.raw_calls=raw_calls.load();s.CPU_verified_assets=verified_assets.load();
    s.lookup_entries=lookup_count;s.CPU_verified_lookups=verified_lookups.load();
    s.codec_output_bytes=output_bytes;s.codec_ordering_bytes=output_bytes;s.codec_scratch_bytes=scratch_bytes.load();s.registry_sha256=registry_hash;
    for(std::size_t i=0;i<asset_count;++i){
        s.original_bytes+=assets[i].original_bytes;
        bool alias=false;
        for(std::size_t j=0;j<i;++j)if(assets[j].storage==assets[i].storage){
            if(assets[j].storage_bytes!=assets[i].storage_bytes)fail("An exact shader alias changed its stored length");
            alias=true;break;
        }
        if(!alias)s.stored_bytes+=assets[i].storage_bytes;
        s.maximum_shader_bytes=std::max<std::uint64_t>(s.maximum_shader_bytes,assets[i].original_bytes);
    }
    return s;
}
ShaderAssetStats verify_native_shader_assets_CPU() {
    if(!initialized.load()||verified_assets.load())fail("Shader CPU verification may only run once after initialization");
    for(std::size_t i=0;i<asset_count;++i) {
        std::size_t bytes=0;void *lease=nullptr;
        const void *data=qwen_app_prepare_shader_code(assets[i].storage,assets[i].storage_bytes,&bytes,&lease);
        const auto actual=digest(data,bytes);
        if(bytes!=assets[i].original_bytes||std::memcmp(actual.data(),assets[i].original_sha256,actual.size()))
            fail("Shader CPU roundtrip changed an original SPIR-V byte");
        qwen_app_complete_shader_code(lease);++verified_assets;
    }
    heap_admission();return native_shader_asset_stats();
}
}
extern "C" const void *qwen_app_prepare_shader_code(const void *storage,std::size_t stored_bytes,std::size_t *original_bytes,void **lease) {
    if(!initialized.load()||failed.load()||!storage||!original_bytes||!lease||stored_bytes<20||stored_bytes>maximum_shader||stored_bytes%4)
        fail("Shader code requires its prior CPU storage admission");
    *lease=nullptr;const auto *data=static_cast<const unsigned char*>(storage);
    if(u32(data)==0x07230203) {
        if(reinterpret_cast<std::uintptr_t>(storage)%4)fail("Original SPIR-V is not word aligned");
        *original_bytes=stored_bytes;++raw_calls;return storage;
    }
    const bool shuffled=stored_bytes>=48&&!std::memcmp(data,shuffled_magic,sizeof(shuffled_magic));
    if(stored_bytes<48||(!shuffled&&std::memcmp(data,packed_magic,sizeof(packed_magic))))fail("Unknown immutable shader storage format");
    const auto bytes=u32(data+8),compressed=u32(data+12);
    if(!bytes||bytes>output_bytes||bytes%4||!compressed||compressed>stored_bytes-48||
       stored_bytes!=((48ull+compressed+3)&~3ull))fail("Packed shader lengths exceed their bounded original");
    for(std::size_t i=48+compressed;i<stored_bytes;++i)if(data[i])fail("Packed shader alignment padding changed");
    acquire();heap_admission();
    // These read-only observations do not mutate the producer's wait gate from
    // a compiler thread. A refusal starts no Vulkan operation and retains backing.
    (void)qwen_app::qualified_system_headroom(qwen_app::observe_native_system_memory());
    if(inflateReset(&stream)!=Z_OK)fail("Shader decoder state did not reset positively");
    stream.next_in=const_cast<Bytef*>(data+48);stream.avail_in=compressed;
    stream.next_out=static_cast<Bytef*>(shuffled?ordered:output);stream.avail_out=bytes;
    if(inflate(&stream,Z_FINISH)!=Z_STREAM_END||stream.total_out!=bytes||stream.total_in!=compressed||allocator_fault)
        fail("Lossless shader decompression did not complete exactly");
    if(shuffled) {
        const auto *from=static_cast<const unsigned char*>(ordered);auto *to=static_cast<unsigned char*>(output);
        const std::size_t words=bytes/4;
        for(std::size_t word=0;word<words;++word)for(unsigned lane=0;lane<4;++lane)
            to[word*4+lane]=from[lane*words+word];
    }
    if(
       u32(static_cast<const unsigned char*>(output))!=0x07230203||
       std::memcmp(digest(output,bytes).data(),data+16,32))
        fail("Lossless shader restoration did not match its complete original SHA256");
    heap_admission();*original_bytes=bytes;*lease=output;++decoded_calls;return output;
}
extern "C" void qwen_app_complete_shader_code(void *lease) {
    if(!lease)return;
    if(!active.load()||lease!=output||lease_owner!=std::this_thread::get_id()||failed.load())
        fail("Shader input reuse lacks the matching positive CPU/module completion");
    active.store(false);lease_owner={};codec_mutex.unlock();
    // The fixed codec buffer/scratch stay in the original CPU heap until normal
    // OS close. Unknown completion never unlocks or releases this owner.
}

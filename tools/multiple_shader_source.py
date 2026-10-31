# SPDX-License-Identifier: MIT
"""Bounded immutable shader registration for composed, separately qualified kernels."""
from additional_shader_source import STATE as SINGLE_STATE,PREPARE as SINGLE_PREPARE
from build_speculative_batch_probe import once

STATE=r'''
namespace {
struct AdditionalShader {const unsigned char*data=nullptr;std::size_t bytes=0;std::array<unsigned char,32>sha{};};
// Four records cover the currently declared compositions. This is a software
// bound, not a GPU capacity claim; the record storage is fixed and allocation-free.
std::array<AdditionalShader,4>additional_shaders{};
std::size_t additional_count=0;
std::atomic<std::size_t>additional_verified_count{0};
std::atomic<std::uint64_t>additional_modules{0};
void verify_additional_shader(){
    for(std::size_t i=0;i<additional_count;++i){const auto&v=additional_shaders[i];
        if(reinterpret_cast<std::uintptr_t>(v.data)%4||v.bytes<20||v.bytes>maximum_shader||v.bytes%4||u32(v.data)!=0x07230203)
            fail("Additional immutable shader exceeds its exact word-aligned SPIR-V scope");
        if(digest(v.data,v.bytes)!=v.sha)fail("Additional immutable shader complete SHA256 differs before Vulkan");
    }
    additional_verified_count.store(additional_count);
}
}
extern "C" void qwen_app_register_additional_shader(const void*data,std::size_t bytes,const unsigned char*sha){
    if(initialized.load()||additional_count>=additional_shaders.size()||!data||!sha||!bytes||bytes>maximum_shader){registration_fault.store(true);return;}
    for(std::size_t i=0;i<additional_count;++i)if(additional_shaders[i].data==data){registration_fault.store(true);return;}
    auto&v=additional_shaders[additional_count++];v.data=static_cast<const unsigned char*>(data);v.bytes=bytes;std::copy_n(sha,32,v.sha.begin());
}
extern "C" std::uint64_t qwen_app_additional_shaders_verified(){return additional_verified_count.load();}
extern "C" std::uint64_t qwen_app_additional_shader_modules(){return additional_modules.load();}
'''

PREPARE=r'''
    for(std::size_t i=0;i<additional_count;++i){const auto&v=additional_shaders[i];
        if(storage!=v.data)continue;
        if(stored_bytes!=v.bytes||additional_verified_count.load()!=additional_count||
           digest(storage,stored_bytes)!=v.sha||failed.load())
            fail("Additional immutable shader lacks exact positive CPU SHA256 admission");
        *original_bytes=stored_bytes;*lease=nullptr;++additional_modules;return storage;
    }
'''

def transform(text):
    text=once(text,SINGLE_STATE,STATE)
    return once(text,SINGLE_PREPARE,PREPARE)

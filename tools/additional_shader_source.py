# SPDX-License-Identifier: MIT
"""Add one separately SHA256-qualified immutable shader without altering the pool."""
from build_speculative_batch_probe import once
STATE=r'''
namespace {
struct AdditionalShader {const unsigned char*data=nullptr;std::size_t bytes=0;std::array<unsigned char,32>sha{};};
AdditionalShader additional_shader;
std::atomic<bool>additional_verified{false};
std::atomic<std::uint64_t>additional_modules{0};
void verify_additional_shader(){
    if(!additional_shader.data)return;
    const auto&v=additional_shader;
    if(reinterpret_cast<std::uintptr_t>(v.data)%4||v.bytes<20||v.bytes>maximum_shader||v.bytes%4||u32(v.data)!=0x07230203)
        fail("Additional immutable shader exceeds its exact word-aligned SPIR-V scope");
    const auto actual=digest(v.data,v.bytes);
    if(actual!=v.sha)fail("Additional immutable shader complete SHA256 differs before Vulkan");
    additional_verified.store(true);
}
}
extern "C" void qwen_app_register_additional_shader(const void*data,std::size_t bytes,const unsigned char*sha){
    if(initialized.load()||additional_shader.data||!data||!sha||!bytes||bytes>maximum_shader){registration_fault.store(true);return;}
    additional_shader.data=static_cast<const unsigned char*>(data);additional_shader.bytes=bytes;std::copy_n(sha,32,additional_shader.sha.begin());
}
extern "C" std::uint64_t qwen_app_additional_shaders_verified(){return additional_verified.load()?1:0;}
extern "C" std::uint64_t qwen_app_additional_shader_modules(){return additional_modules.load();}
'''
PREPARE=r'''
    // Only the separately registered native constant may take this path. Its
    // complete startup and per-module SHA are mandatory; arbitrary raw input
    // still follows the original external-registry rejection below.
    if(storage==additional_shader.data&&stored_bytes==additional_shader.bytes){
        if(!additional_verified.load()||digest(storage,stored_bytes)!=additional_shader.sha||failed.load())
            fail("Additional immutable shader lacks exact positive CPU SHA256 admission");
        *original_bytes=stored_bytes;*lease=nullptr;++additional_modules;return storage;
    }
'''
def transform(text):
 text='#include "additional_shader_assets.h"\n'+text
 text=once(text,'namespace qwen_app {',STATE+'\nnamespace qwen_app {')
 text=once(text,'    heap_admission();initialized.store(true);','    verify_additional_shader();heap_admission();initialized.store(true);')
 text=once(text,'    *lease=nullptr;const auto *data=static_cast<const unsigned char*>(storage);',
     '    *lease=nullptr;const auto *data=static_cast<const unsigned char*>(storage);\n'+PREPARE)
 return text

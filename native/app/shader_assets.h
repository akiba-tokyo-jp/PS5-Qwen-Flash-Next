// SPDX-License-Identifier: MIT
#pragma once
#include "shader_assets_bridge.h"
#include <cstdint>
#include <string>
namespace qwen_app {
struct ShaderAssetStats {
    std::uint64_t assets=0,original_bytes=0,stored_bytes=0,maximum_shader_bytes=0;
    std::uint64_t decoded_calls=0,raw_calls=0,CPU_verified_assets=0;
    std::uint64_t lookup_entries=0,CPU_verified_lookups=0;
    std::uint64_t codec_output_bytes=0,codec_ordering_bytes=0,codec_scratch_bytes=0;
    bool initialized=false,active_lease=false,failed=false;
    std::string registry_sha256;
};
bool native_shader_assets_registered();
void initialize_native_shader_assets();
ShaderAssetStats verify_native_shader_assets_CPU();
ShaderAssetStats native_shader_asset_stats();
}

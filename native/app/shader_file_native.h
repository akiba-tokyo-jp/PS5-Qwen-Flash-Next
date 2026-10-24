// SPDX-License-Identifier: MIT
#pragma once
#include "shader_file.h"
#include "shader_file_bridge.h"
#include <string>
namespace qwen_app {
struct NativeShaderFileStats {
    bool registered=false,verified=false,failed=false,read_pending=false;
    std::uint64_t file_bytes=0,input_window_bytes=0,read_calls=0,returned_bytes=0,frame_requests=0;
};
bool native_shader_file_registered();
void quarantine_native_shader_file();
void initialize_native_shader_file(const std::string &,std::uint64_t,const std::string &);
// Only the existing exclusive codec producer may borrow this window. The file
// descriptor and window persist until ordinary OS close, including on failure.
const unsigned char *native_shader_file_frame(const void *,std::size_t,std::size_t);
NativeShaderFileStats native_shader_file_stats();
// The actual native implementation owns the read-only descriptor. Focused host
// controls supply a fixture provider while running the same session/file code.
ShaderFileOps &open_native_shader_file(const std::string &);
}

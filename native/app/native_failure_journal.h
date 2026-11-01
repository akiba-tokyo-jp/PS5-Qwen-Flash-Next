// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <cstdio>
extern "C" void qwen_native_stage(const char*);
namespace qwen_app {
inline void install_native_assertion_journal(){
 ggml_set_abort_callback([](const char*error){
  // Record the CPU assertion before preserving the library's normal abort.
  // This callback neither reports GPU completion nor attempts recovery.
  char text[640];std::snprintf(text,sizeof(text),"native_library_abort %s",error?error:"missing error");
  try{qwen_native_stage(text);}catch(...){ }
 });
}
}

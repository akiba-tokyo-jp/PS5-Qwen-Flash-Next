// SPDX-License-Identifier: MIT
#pragma once
#include "direct_bmp.h"
namespace qwen_app {
// The caller retains its aligned window after any failed operation. All
// padding is physical only: finish restores the exact original JSON length.
template<class Sink> void stream_direct_report(const void *bytes,std::size_t size,Sink &sink,void *window) {
    if(!bytes||!size||size>frame_write_window||!window||
       reinterpret_cast<std::uintptr_t>(window)%frame_write_alignment)
        throw std::invalid_argument("Bounded aligned metadata evidence is required");
    const auto padded=(size+frame_write_alignment-1)/frame_write_alignment*frame_write_alignment;
    const auto begun=sink.now_ns();
    if(!begun)throw std::runtime_error("Metadata persistence clock is unavailable");
    const auto bounded=[&]{const auto now=sink.now_ns();if(now<begun||now-begun>8000000000ull)
        throw std::runtime_error("Metadata persistence exceeded its original eight-second bound");};
    std::memset(window,0,padded);std::memcpy(window,bytes,size);
    bounded();if(sink.write(window,padded)!=static_cast<std::int64_t>(padded))
        throw std::runtime_error("Direct metadata write did not return its exact aligned count");
    bounded();sink.finish(size);bounded();
}
}

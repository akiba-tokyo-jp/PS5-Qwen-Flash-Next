// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace qwen_app {
inline constexpr std::size_t frame_write_alignment=16384,frame_write_window=1u<<20;
inline constexpr unsigned frame_width=1920,frame_height=1080;
inline constexpr std::size_t frame_row_bytes=frame_width*4;
inline constexpr std::uint64_t frame_bmp_bytes=54+std::uint64_t(frame_row_bytes)*frame_height;
inline std::array<unsigned char,54> frame_bmp_header() {
    std::array<unsigned char,54> h{};h[0]='B';h[1]='M';
    const auto u16=[&](unsigned at,std::uint16_t v){h[at]=v&255;h[at+1]=v>>8;};
    const auto u32=[&](unsigned at,std::uint32_t v){for(unsigned i=0;i<4;++i)h[at+i]=(v>>(8*i))&255;};
    u32(2,frame_bmp_bytes);u32(10,54);u32(14,40);u32(18,frame_width);u32(22,frame_height);
    u16(26,1);u16(28,32);u32(34,frame_row_bytes*frame_height);return h;
}
// Source copies exact bytes from one top-down raster row; the on-disk BMP stays
// byte-identical to the existing bottom-up, uncompressed 32-bit frame evidence.
template<class Source,class Sink>
void stream_direct_bmp(Source &source,Sink &sink,void *window) {
    if(!window || reinterpret_cast<std::uintptr_t>(window)%frame_write_alignment)
        throw std::invalid_argument("An owned aligned frame output window is required");
    auto *target=static_cast<unsigned char*>(window);const auto header=frame_bmp_header();
    const auto started=sink.now_ns();if(!started)throw std::runtime_error("Frame persistence clock is unavailable");
    for(std::uint64_t offset=0;offset<frame_bmp_bytes;) {
        const auto before=sink.now_ns();
        if(before<started || before-started>8000000000ull)throw std::runtime_error("Direct frame persistence deadline expired");
        const auto logical=std::size_t(std::min<std::uint64_t>(frame_write_window,frame_bmp_bytes-offset));
        std::size_t done=0;
        while(done<logical) {
            const auto at=offset+done;
            if(at<header.size()) {
                const auto n=std::min<std::size_t>(header.size()-std::size_t(at),logical-done);
                std::memcpy(target+done,header.data()+at,n);done+=n;
            } else {
                const auto pixel=at-header.size();const auto row=unsigned(pixel/frame_row_bytes);
                const auto within=std::size_t(pixel%frame_row_bytes);
                const auto n=std::min(frame_row_bytes-within,logical-done);
                source.copy_row(frame_height-1-row,within,target+done,n);done+=n;
            }
        }
        const auto physical=(logical+frame_write_alignment-1)&~(frame_write_alignment-1);
        std::memset(target+logical,0,physical-logical);
        if(sink.write(target,physical)!=std::int64_t(physical))
            throw std::runtime_error("Direct frame write did not complete exactly; backing retained");
        const auto after=sink.now_ns();
        if(after<before || after-started>8000000000ull)throw std::runtime_error("Direct frame write exceeded its deadline");
        offset+=logical;
    }
    sink.finish(frame_bmp_bytes);
    const auto finished=sink.now_ns();
    if(finished<started || finished-started>8000000000ull)throw std::runtime_error("Direct frame commit exceeded its deadline");
}
}

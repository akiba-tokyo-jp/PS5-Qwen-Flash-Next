// SPDX-License-Identifier: MIT
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

extern "C" bool __wrap_qwen_app_try_Q2_stream(const void *const *, const std::size_t *, unsigned,
    void *, void (*)(void *, unsigned, const void *));
extern "C" std::uint64_t qwen_iq2_stream_unused_request_bytes();

namespace {
std::array<std::vector<unsigned char>,12> sources, targets;
std::array<std::size_t,12> actual, logical_available, physical_bytes, skip;
std::array<const void*,12> addresses;
unsigned callbacks;
std::size_t rounded(std::size_t bytes) { return (bytes+16383)&~std::size_t(16383); }
void consume(void* owner,unsigned i,const void* data) {
    assert(owner==&callbacks&&i<12&&data==addresses[i]);
    std::memcpy(targets[i].data()+16,data,actual[i]);
    for(unsigned j=0;j<16;++j) assert(targets[i][j]==0xa7&&targets[i][16+actual[i]+j]==0xa7);
    assert(!std::memcmp(targets[i].data()+16,data,actual[i]));
    ++callbacks;
}
}

extern "C" bool __real_qwen_app_try_Q2_stream(const void*const* at,const std::size_t* bytes,
    unsigned count,void* owner,void(*callback)(void*,unsigned,const void*)) {
    // Model logical range and rounded physical EOF as separate preconditions.
    // The real unchanged owner additionally checks identities and overlap.
    for(unsigned i=0;i<count;++i) {
        assert(at[i]==addresses[i]&&(bytes[i]==537600||bytes[i]==460800));
        if(bytes[i]>logical_available[i]||rounded(skip[i]+bytes[i])>physical_bytes[i])return false;
    }
    for(unsigned i=0;i<count;++i)callback(owner,i,at[i]);
    return true;
}

int main() {
    for(unsigned i=0;i<12;++i) {
        const unsigned role=i%3;
        actual[i]=role==2?460800:(role==1||IQ2_STREAM_KIND==2?422400:537600);
        sources[i].resize(34*16384);
        for(std::size_t j=0;j<sources[i].size();++j)sources[i][j]=(j*17+i*31)%251;
        targets[i].assign(actual[i]+32,0xa7);
    }
    unsigned positive=0,negative=0;
    for(const std::size_t offset:{0u,512u,3584u,15872u}) {
        for(unsigned i=0;i<12;++i) {
            skip[i]=offset;addresses[i]=sources[i].data()+offset;
            logical_available[i]=actual[i]==422400?460800:actual[i];
            physical_bytes[i]=rounded(offset+logical_available[i]);
        }
        callbacks=0;const auto before=qwen_iq2_stream_unused_request_bytes();
        assert(__wrap_qwen_app_try_Q2_stream(addresses.data(),actual.data(),12,&callbacks,consume));
        assert(callbacks==12&&qwen_iq2_stream_unused_request_bytes()-before==4*38400ull*(IQ2_STREAM_KIND==2?2:1));
        ++positive;
        --physical_bytes[1];callbacks=0;const auto completed=qwen_iq2_stream_unused_request_bytes();
        assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(),actual.data(),12,&callbacks,consume));
        assert(callbacks==0&&qwen_iq2_stream_unused_request_bytes()==completed);
        ++negative;
    }
    physical_bytes[1]=sources[1].size();logical_available[1]=422400;
    callbacks=0;const auto completed=qwen_iq2_stream_unused_request_bytes();
    assert(!__wrap_qwen_app_try_Q2_stream(addresses.data(),actual.data(),12,&callbacks,consume));
    assert(callbacks==0&&qwen_iq2_stream_unused_request_bytes()==completed);
    ++negative;
    std::printf("{\"completed\":true,\"layout\":%d,\"new_alignment_positives\":%u,\"new_EOF_negatives\":%u,"
        "\"logical_and_physical_bounds_separate\":true,\"destination_canaries_exact\":true,\"PS5_operations\":0}\n",
        IQ2_STREAM_KIND,positive,negative);
}

// SPDX-License-Identifier: MIT
#include "source_read_latency.h"
#include <thread>
#include <iostream>
static_assert(sizeof(qwen_app::SourceReadLatency)==960,"Bounded diagnostic static counters required");
static_assert(std::atomic<std::uint64_t>::is_always_lock_free,"No hidden locking in read observations");
int main(){
    qwen_app::SourceReadLatency profile;
    profile.completed(16384,127999);profile.completed(32768,128000);
    const auto first=profile.snapshot();
    if(first[0]!=2||first[1]!=49152||first[2]!=255999||first[4]!=1||first[5]!=1)return 1;
    const auto lane=[&]{for(unsigned i=0;i<10000;++i)profile.completed(65536,8192000);};
    std::thread a(lane),b(lane);a.join();b.join();
    profile.completed(-1,1);const auto last=profile.snapshot();
    if(last[0]!=20003||last[1]!=49152+20000ull*65536||last[3]!=1||last[68]!=20000)return 2;
    std::uint64_t count=0;for(unsigned i=4;i<4+qwen_app::SourceReadLatency::bins;++i)count+=last[i];
    if(count+last[3]!=last[0]||last[2]-first[2]!=20000ull*8192000)return 3;
    std::uint64_t calls=0,bytes=0,ns=0;
    for(unsigned i=69;i<last.size();i+=3){calls+=last[i];bytes+=last[i+1];ns+=last[i+2];}
    if(calls!=count||bytes!=last[1]||ns!=last[2]||last[72]!=20000)return 4;
    std::cout<<"{\"concurrent_calls_verified\":20000,\"boundary_bins_and_error_accounting_passed\":true}\n";
}

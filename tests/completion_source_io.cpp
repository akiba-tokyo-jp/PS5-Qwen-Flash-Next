// SPDX-License-Identifier: MIT
#include "completion_source_io.h"
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <vector>
using qwen_app::CompletionRead;
using qwen_app::CompletionSourceIO;
struct Reader {
    std::mutex mutex;
    std::condition_variable changed;
    bool first_entered=false,allow_first=false,fail=false;
    unsigned active=0,maximum=0,calls=0;
    static int64_t read(void *value,unsigned,const CompletionRead &r) {
        auto &s=*static_cast<Reader *>(value);std::unique_lock<std::mutex> lock(s.mutex);
        ++s.calls;++s.active;s.maximum=std::max(s.active,s.maximum);
        if(r.id==1) {
            s.first_entered=true;s.changed.notify_all();
            if(!s.changed.wait_for(lock,std::chrono::seconds(3),[&]{return s.allow_first;}))std::abort();
        }
        const bool failed=s.fail;--s.active;s.changed.notify_all();return failed?-1:static_cast<int64_t>(r.bytes);
    }
};
static void require(bool ok){if(!ok)std::abort();}
template<class F>static void refuses(F f){bool caught=false;try{f();}catch(const std::exception &){caught=true;}require(caught);}
int main() {
    std::vector<unsigned char> memory(3*16384);
    auto at=(reinterpret_cast<uintptr_t>(memory.data())+16383)&~uintptr_t(16383);
    auto *a=reinterpret_cast<void *>(at),*b=reinterpret_cast<void *>(at+16384);
    Reader s;CompletionSourceIO queue(Reader::read,&s);queue.start();
    const CompletionRead first{3,a,16384,8u<<20,1},second{3,b,16384,9u<<20,2};
    queue.submit(0,first);
    {std::unique_lock<std::mutex> lock(s.mutex);require(s.changed.wait_for(lock,std::chrono::seconds(3),[&]{return s.first_entered;}));}
    refuses([&]{queue.submit(1,first);});
    queue.submit(1,second);auto result=queue.take(false);require(result.slot==1&&result.bytes==16384);
    refuses([&]{queue.submit(1,second);});refuses([&]{queue.stop_completed();});
    queue.release(1);auto third=second;third.id=3;queue.submit(1,third);
    result=queue.take(false);require(result.slot==1&&result.request.id==3);queue.release(1);
    {std::lock_guard<std::mutex> lock(s.mutex);s.allow_first=true;s.changed.notify_all();}
    result=queue.take(true);require(result.slot==0&&result.request.id==1);queue.release(0);
    refuses([&]{queue.release(0);});
    auto invalid=first;invalid.bytes=16385;refuses([&]{queue.submit(0,invalid);});
    invalid=first;invalid.target=reinterpret_cast<void *>(at+1);refuses([&]{queue.submit(0,invalid);});
    invalid=first;invalid.bytes=(4u<<20)+16384;refuses([&]{queue.submit(0,invalid);});
    invalid=first;invalid.offset=INT64_MAX;refuses([&]{queue.submit(0,invalid);});
    require(s.maximum==2&&s.calls==3);queue.stop_completed();refuses([&]{queue.submit(0,first);});
    Reader bad;bad.fail=true;bad.allow_first=true;CompletionSourceIO failed(Reader::read,&bad);failed.start();
    failed.submit(0,first);result=failed.take(false);require(result.bytes==-1);
    failed.release(0);refuses([&]{failed.submit(0,first);});failed.stop_completed();
    std::cout<<"{\"completion_driven_refill_while_other_read_pending\":true,\"maximum_outstanding_reads\":2,"
        "\"held_buffer_reuse_refused\":true,\"known_failure_drained_and_joined\":true,\"invalid_requests_refused\":true}\n";
}

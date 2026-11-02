// SPDX-License-Identifier: MIT
// Experimental request-end durability for the current three owned token ledgers.
#include "token_ledger_sync_gate.h"
#include <atomic>
#include <cerrno>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>

#ifndef QWEN_PERF_REQUEST_END_SYNC
#define QWEN_PERF_REQUEST_END_SYNC 0
#endif
extern "C" int __real_open(const char*,int,...);
extern "C" int __real_fsync(int);
extern "C" int __real_close(int);
extern "C" void qwen_native_stage(const char*);

namespace {
struct Hooks {
    int sync(int fd){return __real_fsync(fd);}
    int close(int fd){return __real_close(fd);}
    int error()const{return errno;}
    void set_error(int value){errno=value;}
} hooks;
qwen_service::TokenLedgerSyncGate<Hooks,bool(QWEN_PERF_REQUEST_END_SYNC)> gate(hooks);
std::atomic_flag gate_lock=ATOMIC_FLAG_INIT;
struct Lock {
    Lock(){while(gate_lock.test_and_set(std::memory_order_acquire)){} }
    ~Lock(){gate_lock.clear(std::memory_order_release);}
};
bool owned_ledger(const char*path,int flags){
    constexpr char prefix[]="/app0/qwen-runtime/plan-";
    if(!path||std::strncmp(path,prefix,sizeof(prefix)-1))return false;
    const auto*p=path+sizeof(prefix)-1;
    for(unsigned i=0;i<32;++i)if(!((p[i]>='0'&&p[i]<='9')||(p[i]>='a'&&p[i]<='f')))return false;
    p+=32;
    if(std::strncmp(p,".json.arm",9))return false;
    p+=9;
    return p[0]>='0'&&p[0]<='2'&&!std::strcmp(p+1,".token-ledger")&&
        (flags&(O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW))==(O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW);
}
}

extern "C" int __wrap_open(const char*path,int flags,...){
    int fd;
    if(flags&O_CREAT){va_list args;va_start(args,flags);const int mode=va_arg(args,int);va_end(args);fd=__real_open(path,flags,mode);}
    else fd=__real_open(path,flags);
    if(fd>=0&&owned_ledger(path,flags)){
        bool tracked;
        {Lock lock;tracked=gate.track(fd);}
        if(!tracked){const int saved=EMFILE;__real_close(fd);errno=saved;return -1;}
    }
    return fd;
}
extern "C" int __wrap_fsync(int fd){Lock lock;return gate.sync(fd);}
extern "C" int __wrap_close(int fd){
    decltype(gate)::Closed result;
    {Lock lock;result=gate.close(fd);}
    const int saved=errno;
    if(result.matched){
        char text[192];
        std::snprintf(text,sizeof(text),"R1_token_ledger_closed request_end=%u sync_requests=%u actual_syncs=%u close_rc=%d",
            unsigned(QWEN_PERF_REQUEST_END_SYNC),result.requests,result.syncs,result.rc);
        qwen_native_stage(text);
    }
    errno=saved;return result.rc;
}

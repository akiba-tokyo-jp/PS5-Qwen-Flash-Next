// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>

namespace qwen_service {
// Hooks preserve syscall results and errno. Only explicitly registered owned
// token ledgers change durability; other descriptors pass through unchanged.
template<class Hooks,bool RequestEnd> class TokenLedgerSyncGate {
    struct Row { int fd=-1;unsigned requests=0,syncs=0;bool dirty=false; } rows_[3];
    Hooks& hooks_;
public:
    struct Closed { int rc=0;bool matched=false;unsigned requests=0,syncs=0; };
    explicit TokenLedgerSyncGate(Hooks& hooks):hooks_(hooks){}
    bool tracks(int fd)const{for(const auto&row:rows_)if(row.fd==fd&&fd>=0)return true;return false;}
    bool track(int fd) {
        if(fd<0)return false;
        for(const auto&row:rows_)if(row.fd==fd)return false;
        for(auto&row:rows_)if(row.fd<0){row=Row{};row.fd=fd;return true;}
        return false;
    }
    int sync(int fd) {
        for(auto&row:rows_)if(row.fd==fd){
            ++row.requests;
            if(RequestEnd){row.dirty=true;return 0;}
            ++row.syncs;return hooks_.sync(fd);
        }
        return hooks_.sync(fd);
    }
    Closed close(int fd) {
        for(auto&row:rows_)if(row.fd==fd){
            int sync_error=0;
            if(row.dirty){++row.syncs;if(hooks_.sync(fd))sync_error=hooks_.error();}
            const int rc=hooks_.close(fd);const Closed result{sync_error?-1:rc,true,row.requests,row.syncs};
            row=Row{};
            if(sync_error)hooks_.set_error(sync_error);
            return result;
        }
        return Closed{hooks_.close(fd),false,0,0};
    }
};
}

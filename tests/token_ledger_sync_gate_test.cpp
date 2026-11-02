// SPDX-License-Identifier: MIT
#include "token_ledger_sync_gate.h"
#include <cassert>
#include <cstdio>
#include <vector>

struct Hooks {
    int current_error=0,sync_error=0,close_error=0;
    std::vector<int> synced,closed;
    int sync(int fd){synced.push_back(fd);if(sync_error){current_error=sync_error;return -1;}return 0;}
    int close(int fd){closed.push_back(fd);current_error=close_error;return close_error?-1:0;}
    int error()const{return current_error;}
    void set_error(int value){current_error=value;}
};

template<bool Deferred>void normal(){
    Hooks hooks;qwen_service::TokenLedgerSyncGate<Hooks,Deferred> gate(hooks);
    assert(!gate.track(-1));assert(gate.track(9));assert(!gate.track(9));
    for(unsigned i=0;i<22;++i)assert(gate.sync(9)==0);
    assert(hooks.synced.size()==(Deferred?0:22));
    const auto result=gate.close(9);
    assert(result.matched&&result.rc==0&&result.requests==22&&result.syncs==(Deferred?1:22));
    assert(hooks.closed==std::vector<int>{9});assert(hooks.synced.size()==(Deferred?1:22));
    assert(gate.track(9));const auto reused=gate.close(9);
    assert(reused.matched&&reused.requests==0&&reused.syncs==0);
}

int main(){
    normal<false>();normal<true>();
    {
        Hooks h;qwen_service::TokenLedgerSyncGate<Hooks,true> g(h);
        assert(g.sync(71)==0);const auto r=g.close(71);
        assert(!r.matched&&r.rc==0&&h.synced==std::vector<int>{71}&&h.closed==std::vector<int>{71});
        assert(g.track(1)&&g.track(2)&&g.track(3)&&!g.track(4));
        g.close(2);assert(g.track(4));
    }
    {
        Hooks h;qwen_service::TokenLedgerSyncGate<Hooks,true> g(h);assert(g.track(3));
        assert(g.sync(3)==0);h.sync_error=5;const auto r=g.close(3);
        assert(r.rc==-1&&r.matched&&r.requests==1&&r.syncs==1&&h.current_error==5);
        assert(h.closed==std::vector<int>{3});assert(g.track(3));
    }
    {
        Hooks h;qwen_service::TokenLedgerSyncGate<Hooks,false> g(h);assert(g.track(3));
        h.sync_error=4;assert(g.sync(3)==-1&&h.current_error==4);
        h.close_error=9;const auto r=g.close(3);assert(r.rc==-1&&h.current_error==9&&r.syncs==1);
    }
    {
        Hooks h;qwen_service::TokenLedgerSyncGate<Hooks,true> g(h);assert(g.track(3));
        assert(g.sync(3)==0);h.sync_error=5;h.close_error=9;const auto r=g.close(3);
        assert(r.rc==-1&&h.current_error==5&&h.closed.size()==1&&h.synced.size()==1);
        const auto unknown=g.close(91);assert(!unknown.matched&&unknown.rc==-1&&h.current_error==9);
    }
    std::puts("Token sync descriptor isolation, reuse, capacity and fault-injection controls passed; 22 -> 1 syncs.");
}

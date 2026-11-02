// SPDX-License-Identifier: MIT
#include "bounded_token_writer.h"
#include <algorithm>
#include <cassert>
#include <limits>
#include <string>
#include <vector>

struct Sink {
    std::string data,durable;
    std::vector<std::int64_t> writes;
    std::size_t next=0;
    unsigned syncs=0;
    bool interrupt=false,fail_sync=false,throw_sync=false;
    std::int64_t write(const char* value,std::size_t length) {
        auto n=next<writes.size()?writes[next++]:static_cast<std::int64_t>(length);
        if(n>0&&static_cast<std::uint64_t>(n)<=length)data.append(value,static_cast<std::size_t>(n));
        return n;
    }
    bool interrupted()const{return interrupt;}
    bool sync(){++syncs;if(throw_sync)throw std::runtime_error("Injected sync exception");if(fail_sync)return false;durable=data;return true;}
};
template<class F>void refuses(F f){bool caught=false;try{f();}catch(const std::exception&){caught=true;}assert(caught);}
int main(){
    using namespace qwen_service;
    // Partial writes and EINTR cannot truncate or duplicate a JSON record.
    Sink a;a.writes={-1,1,2,1};a.interrupt=true;
    BoundedTokenWriter<Sink> strict(a);
    strict.append("one\n",4);assert(a.data=="one\n"&&a.durable==a.data&&strict.syncs()==1);
    strict.append("two\n",4);strict.finish();assert(a.syncs==2&&strict.bytes()==8&&strict.records()==2);
    refuses([&]{strict.append("x",1);});
    // Default and deferred modes produce exactly the same complete bytes.
    Sink b;TokenLedgerPolicy p;p.durability=TokenDurability::request_end;
    BoundedTokenWriter<Sink> deferred(b,p);
    deferred.append("one\n",4);deferred.append("two\n",4);
    assert(b.durable.empty()&&deferred.dirty());deferred.finish();
    assert(b.data==a.data&&b.durable==a.durable&&b.syncs==1&&!deferred.dirty());
    // A failed synchronization cannot be retried as a successful request.
    Sink c;c.fail_sync=true;BoundedTokenWriter<Sink> failed(c,p);
    failed.append("lost\n",5);refuses([&]{failed.finish();});
    assert(failed.failed()&&failed.dirty()&&c.durable.empty());
    c.fail_sync=false;refuses([&]{failed.finish();});
    Sink exception;exception.throw_sync=true;BoundedTokenWriter<Sink> throwing(exception,p);
    throwing.append("x",1);refuses([&]{throwing.flush();});assert(throwing.failed()&&throwing.dirty());
    refuses([&]{throwing.finish();});
    // A partial failed write poisons the stream, rather than replaying a prefix.
    Sink d;d.writes={2,-1};BoundedTokenWriter<Sink> broken(d);
    refuses([&]{broken.append("four",4);});assert(d.data=="fo"&&broken.records()==0&&broken.failed());
    refuses([&]{broken.append("four",4);});assert(d.data=="fo");
    for(auto result:{std::int64_t(0),std::int64_t(5)}){
        Sink e;e.writes={result};BoundedTokenWriter<Sink> w(e);refuses([&]{w.append("four",4);});assert(w.failed());
    }
    Sink f;TokenLedgerPolicy small;small.max_records=2;small.max_bytes=6;small.max_record_bytes=4;
    BoundedTokenWriter<Sink> bounded(f,small);
    refuses([&]{bounded.append(nullptr,1);});refuses([&]{bounded.append("",0);});
    refuses([&]{bounded.append("large",5);});assert(f.data.empty());
    bounded.append("1234",4);refuses([&]{bounded.append("789",3);});bounded.append("56",2);
    refuses([&]{bounded.append("7",1);});bounded.finish();assert(f.data=="123456");
    // Accounting subtraction remains safe even with an explicit 64-bit limit.
    Sink g;TokenLedgerPolicy wide;wide.max_bytes=std::numeric_limits<std::uint64_t>::max();
    BoundedTokenWriter<Sink> large(g,wide);large.append("x",1);large.finish();assert(large.bytes()==1);
    Sink h;BoundedTokenWriter<Sink> empty(h,p);empty.finish();assert(h.syncs==0);
    for(unsigned invalid=0;invalid<4;++invalid){
        TokenLedgerPolicy bad;
        if(invalid==0)bad.max_records=0;
        if(invalid==1)bad.max_bytes=0;
        if(invalid==2)bad.max_record_bytes=bad.max_bytes+1;
        if(invalid==3)bad.durability=static_cast<TokenDurability>(999);
        refuses([&]{BoundedTokenWriter<Sink> rejected(h,bad);});
    }
    for(auto mode:{TokenDurability::per_token,TokenDurability::request_end}){
        Sink s;TokenLedgerPolicy many;many.durability=mode;many.max_records=256;many.max_bytes=1u<<20;
        BoundedTokenWriter<Sink> w(s,many);for(unsigned i=0;i<256;++i)w.append("{}\n",3);w.finish();
        assert(w.records()==256&&w.bytes()==768&&s.syncs==(mode==TokenDurability::per_token?256u:1u));
    }
}

// SPDX-License-Identifier: MIT
#include "immutable_span_prefetch.h"
#include <algorithm>
#include <cassert>
#include <map>
#include <vector>

using namespace qwen_app;
namespace {
constexpr std::size_t span=540672;
struct FakeIO {
    std::mutex mutex;
    std::map<int,ImmutableSpanIdentity> descriptors;
    int next=100,duplicates=0,closes=0;
    bool admitted=true,short_prediction=false;
    FakeIO(){ImmutableSpanIdentity i;i.device=4;i.inode=7;i.bytes=128ull<<20;i.mode=0100444;i.links=1;descriptors.emplace(3,i);}
    static unsigned char value(const ImmutableSpanIdentity&i,std::uint64_t offset,std::size_t n){return unsigned((i.inode+offset/16384+n*7)%256);}
    ImmutableSpanHooks hooks(const std::shared_ptr<FakeIO>&self){return {
        [self](int fd,ImmutableSpanIdentity&i){std::lock_guard<std::mutex>g(self->mutex);auto p=self->descriptors.find(fd);if(p==self->descriptors.end())return false;i=p->second;return true;},
        [self](int fd){std::lock_guard<std::mutex>g(self->mutex);const auto n=self->next++;self->descriptors.emplace(n,self->descriptors.at(fd));++self->duplicates;return n;},
        [self](int fd,void*p,std::size_t n,std::uint64_t offset)->std::ptrdiff_t{
            ImmutableSpanIdentity i;bool short_read;
            {std::lock_guard<std::mutex>g(self->mutex);i=self->descriptors.at(fd);short_read=self->short_prediction&&fd>=100;}
            const auto got=n-unsigned(short_read);auto*d=static_cast<unsigned char*>(p);
            for(std::size_t k=0;k<got;++k)d[k]=value(i,offset,k);return std::ptrdiff_t(got);
        },
        [self](int fd){std::lock_guard<std::mutex>g(self->mutex);++self->closes;return self->descriptors.erase(fd)==1;},
        [self](std::size_t){return self->admitted;},[](const char*){}
    };}
};
struct Fixture {
    std::shared_ptr<FakeIO> io=std::make_shared<FakeIO>();
    std::shared_ptr<std::vector<unsigned char>> allocation=std::make_shared<std::vector<unsigned char>>(span+16384);
    void*scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(allocation->data())+16383)&~std::uintptr_t(16383));
    ImmutableSpanPrefetch reader{io->hooks(io),scratch,span,allocation};
    std::vector<unsigned char> buffer=std::vector<unsigned char>(span+32,0xA5);
    void read(std::uint64_t offset){
        assert(reader.read(3,buffer.data()+16,span,offset)==std::ptrdiff_t(span));
        ImmutableSpanIdentity identity;{std::lock_guard<std::mutex>g(io->mutex);identity=io->descriptors.at(3);}
        for(std::size_t k=0;k<span;++k)assert(buffer[k+16]==FakeIO::value(identity,offset,k));
        for(unsigned k=0;k<16;++k)assert(buffer[k]==0xA5&&buffer[span+16+k]==0xA5);
    }
    ~Fixture(){reader.close_completed();assert(io->duplicates==io->closes&&io->descriptors.size()==1);}
};
}
int main(){
    {Fixture f;f.reader.begin_request(true);for(unsigned i=0;i<8;++i)f.read(i*span);f.reader.finish_request();auto s=f.reader.snapshot();
        assert(s.hits==6&&s.prefetch_calls==6&&s.foreground_calls==2&&s.unused==0&&s.hit_bytes==6*span);}
    {Fixture f;f.reader.begin_request(false);for(unsigned i=0;i<4;++i)f.read(i*span);f.reader.finish_request();auto s=f.reader.snapshot();assert(s.hits==0&&s.foreground_calls==4&&s.prefetch_calls==0);}
    {Fixture f;f.reader.begin_request(true);f.read(0);f.read(span);
        {std::lock_guard<std::mutex>g(f.io->mutex);++f.io->descriptors.at(3).inode;}
        f.read(2*span);f.reader.finish_request();auto s=f.reader.snapshot();assert(s.hits==0&&s.unused==1&&s.foreground_calls==3);}
    {Fixture f;f.io->short_prediction=true;f.reader.begin_request(true,1);f.read(0);f.read(span);f.read(2*span);f.reader.finish_request();auto s=f.reader.snapshot();assert(s.hits==0&&s.invalid==1&&s.foreground_calls==3&&s.prefetch_calls==1);}
    {Fixture f;f.io->admitted=false;f.reader.begin_request(true);for(unsigned i=0;i<4;++i)f.read(i*span);f.reader.finish_request();auto s=f.reader.snapshot();assert(s.declined==3&&s.prefetch_calls==0&&f.io->duplicates==0);}
    {Fixture f;f.reader.begin_request(true);f.read(0);f.read(span);f.read(5*span);f.reader.finish_request();auto s=f.reader.snapshot();assert(s.hits==0&&s.unused==2&&s.foreground_calls==3);}
    {Fixture f;f.reader.begin_request(true);f.read(0);f.read(span);bool refused=false;
        std::thread other([&]{try{f.reader.snapshot();}catch(const std::runtime_error&){refused=true;}});other.join();assert(refused);
        f.reader.finish_request();assert(f.reader.snapshot().unused==1);}
    {Fixture f;f.reader.begin_request(true);f.read(0);bool refused=false;try{f.reader.begin_request(true);}catch(const std::runtime_error&){refused=true;}assert(refused);f.reader.finish_request();}
}

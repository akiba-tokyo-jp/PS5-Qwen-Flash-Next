// SPDX-License-Identifier: MIT
#include "direct_report.h"
#include <cassert>
#include <string>
#include <vector>
struct Sink {
    std::uint64_t tick=100;bool short_write=false,closed=false,timeout=false;unsigned writes=0;
    std::vector<unsigned char> saved;
    std::uint64_t now_ns(){return timeout?(tick+=9000000000ull):++tick;}
    std::int64_t write(void *data,std::size_t bytes){++writes;auto *p=static_cast<unsigned char *>(data);saved.assign(p,p+bytes);return bytes-(short_write?1:0);}
    void finish(std::uint64_t bytes){saved.resize(bytes);closed=true;}
};
int main(){
    std::vector<unsigned char> storage(qwen_app::frame_write_window+qwen_app::frame_write_alignment);
    auto *window=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(storage.data())+
        qwen_app::frame_write_alignment-1)&~std::uintptr_t(qwen_app::frame_write_alignment-1));
    for(std::size_t bytes:{1u,16383u,16384u,16385u,1048576u}) {
        const std::string text(bytes,'x');Sink sink;
        qwen_app::stream_direct_report(text.data(),text.size(),sink,window);
        assert(sink.closed&&sink.writes==1&&sink.saved.size()==bytes);
        assert(!std::memcmp(sink.saved.data(),text.data(),bytes));
    }
    for(unsigned scenario=0;scenario<5;++scenario){
        Sink sink;const std::string text(scenario==4?1048577:1500,'y');
        sink.short_write=scenario==0;sink.timeout=scenario==1;bool refused=false;
        try{qwen_app::stream_direct_report(text.data(),scenario==2?0:text.size(),sink,scenario==3?window+1:window);}
        catch(const std::exception &){refused=true;}
        assert(refused&&!sink.closed&&sink.writes<2);
    }
}

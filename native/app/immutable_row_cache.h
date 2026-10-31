// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace qwen_app {
// Reader-local lifetime seals the source generation. File identities are still
// checked by the reader on every access; no scratch pointer is retained here.
class ImmutableRowCache {
    template<unsigned Bytes,unsigned Count>struct Bank {
        struct Row {std::uint64_t offset=0,tick=0;std::size_t file=0;bool valid=false;alignas(16)std::array<unsigned char,Bytes> data{};};
        std::array<Row,Count> rows{};
        const void*get(std::size_t file,std::uint64_t offset,std::uint64_t tick){
            for(auto&r:rows)if(r.valid&&r.file==file&&r.offset==offset){r.tick=tick;return r.data.data();}return nullptr;
        }
        void put(std::size_t file,std::uint64_t offset,const void*data,std::uint64_t tick){
            Row*victim=&rows[0];for(auto&r:rows){if(r.valid&&r.file==file&&r.offset==offset){victim=&r;break;}
                if(!r.valid){victim=&r;break;}if(r.tick<victim->tick)victim=&r;}
            std::memcpy(victim->data.data(),data,Bytes);victim->file=file;victim->offset=offset;victim->tick=tick;victim->valid=true;
        }
        void clear(){for(auto&r:rows)r.valid=false;}
    };
    Bank<320,1024> ple_;Bank<5120,32> embedding_;std::uint64_t tick_=0,hits_=0,misses_=0;
public:
    static constexpr std::size_t payload_bytes=320*1024+5120*32;
    const void*get(std::size_t file,std::uint64_t offset,std::size_t bytes){
        const void*p=bytes==320?ple_.get(file,offset,++tick_):bytes==5120?embedding_.get(file,offset,++tick_):nullptr;
        p?++hits_:++misses_;return p;
    }
    void put(std::size_t file,std::uint64_t offset,std::size_t bytes,const void*data){
        if(!data)throw std::invalid_argument("Completed owned row required");
        if(bytes==320)ple_.put(file,offset,data,++tick_);else if(bytes==5120)embedding_.put(file,offset,data,++tick_);
        else throw std::invalid_argument("Unsupported immutable row size");
    }
    void clear(){ple_.clear();embedding_.clear();tick_=0;}
    std::array<std::uint64_t,2>stats()const{return {hits_,misses_};}
};
}

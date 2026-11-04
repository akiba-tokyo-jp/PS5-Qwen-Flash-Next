// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace qwen_app {
// Two original640-column rows form one1280-element encoding row. Blocks
// straddle the original row boundary; padding individual rows is incorrect.
struct PairedIQ2Down {
    static constexpr unsigned columns=640,rows=2560,pair_bytes=330,matrix_bytes=422400;
    static constexpr unsigned address(unsigned row,unsigned column){
        return (row/2)*pair_bytes+(((row%2)*columns+column)/256)*66;
    }
    static float half(std::uint16_t bits){
        std::uint32_t sign=std::uint32_t(bits&0x8000)<<16,exp=(bits>>10)&31,mantissa=bits&1023,value;
        if(exp==0){
            if(!mantissa)value=sign;
            else{int shift=0;while(!(mantissa&1024)){mantissa<<=1;++shift;}
                value=sign|(std::uint32_t(113-shift)<<23)|((mantissa&1023)<<13);}
        }else value=sign|((exp==31?255:exp+112)<<23)|(mantissa<<13);
        float result;std::memcpy(&result,&value,4);return result;
    }
    static std::uint32_t u32(const unsigned char*data){
        return std::uint32_t(data[0])|(std::uint32_t(data[1])<<8)|(std::uint32_t(data[2])<<16)|(std::uint32_t(data[3])<<24);
    }
    static float decode(const unsigned char*data,unsigned row,unsigned column,const std::uint64_t*grid,const std::uint8_t*signs){
        const auto logical=(row%2)*columns+column,within=logical%256;
        const auto*block=data+address(row,column);const auto*group=block+2+(within/32)*8;
        const auto packed_signs=u32(group+4),sub=(within%32)/8,bit=within%8;
        const float scale=half(std::uint16_t(block[0])|(std::uint16_t(block[1])<<8));
        const float delta=scale*(0.5f+float(packed_signs>>28))*0.25f;
        const auto magnitude=(grid[group[sub]]>>(8*bit))&255;
        return (delta*float(magnitude))*((signs[(packed_signs>>(7*sub))&127]&(1u<<bit))?-1.0f:1.0f);
    }
};
static_assert(PairedIQ2Down::rows/2*PairedIQ2Down::pair_bytes==PairedIQ2Down::matrix_bytes);
static_assert(PairedIQ2Down::address(0,639)==132&&PairedIQ2Down::address(1,0)==132);
static_assert(PairedIQ2Down::address(1,639)==264&&PairedIQ2Down::address(2,0)==330);
}

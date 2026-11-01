// SPDX-License-Identifier: GPL-3.0-or-later
// Adapter for pinned powzix/ooz entropy decoding, not a hardware decoder.
// Callers provide 64 readable/writable padding bytes after source/target.
#include <stddef.h>
#include <stdint.h>
int Kraken_DecodeBytes(unsigned char**,const unsigned char*,const unsigned char*,int*,size_t,bool,unsigned char*,unsigned char*);
extern "C" int qwen_kraken_entropy(const unsigned char*source,size_t stored,unsigned char*target,size_t expected,unsigned char*scratch,size_t scratch_bytes){
    if(!source||!target||!scratch||!stored||!expected||expected>131072||stored>expected||scratch_bytes<0x6c000)return -1;
    unsigned char*out=target;int decoded=0;
    int used=Kraken_DecodeBytes(&out,source,source+stored,&decoded,expected,true,scratch,scratch+scratch_bytes);
    return used==static_cast<int>(stored)&&decoded==static_cast<int>(expected)&&out==target?0:-1;
}

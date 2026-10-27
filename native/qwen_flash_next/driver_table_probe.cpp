// SPDX-License-Identifier: MIT
#include "../app/driver_table_restore.h"
#include <cstdlib>
extern "C" int sceKernelMprotect(void *,std::size_t,int);
namespace {
struct Allocation {void *p=nullptr;std::size_t bytes=0;};
Allocation slots[8];std::size_t live=0,peak=0;bool fault=false;unsigned protection_calls=0;
voidpf allocate(voidpf,uInt n,uInt bytes){
    if(!n||!bytes||std::size_t(n)>(1u<<20)/bytes||std::size_t(n)*bytes>(1u<<20)-live){fault=true;return nullptr;}
    for(auto &s:slots)if(!s.p){s.p=std::calloc(n,bytes);s.bytes=std::size_t(n)*bytes;
        if(!s.p){fault=true;return nullptr;}live+=s.bytes;if(live>peak)peak=live;return s.p;}
    fault=true;return nullptr;
}
void release(voidpf,voidpf p){for(auto &s:slots)if(p&&s.p==p){std::free(p);live-=s.bytes;s={};return;}fault=true;}
int protect(void *p,std::size_t n){++protection_calls;return sceKernelMprotect(p,n,1);}
}
extern "C" std::size_t table_probe_count(){return qwen_driver_table_storage.count;}
extern "C" std::size_t table_probe_raw(){std::size_t n=0;for(std::size_t i=0;i<qwen_driver_table_storage.count;++i)n+=qwen_driver_table_storage.tables[i].bytes;return n;}
extern "C" std::size_t table_probe_packed(){return qwen_driver_table_storage.packed_bytes;}
extern "C" std::size_t table_probe_scratch_peak(){return peak;}
extern "C" int table_probe_restore(){return qwen_app::restore_driver_tables(qwen_driver_table_storage,allocate,release,nullptr,protect)&&!fault&&!live&&protection_calls==1;}

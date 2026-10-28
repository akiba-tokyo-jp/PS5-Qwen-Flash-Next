// SPDX-License-Identifier: MIT
#include "resident_direct_tables.h"
#include <array>
#include <iostream>
#include <string>
namespace {
constexpr std::size_t storage_bytes=9486336+32768;
unsigned char unaligned_storage[storage_bytes+16383];
unsigned char *storage=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(unaligned_storage)+16383)&~std::uintptr_t(16383));
std::array<qwen_driver_table,673> tables{};unsigned char packed=1;
std::string mode;unsigned allocations=0,mappings=0,queries=0;bool mapped=false;
void check(bool value){if(!value)throw std::runtime_error("Owned Direct table control failed");}
}
extern "C" const qwen_driver_table_plan qwen_driver_table_storage={tables.data(),tables.size(),&packed,1,storage+16384,storage+16384+9486336};
namespace qwen_app {
SystemMemoryObservation admit_native_system_memory(){return {436ull<<20,16384,100000,mode=="low"?1172u:2500u,898,2974,206};}
}
extern "C" std::int64_t sceKernelGetDirectMemorySize(){return 12ll<<30;}
extern "C" std::int32_t sceKernelAvailableDirectMemorySize(std::int64_t,std::int64_t,std::size_t alignment,std::int64_t *physical,std::size_t *available){
    check(alignment==65536);*physical=65536;*available=mode=="capacity"?9502720:(11ull<<30);return 0;}
extern "C" std::int32_t sceKernelAllocateDirectMemory(std::int64_t,std::int64_t,std::size_t bytes,std::size_t alignment,int type,std::int64_t *physical){
    ++allocations;check(bytes==9502720&&alignment==65536&&type==12);if(mode=="allocation")return -1;*physical=65536;return 0;}
extern "C" std::int32_t sceKernelMapDirectMemory(void **address,std::size_t bytes,int protection,int flags,std::int64_t physical,std::size_t alignment){
    ++mappings;check(*address==storage+16384&&bytes==9486336&&protection==3&&flags==0x10&&physical==65536&&alignment==16384);
    check(storage[16384]==0x5c);if(mode=="mapping")return -1;if(mode=="address")*address=storage+32768;mapped=true;return 0;}
extern "C" std::int32_t sceKernelQueryMemoryProtection(void *,void **begin,void **end,std::uint32_t *protection){
    ++queries;*begin=storage+16384;*end=storage+16384+9486336;*protection=3;
    if(mode=="query"&&!mapped)*end=storage+32768;if(mode=="post-query"&&mapped)*protection=1;return 0;}
int main(int argc,char **argv){try{
    mode=argc>1?argv[1]:"valid";std::memset(storage,0x5c,storage_bytes);
    std::size_t offset=0;for(unsigned i=0;i<673;++i){const auto bytes=i==672?9471408-offset:14000;
        tables[i]={storage+16384+offset,bytes,0,1,{}};offset+=bytes;}
    check(offset==9471408);if(mode=="overlap")tables[1].target=tables[0].target;if(mode=="outside")tables[0].target=storage;
    bool refused=false;try{qwen_app::map_resident_driver_tables_to_Direct();}catch(const std::exception &){refused=true;}
    const auto &owner=qwen_app::resident_direct_table_owner();
    if(mode=="valid"){
        check(!refused&&allocations==1&&mappings==1&&queries==2&&owner.allocated&&owner.mapped&&owner.zeroed);
        check(std::all_of(storage+16384,storage+16384+9486336,[](auto b){return b==0;}));
        check(std::all_of(storage,storage+16384,[](auto b){return b==0x5c;})&&std::all_of(storage+16384+9486336,storage+storage_bytes,[](auto b){return b==0x5c;}));
    }else{
        check(refused&&!owner.zeroed);
        if(mode=="low"||mode=="capacity"||mode=="query"||mode=="overlap"||mode=="outside")check(!allocations&&!mappings);
        if(mode=="mapping"||mode=="address"||mode=="post-query")check(owner.allocated&&mappings==1);
    }
    const auto calls=allocations+mappings+queries;refused=false;
    try{qwen_app::map_resident_driver_tables_to_Direct();}catch(const std::exception &){refused=true;}
    check(refused&&calls==allocations+mappings+queries);
    std::cout<<"{\"mode\":\""<<mode<<"\",\"owned_boundaries_preserved\":true,\"one_attempt\":true,\"backing_retained_after_map_error\":true}\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}

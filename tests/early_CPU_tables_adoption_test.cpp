// SPDX-License-Identifier: MIT
#include "early_CPU_tables_adoption.h"
#include <cstdio>
int main(){
    constexpr std::uintptr_t begin=0x4000000,end=begin+9486336;
    qwen_early_CPU_tables value{};value.begin=begin;value.end=begin+9502720;
    value.mapped_bytes=value.allocated_bytes=9502720;value.available_before=9502720+(256ull<<20);
    value.physical=65536;value.minimum_free=919;value.allocated=value.mapped=value.zeroed=1;
    value.checksum_passed=value.all_CPU_operations_returned=1;value.checksum=UINT64_C(17437583033832448805);
    auto valid=[&](const qwen_early_CPU_tables*r){qwen_app::require_early_CPU_table_backing(r,begin,end,9502720);};
    valid(&value);unsigned refused=0;
    auto reject=[&](auto change){auto bad=value;change(bad);try{valid(&bad);}catch(const std::exception&){++refused;return;}throw std::runtime_error("An invalid early CPU owner was admitted");};
    reject([](auto&r){++r.begin;});reject([](auto&r){--r.end;});
    reject([](auto&r){--r.mapped_bytes;});reject([](auto&r){--r.allocated_bytes;});
    reject([](auto&r){--r.available_before;});reject([](auto&r){r.physical=-1;});
    reject([](auto&r){++r.physical;});reject([](auto&r){r.status=1;});
    reject([](auto&r){r.allocated=0;});reject([](auto&r){r.mapped=0;});
    reject([](auto&r){r.zeroed=0;});reject([](auto&r){r.checksum_passed=0;});
    reject([](auto&r){r.all_CPU_operations_returned=0;});reject([](auto&r){++r.checksum;});
    reject([](auto&r){--r.minimum_free;});
    try{valid(nullptr);}catch(const std::exception&){++refused;}
    if(refused!=16)return 1;
    std::printf("{\"positive_controls\":1,\"negative_controls\":16,\"CPU_mapping_API_calls\":0}\n");
}

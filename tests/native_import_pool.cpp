// SPDX-License-Identifier: MIT
#include "../native/app/native_import_pool.h"
#include <cstring>
#include <iostream>
#include <stdexcept>
int main() {
    ps5_ai_flex_stats value;std::memset(&value,0xff,sizeof(value));ps5_ai_flex_snapshot(&value);
    const ps5_ai_flex_stats empty{};
    if(sizeof(value)!=72||ps5_ai_flex_pool_bytes()||std::memcmp(&value,&empty,sizeof(value))||
       ps5_ai_flex_grant_gpu(reinterpret_cast<void *>(0x10000),16384)||ps5_ai_flex_grant_gpu(nullptr,0))
        throw std::runtime_error("Unowned import pool or pointer was advertised");
    ps5_ai_flex_snapshot(nullptr);
    std::cout<<"Absent import-only pool reports exact zero ownership and rejects all host imports; no driver/kernel calls\n";
}

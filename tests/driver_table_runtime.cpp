// SPDX-License-Identifier: MIT
// Exercise the actual production wrapper, including its own admission call.
#include "driver_tables.h"
#include "system_memory.h"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <set>
namespace {std::set<void *> owned;unsigned observations=0,protections=0;bool low=false;}
extern "C" void *ps5_heap_calloc(std::size_t n,std::size_t size){void *p=std::calloc(n,size);if(p)owned.insert(p);return p;}
extern "C" int ps5_heap_owns(const void *p){return owned.count(const_cast<void *>(p))!=0;}
extern "C" void ps5_heap_free(void *p){if(!owned.erase(p))std::abort();std::free(p);}
extern "C" int mprotect(void *p,std::size_t n,int protection){
    if(p!=qwen_driver_table_storage.begin||n!=std::size_t(qwen_driver_table_storage.end-qwen_driver_table_storage.begin)||protection!=1)std::abort();
    ++protections;return 0;
}
namespace qwen_app {
SystemMemoryObservation admit_native_system_memory(){++observations;
    SystemMemoryObservation s{128u<<20,16384,138739,low?1665u:1666u,898,2974,206};
    (void)qualified_system_headroom(s);return s;
}
}
int main(int argc,char **argv){if(argc!=2)return 2;low=!std::strcmp(argv[1],"pressure");
    bool passed=false,refused=false;
    try{qwen_app::restore_native_driver_tables();passed=true;}
    catch(const qwen_app::KernelMemoryPressure &){refused=true;}
    if(observations!=1||!owned.empty()||passed==low||refused!=low||protections!=(low?0u:1u))return 1;
    bool repeated=false;try{qwen_app::restore_native_driver_tables();}catch(const std::exception &){repeated=true;}
    if(!repeated||observations!=1)return 1;
    std::cout<<"Production restoration wrapper: "<<(low?"known pressure refusal":"exact data and protection")<<"; no retry passed.\n";
}

// SPDX-License-Identifier: MIT
// Exercise the actual native snapshot body with malformed counter responses.
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <map>
#include <string>
#include <stdexcept>
#include <iostream>
struct Json:std::map<std::string,std::uint32_t>{static Json object(){return {};}};
static std::string mode;
static unsigned calls=0;
static int sysctlbyname(const char *name,void *target,std::size_t *bytes,const void *,std::size_t) {
    ++calls;std::uint32_t value=0;
    const std::map<std::string,std::uint32_t> counters={{"vm.stats.vm0.v_free_count",6031},
        {"vm.stats.vm0.v_active_count",29150},{"vm.stats.vm0.v_inactive_count",72528},
        {"vm.stats.vm0.v_wire_count",31030},{"vm.stats.vm0.v_page_count",138739}};
    value=counters.at(name);std::memcpy(target,&value,sizeof(value));
    if(calls==3) {
        if(mode=="query_failure")return -1;
        if(mode=="size_failure")*bytes=8;
        if(mode=="canary_failure")std::memset(static_cast<char*>(target)+8,0,8);
    }
    return 0;
}
#include "actual_native_vm_population.h"
int main(int argc,char **argv) {
    if(argc!=2)return 2;mode=argv[1];bool rejected=false;
    try {
        const auto v=diagnostic_VM_population();
        if(mode!="normal"||calls!=5||v.size()!=5||v.at("total")!=138739||
           v.at("free")+v.at("active")+v.at("inactive")+v.at("wired")!=v.at("total"))return 1;
    } catch(const std::runtime_error &) {rejected=true;}
    if((mode=="normal")?rejected:(!rejected||calls!=3))return 1;
    std::cout<<mode<<" actual native VM population control passed\n";
}

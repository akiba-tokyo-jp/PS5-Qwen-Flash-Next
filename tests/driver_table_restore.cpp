// SPDX-License-Identifier: MIT
#include "driver_table_restore.h"
#include <cstdlib>
#include <iostream>
#include <vector>
namespace {
std::size_t live=0;bool refuse=false;unsigned protected_calls=0;
voidpf allocate(voidpf,uInt n,uInt bytes){if(refuse||!n||!bytes||std::size_t(n)*bytes>(1u<<20))return nullptr;
    void *p=std::calloc(n,bytes);if(p)++live;return p;}
void release(voidpf,voidpf p){if(!p||!live)std::abort();std::free(p);--live;}
int protect(void *,std::size_t){++protected_calls;return 0;}
int bad_protect(void *,std::size_t){return -1;}
void require(bool b){static unsigned n=0;++n;if(!b){std::cerr<<"Restoration control failed: "<<n<<" live="<<live<<" protected="<<protected_calls<<"\n";std::exit(1);}}
}
int main(){
    auto p=qwen_driver_table_storage;const auto restore=[&](const auto &plan){return qwen_app::restore_driver_tables(plan,allocate,release,nullptr,protect);};
    std::cerr<<"Plan tables="<<p.count<<" begin="<<static_cast<void *>(p.begin)<<" end="<<static_cast<void *>(p.end)<<" packed="<<p.packed_bytes<<" z_stream="<<sizeof(z_stream)<<"\n";
    for(std::size_t i=0;i<p.count;++i){const auto &t=p.tables[i];
        if(t.target<p.begin||t.target+t.bytes>p.end)std::cerr<<"Outside table="<<i<<"\n";}
    require(restore(p)&&live==0&&protected_calls==1);
    std::vector<qwen_driver_table> tables(p.tables,p.tables+p.count);auto broken=p;broken.tables=tables.data();
    tables[0].sha256[0]^=1;require(!restore(broken)&&live==0&&protected_calls==1);tables[0]=p.tables[0];
    tables[0].offset=1;require(!restore(broken)&&live==0);tables[0]=p.tables[0];
    tables[0].target=p.end;require(!restore(broken)&&live==0);tables[0]=p.tables[0];
    require(p.count>1);tables[1].target=tables[0].target;require(!restore(broken)&&live==0);tables[1]=p.tables[1];
    std::vector<unsigned char> packed(p.packed,p.packed+p.packed_bytes);broken.packed=packed.data();packed[0]^=0xff;
    require(!restore(broken)&&live==0&&protected_calls==1);
    refuse=true;require(!restore(p)&&live==0);refuse=false;
    require(!qwen_app::restore_driver_tables(p,allocate,release,nullptr,bad_protect)&&live==0);
    require(restore(p)&&live==0&&protected_calls==2);
    std::cout<<"Actual NIR tables restored exactly; seven corruption/admission/protection controls passed.\n";
}

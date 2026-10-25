// SPDX-License-Identifier: MIT
#include "indexed_vector_admission.h"
#include <cassert>
#include <cmath>
#include <cstring>
#include <initializer_list>
int main() {
    for(unsigned columns:{640u,2560u})for(unsigned vectors:{1u,10u}) {
        unsigned changed=0;
        for(unsigned v=0;v<vectors;++v)for(unsigned c=0;c<columns;++c) {
            const float dyadic=qwen_app::indexed_fixture_input(c,v,false);
            const float full=qwen_app::indexed_fixture_input(c,v,true);
            std::uint32_t a=0,b=0;std::memcpy(&a,&dyadic,4);std::memcpy(&b,&full,4);
            assert(std::isfinite(dyadic)&&std::isfinite(full));
            assert((a&0xffffu)==0);
            if(full!=0){assert((b&0xffffu)!=0);++changed;}
            else assert(dyadic==0);
            assert(dyadic==float(int((c*11+v)%13)-6)/64.0f);
            assert(full==float(int((c*11+v)%13)-6)/63.0f);
        }
        assert(changed>columns*vectors*9/10);
    }
}

// SPDX-License-Identifier: MIT
#include "lean_prefill_policy.h"
#include <cassert>
int main(){
    for(unsigned mode=0;mode<6;++mode){
        const auto p=qwen_app::lean_prefill_policy(mode);
        assert(p.width==(4u<<(mode/2)));
        for(unsigned n=1;n<=p.width;++n){
            unsigned outputs=0;
            for(unsigned i=0;i<n;++i){
                outputs+=qwen_app::lean_prefill_output(p,true,i,n);
                assert(qwen_app::lean_prefill_output(p,false,i,n));
            }
            assert(outputs==(p.last_output_only?1:n));
        }
    }
    unsigned refused=0;
    try{qwen_app::lean_prefill_policy(6);}catch(const std::invalid_argument&){++refused;}
    try{qwen_app::lean_prefill_output({4,true},true,4,4);}catch(const std::invalid_argument&){++refused;}
    try{qwen_app::lean_prefill_output({4,true},true,0,5);}catch(const std::invalid_argument&){++refused;}
    try{qwen_app::lean_prefill_output({4,true},true,0,0);}catch(const std::invalid_argument&){++refused;}
    assert(refused==4);
}

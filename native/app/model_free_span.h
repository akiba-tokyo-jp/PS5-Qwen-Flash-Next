// SPDX-License-Identifier: MIT
#pragma once
#include "model_free_draft.h"
#include <array>
namespace qwen_app {
struct ModelFreeSpan {bool found=false;std::array<std::int32_t,3> tokens{};std::size_t matches=0;};
// All three continuation tokens must already exist in each historical match.
// Proposed, unverified tokens are never passed off as committed history.
inline ModelFreeSpan propose_model_free_span(const std::int32_t*prompt,std::size_t pn,
 const std::int32_t*history,std::size_t hn,std::size_t vocabulary){
    (void)propose_model_free_token(prompt,pn,history,hn,vocabulary,DraftEvidence::consistent_pair);
    if(hn<1)return {};
    const auto search=[&](const std::int32_t*source,std::size_t count,unsigned minimum){
        const auto maximum=std::min<std::size_t>({4,hn,count>=3?count-3:0});
        if(maximum<minimum)return ModelFreeSpan{};
        for(auto n=maximum;;--n){ModelFreeSpan result;bool conflict=false;
            for(std::size_t at=0;at+n+3<=count;++at){
                if(!std::equal(history+hn-n,history+hn,source+at))continue;
                std::array<std::int32_t,3> span{};std::copy_n(source+at+n,3,span.begin());
                if(!result.matches)result.tokens=span;else if(result.tokens!=span)conflict=true;
                ++result.matches;
            }
            if(result.matches>=2&&!conflict){result.found=true;return result;}
            if(n==minimum)break;
        }
        return ModelFreeSpan{};
    };
    const auto own=search(history,hn,1);return own.found?own:search(prompt,pn,2);
}
}

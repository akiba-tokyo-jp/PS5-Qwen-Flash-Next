// SPDX-License-Identifier: MIT
#pragma once
#include "decode_prefill_protection.h"
#include <array>

namespace qwen_app {
// Experimental metadata only. The caller binds the already tokenized prompt
// before any prefill route; no future route or unaccepted token is consulted.
class AdaptivePrefillProtection {
    DecodePrefillProtection history_;
    std::vector<std::int32_t> previous_prompt_,prompt_;
    std::vector<bool> selected_=std::vector<bool>(49*512,false);
    bool prompt_equal_=false,enabled_=false;
public:
    void begin(bool enabled,bool clear){
        enabled_=enabled;history_.begin(enabled,clear);
        if(clear)previous_prompt_.clear();prompt_.clear();prompt_equal_=false;
        std::fill(selected_.begin(),selected_.end(),false);
    }
    void bind_prompt(const std::vector<std::int32_t>&tokens){
        if(tokens.empty()||tokens.size()>256)throw std::invalid_argument("Bounded nonempty prompt required");
        prompt_=tokens;prompt_equal_=prompt_==previous_prompt_;
    }
    const std::vector<bool>*prepare(int layer,const std::vector<int>&ids,bool decode,
                                    bool require_same_prompt,unsigned denominator){
        const auto*base=history_.keys(decode);
        if(!base||!enabled_||(require_same_prompt&&!prompt_equal_))return nullptr;
        if(!denominator)return base;
        if(layer<0||layer>=48||ids.empty())throw std::invalid_argument("Observed prefill geometry required");
        if(denominator!=2&&denominator!=4&&denominator!=8)throw std::invalid_argument("Unsupported overlap threshold");
        std::array<bool,512>seen{};unsigned unique=0,overlap=0;
        for(int id:ids){if(id<0||id>=512)throw std::invalid_argument("Observed Expert exceeds geometry");
            if(!seen[id]){seen[id]=true;++unique;overlap+=(*base)[layer*512+id];}}
        // Only this already observed layer gains or loses protection. Other
        // layers have no newly inferred overlap and remain unprotected.
        for(unsigned id=0;id<512;++id)selected_[layer*512+id]=overlap*denominator>=unique&&(*base)[layer*512+id];
        return &selected_;
    }
    void observe(int layer,const std::vector<int>&ids,bool decode){history_.observe(layer,ids,decode);}
    void commit(){if(prompt_.empty())throw std::logic_error("Bind prompt before accepting a token");history_.commit();previous_prompt_=prompt_;}
};
}

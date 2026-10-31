// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <vector>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
class DecodePrefillProtection {
    std::vector<int>recent_,committed_;
    std::vector<bool>protected_=std::vector<bool>(49*512,false);
    bool enabled_=false;
public:
    DecodePrefillProtection(){recent_.reserve(1536);committed_.reserve(1536);}
    void begin(bool enabled,bool clear){
        enabled_=enabled;if(clear)committed_.clear();std::fill(protected_.begin(),protected_.end(),false);
        if(enabled)for(int key:committed_)protected_.at(key)=true;recent_.clear();
    }
    void observe(int layer,const std::vector<int>&ids,bool decode){
        if(!decode)return;for(int id:ids){if(layer<0||layer>=48||id<0||id>=512)throw std::invalid_argument("Decode history key exceeds source geometry");
            int key=layer*512+id;auto it=std::find(recent_.begin(),recent_.end(),key);if(it!=recent_.end())recent_.erase(it);
            else if(recent_.size()==1536)recent_.erase(recent_.begin());recent_.push_back(key);}
    }
    // Called only for an emitted accepted token; EOS and rejected-only work do
    // not become the committed history of a later independent request.
    void commit(){committed_=recent_;}
    const std::vector<bool>*keys(bool decode)const{return enabled_&&!decode?&protected_:nullptr;}
};
}

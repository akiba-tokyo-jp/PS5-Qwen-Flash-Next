// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <array>
#include <stdexcept>
#include <thread>
#include <unordered_set>
#include <vector>
namespace qwen_app {
// Retain only CPU topology. A positively synchronized scheduler must allocate
// every restored graph again; no GPU allocation or completion state is cached.
class WidthGraphBindings {
    struct Links{ggml_tensor*node;std::array<ggml_tensor*,GGML_MAX_SRC>source;decltype(ggml_tensor::flags) flags;};
    struct Allocation{ggml_tensor*tensor;void*extra;};
    std::vector<Links>links_;
    std::vector<Allocation>unallocated_;
    std::thread::id owner_{};bool valid_=false;
    void owner(){if(owner_!=std::this_thread::get_id())throw std::runtime_error("Graph topology has another CPU producer");}
public:
    bool valid()const noexcept{return valid_;}
    void clear(){if(valid_)owner();links_.clear();unallocated_.clear();valid_=false;}
    void capture(ggml_tensor*const*nodes,std::size_t count,ggml_tensor*const*leaves,std::size_t leaf_count){
        if(count>65536||leaf_count>65536||(!nodes&&count)||(!leaves&&leaf_count))throw std::invalid_argument("Graph topology exceeds its bounded scope");
        clear();owner_=std::this_thread::get_id();std::unordered_set<ggml_tensor*>seen;
        const auto remember=[&](ggml_tensor*t){if(t&&seen.insert(t).second&&!t->data&&!t->buffer)unallocated_.push_back({t,t->extra});};
        for(std::size_t i=0;i<leaf_count;++i)remember(leaves[i]);
        for(std::size_t i=0;i<count;++i){auto*t=nodes[i];if(!t)throw std::invalid_argument("Graph node is missing");Links row{t,{},t->flags};
            remember(t);remember(t->view_src);for(unsigned j=0;j<GGML_MAX_SRC;++j){row.source[j]=t->src[j];remember(t->src[j]);}
            links_.push_back(row);
        }valid_=true;
    }
    void restore_after_positive_sync(){
        owner();if(!valid_)throw std::runtime_error("No original graph topology was captured");
        for(const auto&row:links_){row.node->flags=row.flags;for(unsigned j=0;j<GGML_MAX_SRC;++j)row.node->src[j]=row.source[j];}
        // Never dereference a stale backend buffer. Only tensors that had no
        // allocation before scheduling are rebound. External weights/KV stay.
        for(const auto&row:unallocated_){row.tensor->data=nullptr;row.tensor->buffer=nullptr;row.tensor->extra=row.extra;}
    }
    std::uint64_t retained_bytes()const noexcept{return links_.capacity()*sizeof(Links)+unallocated_.capacity()*sizeof(Allocation);}
};
}

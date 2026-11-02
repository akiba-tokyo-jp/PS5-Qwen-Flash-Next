// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace qwen_app {
// Retain NextN rows at the original target synchronization boundary, before a
// compact rejection restore may invalidate them. No process is added/replayed.
// All hooks execute on the original GPU producer inside its owned epoch.
template<std::size_t Elements=10240>class MtpTargetHiddenCapture {
public:
    using Hidden=std::array<float,Elements>;
    struct Hooks {float*(*get)(void*,int)=nullptr;void(*synchronize)(void*)=nullptr;};
private:
    struct Batch {void*batch=nullptr;void*context=nullptr;unsigned tokens=0;};
    std::array<Batch,16>batches_{};
    void*target_=nullptr;Hooks hooks_;
    Hidden first_{},last_{};
    std::uint64_t serial_=0;
    unsigned pending_width_=0,last_width_=0;
    bool pending_=false,capturing_=false,failed_=false,valid_=false;
    Batch*find(void*batch){for(auto&row:batches_)if(row.batch==batch)return &row;return nullptr;}
    bool copy(Hidden&to,int index){
        const auto*data=hooks_.get(target_,index);hooks_.synchronize(target_);
        if(!data)return false;
        std::copy_n(data,Elements,to.begin());
        return std::all_of(to.begin(),to.end(),[](float value){return std::isfinite(value);});
    }
public:
    explicit MtpTargetHiddenCapture(Hooks hooks):hooks_(hooks){}
    void bind_target(void*context){
        if(!context||pending_||capturing_||!hooks_.get||!hooks_.synchronize){failed_=true;return;}
        target_=context;serial_=0;last_width_=0;valid_=false;
    }
    void batch_created(void*batch,void*context){
        if(!batch||!context)return;
        auto*row=find(batch);
        if(!row)for(auto&slot:batches_)if(!slot.batch){row=&slot;break;}
        if(!row){failed_=true;return;}*row={batch,context,0};
    }
    void batch_freed(void*batch){if(auto*row=find(batch))*row={};}
    void batch_cleared(void*batch){if(auto*row=find(batch))row->tokens=0;}
    void token_added(void*batch,int actual_index){
        if(auto*row=find(batch)){
            if(actual_index<0||actual_index>=256){if(row->context==target_)failed_=true;return;}
            row->tokens=std::max(row->tokens,unsigned(actual_index)+1);
        }
    }
    void original_process_returned(void*context,void*batch,int result){
        if(context!=target_)return;
        auto*row=find(batch);
        if(result||pending_||capturing_||!row||row->context!=context||!row->tokens){failed_=true;valid_=false;return;}
        pending_width_=row->tokens;pending_=true;valid_=false;
    }
    void original_synchronize_returned(void*context){
        if(context!=target_||!pending_||capturing_)return;
        pending_=false;capturing_=true;
        // Clear pending before either getter; the pinned getter may synchronize
        // recursively. Its own nested synchronization cannot capture twice.
        const bool first_ok=copy(first_,pending_width_==2?0:-1);
        bool last_ok=first_ok;
        if(pending_width_==2)last_ok=copy(last_,1);else last_=first_;
        last_width_=pending_width_;++serial_;valid_=first_ok&&last_ok;
        if(!valid_)failed_=true;
        capturing_=false;
    }
    bool valid()const noexcept{return valid_&&!failed_&&!pending_&&!capturing_;}
    bool failed()const noexcept{return failed_;}
    unsigned last_width()const noexcept{return last_width_;}
    std::uint64_t serial()const noexcept{return serial_;}
    const Hidden&first()const noexcept{return first_;}
    const Hidden&last()const noexcept{return last_;}
};
}

// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Causal CPU bookkeeping only. The caller commits each transition after its
// actual GPU fence/checkpoint and retains this object on unknown completion.
// A target-accepted draft must enter auxiliary KV before the next proposal.
template<std::size_t HiddenElements=10240>
class PersistentMtpCursor {
public:
    using Hidden=std::array<float,HiddenElements>;
    struct Input {std::int32_t token=-1,position=-1;Hidden hidden{};};
private:
    Hidden live_{},accepted_first_{};
    std::int32_t position_=0,auxiliary_next_=0,pending_=-1,accepted_draft_=-1;
    bool ready_=false,sampled_=false,pending_valid_=false,proposal_=false,auxiliary_pending_done_=false;
    bool catchup_=false,bonus_=false;
    static void require(bool condition){if(!condition)throw std::logic_error("Inconsistent persistent MTP causal transition");}
public:
    void reset(std::int32_t prompt_tokens,const Hidden&hidden){
        require(prompt_tokens>0&&prompt_tokens<256&&!proposal_&&!catchup_);
        live_=hidden;position_=auxiliary_next_=prompt_tokens;pending_=-1;accepted_draft_=-1;
        ready_=true;sampled_=false;pending_valid_=false;auxiliary_pending_done_=false;bonus_=false;
    }
    void first_sample(std::int32_t token,bool end=false){
        require(ready_&&!sampled_&&!pending_valid_&&!proposal_&&!catchup_&&!bonus_&&(end||token>=0));
        sampled_=true;pending_=token;pending_valid_=!end;
    }
    Input proposal_input(){
        require(ready_&&pending_valid_&&!proposal_&&!catchup_&&!bonus_&&auxiliary_next_==position_&&position_<255);
        proposal_=true;auxiliary_pending_done_=false;return {pending_,position_,live_};
    }
    void auxiliary_pending_completed(){
        require(proposal_&&!auxiliary_pending_done_&&auxiliary_next_==position_);
        ++auxiliary_next_;auxiliary_pending_done_=true;
    }
    void target_single_completed(std::int32_t next_token,const Hidden&hidden,bool end=false){
        require(proposal_&&auxiliary_pending_done_&&!catchup_&&!bonus_&&(end||next_token>=0));
        ++position_;live_=hidden;pending_=next_token;pending_valid_=!end;proposal_=false;auxiliary_pending_done_=false;
        require(auxiliary_next_==position_);
    }
    void target_pair_completed(std::int32_t draft,bool accepted,std::int32_t next_token,
            const Hidden&first_hidden,const Hidden&last_hidden,bool end=false){
        require(proposal_&&auxiliary_pending_done_&&!catchup_&&!bonus_&&draft>=0&&(end||next_token>=0)&&position_<254);
        proposal_=false;auxiliary_pending_done_=false;pending_=next_token;pending_valid_=!end;
        if(accepted){
            position_+=2;live_=last_hidden;accepted_first_=first_hidden;accepted_draft_=draft;catchup_=true;bonus_=true;
            require(auxiliary_next_==position_-1);
        }else{
            ++position_;live_=first_hidden;require(auxiliary_next_==position_);
        }
    }
    Input accepted_draft_catchup_input()const{
        require(catchup_&&!proposal_&&auxiliary_next_==position_-1);
        return {accepted_draft_,position_-1,accepted_first_};
    }
    void accepted_draft_catchup_completed(){
        require(catchup_&&!proposal_&&auxiliary_next_==position_-1);++auxiliary_next_;catchup_=false;accepted_draft_=-1;
    }
    void queued_bonus_observed(std::int32_t token,bool end=false){
        require(bonus_&&!catchup_&&!proposal_&&auxiliary_next_==position_&&token==pending_&&pending_valid_==!end);
        bonus_=false;
    }
    bool has_pending()const noexcept{return pending_valid_;}
    bool catchup_required()const noexcept{return catchup_;}
    bool bonus_pending()const noexcept{return bonus_;}
    std::int32_t position()const noexcept{return position_;}
    std::int32_t auxiliary_next_position()const noexcept{return auxiliary_next_;}
};
}

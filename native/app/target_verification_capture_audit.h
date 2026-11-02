// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include "mtp_target_hidden_capture.h"
#include <functional>
#include <nlohmann/json.hpp>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
struct TargetVerificationDecision {
    unsigned attempts=0,accepted=0,rejected=0,queued_bonus=0;
};
struct TargetVerificationCaptureHooks {
    std::function<Token(std::int32_t)>verify;
    std::function<TargetVerificationDecision()>decision;
    std::function<const MtpTargetHiddenCapture<>*()>capture;
};
// Two diagnostic drafts for the fixed counting cohort. Only the original
// target verifier chooses output. A returned semantic negative remains a
// healthy completed result rather than quarantining positively completed GPU work.
class TargetVerificationCaptureAudit final:public Engine {
    using Json=nlohmann::json;
    Engine&ordinary_;TargetVerificationCaptureHooks hooks_;
    Json observations_=Json::array();
    unsigned prompt_=0,calls_=0;bool checks_=true,closed_=false,first_accepted_=false;
    static std::string digest(const MtpTargetHiddenCapture<>::Hidden&hidden){
        sha256_t hash;sha256_init(&hash);sha256_update(&hash,reinterpret_cast<const unsigned char*>(hidden.data()),hidden.size()*sizeof(float));
        unsigned char bytes[32];sha256_final(&hash,bytes);std::string value;
        for(auto byte:bytes){value+="0123456789abcdef"[byte>>4];value+="0123456789abcdef"[byte&15];}return value;
    }
public:
    TargetVerificationCaptureAudit(Engine&ordinary,TargetVerificationCaptureHooks hooks):ordinary_(ordinary),hooks_(std::move(hooks)){
        if(!hooks_.verify||!hooks_.decision||!hooks_.capture)throw std::invalid_argument("Complete original target verification/capture hooks required");
    }
    std::uint32_t tokenize(const std::string&text)override{prompt_=ordinary_.tokenize(text);return prompt_;}
    void prefill(std::uint32_t capacity)override{
        ordinary_.prefill(capacity);const auto*c=hooks_.capture();
        checks_&=capacity==256&&prompt_==30&&c&&c->valid()&&c->last_width()==prompt_;
    }
    Token next()override{
        const auto before=hooks_.decision();const auto*c=hooks_.capture();const auto serial=c?c->serial():0;
        const bool pair=calls_==1||calls_==3;const std::int32_t draft=calls_==1?11:42;
        const auto token=pair?hooks_.verify(draft):ordinary_.next();
        const auto after=hooks_.decision();c=hooks_.capture();
        const auto delta=c?c->serial()-serial:0;const unsigned width=c?c->last_width():0;
        bool decision=true;
        if(pair){
            decision=after.attempts==before.attempts+1&&after.accepted+after.rejected==before.accepted+before.rejected+1;
            if(calls_==1){first_accepted_=after.accepted==before.accepted+1;
                decision&=first_accepted_&&token.id==draft&&delta==1&&width==2;}
            else decision&=after.rejected==before.rejected+1&&token.id!=draft&&
                ((delta==1&&width==2)||(delta==2&&width==1));
        }else if(calls_==0)decision=delta==0;
        else if(calls_==2&&first_accepted_)decision=delta==0&&after.queued_bonus==before.queued_bonus+1;
        else decision=delta==1&&width==1;
        const bool valid=c&&c->valid();checks_&=decision&&valid;
        Json row={{"call",calls_},{"pair",pair},{"returned_token",token.id},{"end",token.end_of_generation},
            {"capture_valid",valid},{"capture_serial_delta",delta},{"last_process_width",width},{"decision_check_passed",decision},
            {"target_attempts",after.attempts},{"target_accepted",after.accepted},{"target_rejected",after.rejected},
            {"queued_bonus_samples",after.queued_bonus}};
        if(pair)row["controlled_draft"]=draft;
        if(valid){row["first_hidden_sha256"]=digest(c->first());row["last_hidden_sha256"]=digest(c->last());}
        observations_.push_back(std::move(row));++calls_;return token;
    }
    void finish()override{ordinary_.finish();closed_=true;}
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return ordinary_.expert_cache_metrics();}
    Json report()const{
        const auto decision=hooks_.decision();
        return {{"completed",closed_},{"capture_and_decision_checks_passed",checks_&&decision.attempts==2&&decision.accepted==1&&decision.rejected==1},
            {"actual_target_attempts",decision.attempts},{"actual_target_accepted",decision.accepted},{"actual_target_rejected",decision.rejected},
            {"hidden_elements",10240},{"original_target_process_calls_added_by_capture",0},{"auxiliary_contexts",0},
            {"only_original_target_verified_tokens_emitted",true},{"controlled_drafts",Json::array({11,42})},
            {"observations",observations_},{"MTP_proposals_used",0},{"online_MTP_scheduling_qualified",false},{"whole_speed_qualified",false}};
    }
};
}

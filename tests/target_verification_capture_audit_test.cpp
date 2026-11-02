// SPDX-License-Identifier: MIT
#include "target_verification_capture_audit.h"
#include "first_generation.h"
#include <cassert>
namespace {
using Capture=qwen_app::MtpTargetHiddenCapture<>;
struct Context {Capture::Hidden first{},last{};};
Capture*observer=nullptr;bool active=false;
float*get(void*context,int index){
    assert(active);observer->original_synchronize_returned(context);
    auto&value=*static_cast<Context*>(context);return index==0?value.first.data():value.last.data();
}
void synchronize(void*context){assert(active);observer->original_synchronize_returned(context);}
class Target final:public qwen_app::Engine {
    Context&context_;Capture&capture_;int batch_=0;
    unsigned emitted_=0,position_=30;bool bonus_=false;
    const std::vector<int>tokens_{16,11,220,17,11,220,18,11,220,19,11,220,20,11,220,21,11,220,22,11,220,23,248046};
    void process(unsigned count){
        assert(!active);active=true;capture_.batch_cleared(&batch_);
        for(unsigned i=0;i<count;++i)capture_.token_added(&batch_,i);
        context_.first.fill(float(position_));context_.last.fill(float(position_+count-1));
        capture_.original_process_returned(&context_,&batch_,0);capture_.original_synchronize_returned(&context_);active=false;
    }
    qwen_app::Token emit(){const auto token=tokens_.at(emitted_++);return {token,std::to_string(token),token==248046};}
public:
    qwen_app::TargetVerificationDecision stats{};unsigned finishes=0;
    Target(Context&context,Capture&capture):context_(context),capture_(capture){capture_.batch_created(&batch_,&context_);capture_.bind_target(&context_);}
    std::uint32_t tokenize(const std::string&)override{return 30;}
    void prefill(std::uint32_t capacity)override{assert(capacity==256);process(30);}
    qwen_app::Token next()override{
        if(bonus_){bonus_=false;++stats.queued_bonus;return emit();}
        if(emitted_){process(1);++position_;}return emit();
    }
    qwen_app::Token verify(int draft){
        assert(emitted_&&!bonus_);++stats.attempts;process(2);
        if(draft==tokens_.at(emitted_)){++stats.accepted;bonus_=true;position_+=2;}
        else{++stats.rejected;++position_;
            // Emulate a completed compact rollback invalidating the original
            // downloaded rows before the caller receives the rejected result.
            context_.first.fill(0);context_.last.fill(0);}
        return emit();
    }
    void finish()override{++finishes;}
};
}
int main(){
    Context context;Capture capture({get,synchronize});observer=&capture;Target target(context,capture);
    qwen_app::TargetVerificationCaptureHooks hooks;
    hooks.verify=[&](int draft){return target.verify(draft);};hooks.decision=[&]{return target.stats;};hooks.capture=[&]{return &capture;};
    qwen_app::TargetVerificationCaptureAudit audit(target,std::move(hooks));qwen_app::FirstGeneration generation(audit);
    const auto&result=generation.run({"capture_controls","counting control",256,32},[](const auto&){},[](const auto&,const auto&){},[](const char*){});
    assert(result.request_reset_completed&&result.metrics.prompt_tokens==30&&result.token_ids.size()==22&&target.finishes==1&&!active);
    const auto report=audit.report();assert(report.at("capture_and_decision_checks_passed")==true);
    assert(report.at("actual_target_attempts")==2&&report.at("actual_target_accepted")==1&&report.at("actual_target_rejected")==1);
    const auto rows=report.at("observations");assert(rows.size()==23&&rows[2].at("capture_serial_delta")==0&&rows[3].at("last_process_width")==2);
    assert(rows[3].at("first_hidden_sha256")!=rows[3].at("last_hidden_sha256"));
}

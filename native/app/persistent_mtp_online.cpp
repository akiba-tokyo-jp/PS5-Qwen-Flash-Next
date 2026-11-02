// SPDX-License-Identifier: MIT
#include "persistent_mtp_online.h"
#include "persistent_mtp_cursor.h"
#include "mtp_target_hidden_capture_runtime.h"
#include "llama-ext.h"
#include <algorithm>
#include <chrono>
#include <cmath>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
namespace {
using Cursor=PersistentMtpCursor<>;using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
void need(bool value,const char*message){if(!value)throw std::runtime_error(message);}
std::string digest(const Cursor::Hidden&hidden){
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,reinterpret_cast<const unsigned char*>(hidden.data()),hidden.size()*sizeof(float));
    unsigned char bytes[32];sha256_final(&hash,bytes);std::string value;
    for(auto byte:bytes){value+="0123456789abcdef"[byte>>4];value+="0123456789abcdef"[byte&15];}return value;
}
double elapsed(Clock::time_point start){return std::chrono::duration<double,std::micro>(Clock::now()-start).count();}
}
struct PersistentMtpOnline::State {
    Engine*target;llama_model*model;llama_context*context;MtpOnlineHooks hooks;
    llama_context*aux=nullptr;llama_batch_ext*batch=nullptr;
    Cursor cursor;Cursor::Input input{};
    Json observations=Json::array(),auxiliary_inputs=Json::array();
    unsigned prompt=0,calls=0,attempts=0,accepted=0,rejected=0,proposals=0,catchups=0,maximum=0,bonus_samples=0;
    bool force_wrong=false,forced=false,sampled=false,disabled=false,unknown=false,closed=false,checks=true,single_completion=false;
    unsigned required_completions=0,extra_checkpoints=0;
    bool retain_auxiliary=false;
    unsigned request_ordinal=0,context_creations=0,lifetime_clears=0;
    double setup_us=0,proposal_us=0,catchup_us=0,retirement_us=0,completion_us=0;
    Clock::time_point deadline=Clock::now()+std::chrono::seconds(180);
    State(Engine&t,llama_model*m,llama_context*c,MtpOnlineHooks h,unsigned n,bool f,bool single,bool retain):
        target(&t),model(m),context(c),hooks(std::move(h)),maximum(n),force_wrong(f),single_completion(single),retain_auxiliary(retain){}
    void guard(){need(!unknown&&!closed&&Clock::now()<deadline,"A healthy finite online MTP owner is required");hooks.guard();}
    void begin(const char*stage){guard();hooks.stage(stage);hooks.begin();unknown=true;}
    void complete(){
        const auto start=Clock::now();
        // The selected complete callback performs the same full positive
        // device/worker/owner/journal boundary as checkpoint, then releases
        // the producer. Keep that mandatory callback in both comparison arms.
        if(!single_completion){hooks.checkpoint();++extra_checkpoints;}
        hooks.complete();++required_completions;unknown=false;completion_us+=elapsed(start);
    }
    const MtpTargetHiddenCapture<>&capture(){const auto*value=mtp_target_hidden_capture();need(value&&value->valid(),"Completed original target hidden rows required");return *value;}
    void initialize(){
        const auto start=Clock::now();begin(aux?"S1_online_before_retained_auxiliary_request_clear":"S1_online_before_one_auxiliary_creation");
        if(!aux){
        auto p=llama_context_default_params();p.ctx_type=LLAMA_CONTEXT_TYPE_MTP;p.n_ctx=256;p.n_batch=p.n_ubatch=1;
        p.n_seq_max=1;p.n_rs_seq=0;p.n_threads=p.n_threads_batch=6;p.offload_kqv=p.op_offload=true;
        p.moe_cache_size=0;p.type_k=p.type_v=GGML_TYPE_F32;p.no_perf=false;
        aux=llama_init_from_model(model,p);need(aux,"Online MTP auxiliary creation failed; retain owner");
        batch=llama_batch_ext_init(aux);need(batch,"Online MTP batch creation failed; retain owner");
        ++context_creations;
        }
        need(batch,"The retained auxiliary batch must remain owned");llama_batch_ext_clear(batch);
        llama_memory_clear(llama_get_memory(aux),true);++lifetime_clears;complete();setup_us=elapsed(start);
        hooks.stage("S1_online_one_auxiliary_creation_completed");
    }
    void retire(){
        guard();need(aux&&batch,"One positively completed auxiliary owner required for retirement");
        const auto start=Clock::now();begin("S1_online_before_auxiliary_retirement");
        llama_batch_ext_free(batch);batch=nullptr;llama_free(aux);aux=nullptr;complete();retirement_us=elapsed(start);
        hooks.stage("S1_online_auxiliary_retirement_completed");
    }
    std::int32_t auxiliary_step(const Cursor::Input&value,bool catchup){
        need(aux&&batch&&proposals+catchups<32,"One bounded persistent auxiliary context required");
        input=value;const auto start=Clock::now();begin(catchup?"S1_online_before_accepted_draft_catchup":"S1_online_before_auxiliary_proposal");
        llama_batch_ext_clear(batch);const auto index=llama_batch_ext_add_token(batch,0,input.token);const llama_pos position=input.position;
        need(index>=0&&llama_batch_ext_set_pos(batch,index,&position)&&llama_batch_ext_set_output_logits(batch,index,true)&&
             llama_batch_ext_set_embd_state(batch,index,llama_embd{input.hidden.data(),1,input.hidden.size()}),
             "Exact persistent MTP causal token/hidden/position required; retain owner");
        need(llama_process(aux,LLAMA_PROCESS_TYPE_DECODE,batch)==0,"Online MTP process failed; retain owner");
        llama_synchronize(aux);const auto*logits=llama_get_logits_ith(aux,-1);complete();
        need(logits&&llama_vocab_n_tokens(llama_model_get_vocab(model))==248320,"Full completed auxiliary vocabulary required");
        std::int32_t best=0;for(std::int32_t i=0;i<248320;++i){need(std::isfinite(logits[i]),"Completed auxiliary logits are nonfinite");if(logits[i]>logits[best])best=i;}
        auxiliary_inputs.push_back({{"catchup",catchup},{"token",input.token},{"position",input.position},{"hidden_sha256",digest(input.hidden)}});
        if(catchup){++catchups;catchup_us+=elapsed(start);}else{++proposals;proposal_us+=elapsed(start);}
        hooks.stage(catchup?"S1_online_accepted_draft_catchup_completed":"S1_online_auxiliary_proposal_completed");return best;
    }
};
PersistentMtpOnline::PersistentMtpOnline(Engine&target,llama_model*model,llama_context*context,MtpOnlineHooks hooks,unsigned maximum,bool force_wrong,bool single_completion,bool retain){
    need(model&&context&&llama_n_ctx(context)==256&&maximum>0&&maximum<=6&&hooks.begin&&hooks.complete&&hooks.checkpoint&&hooks.stage&&hooks.guard&&hooks.verify&&hooks.decision,
         "Complete finite target verifier and successful single auxiliary geometry required");
    state_=new State(target,model,context,std::move(hooks),maximum,force_wrong,single_completion,retain);
}
PersistentMtpOnline::~PersistentMtpOnline(){if(state_&&state_->closed&&!state_->unknown&&!state_->aux&&!state_->batch)delete state_;}
void PersistentMtpOnline::begin_request(Engine&target,llama_model*model,llama_context*context,MtpOnlineHooks hooks){
    auto&s=*state_;
    need(s.retain_auxiliary&&s.closed&&!s.unknown&&s.aux&&s.batch&&s.lifetime_clears==s.request_ordinal+1&&s.request_ordinal<2&&model==s.model&&context&&llama_n_ctx(context)==256&&
        hooks.begin&&hooks.complete&&hooks.checkpoint&&hooks.stage&&hooks.guard&&hooks.verify&&hooks.decision,
        "A completed request and the same live model are required before reusing its auxiliary owner");
    hooks.guard();s.target=&target;s.context=context;s.hooks=std::move(hooks);++s.request_ordinal;
    s.prompt=s.calls=s.attempts=s.accepted=s.rejected=s.proposals=s.catchups=s.bonus_samples=0;
    s.required_completions=s.extra_checkpoints=0;s.setup_us=s.proposal_us=s.catchup_us=s.retirement_us=s.completion_us=0;
    s.forced=s.sampled=s.disabled=s.closed=false;s.checks=true;s.observations=Json::array();s.auxiliary_inputs=Json::array();
    s.deadline=Clock::now()+std::chrono::seconds(180);
}
void PersistentMtpOnline::retire_auxiliary(){
    auto&s=*state_;need(s.retain_auxiliary&&s.closed&&!s.unknown&&s.aux&&s.batch,"A completed retained request is required before final auxiliary retirement");
    s.closed=false;s.retire();s.closed=true;
}
std::uint32_t PersistentMtpOnline::tokenize(const std::string&text){auto&s=*state_;s.guard();need(!s.prompt,"One online request required");s.prompt=s.target->tokenize(text);return s.prompt;}
void PersistentMtpOnline::prefill(std::uint32_t capacity){
    auto&s=*state_;s.guard();need(capacity==256&&s.prompt>0&&s.prompt<=64&&s.lifetime_clears==s.request_ordinal,
        "One exact target context-capacity prefill and one auxiliary clear per request required");
    s.target->prefill(capacity);const auto&capture=s.capture();
    need(capture.serial()>0&&capture.last_width()>0&&capture.last_width()<=s.prompt,"Actual final prefill-batch hidden row required");
    s.cursor.reset(s.prompt,capture.last());s.initialize();
}
Token PersistentMtpOnline::next(){
    auto&s=*state_;s.guard();need(s.calls<33,"Finite original output bound required");
    if(!s.sampled){const auto token=s.target->next();s.cursor.first_sample(token.id,token.end_of_generation);s.sampled=true;++s.calls;return token;}
    if(s.disabled){++s.calls;return s.target->next();}
    if(s.cursor.bonus_pending()){
        const auto serial=s.capture().serial();const auto token=s.target->next();
        s.checks&=s.capture().serial()==serial;s.cursor.queued_bonus_observed(token.id,token.end_of_generation);++s.bonus_samples;++s.calls;
        if(s.attempts>=s.maximum)s.disabled=true;
        s.observations.push_back({{"kind","bonus"},{"returned_token",token.id},{"target_process_added",false}});return token;
    }
    const auto input=s.cursor.proposal_input();const auto prediction=s.auxiliary_step(input,false);s.cursor.auxiliary_pending_completed();
    const bool pair=!llama_vocab_is_eog(llama_model_get_vocab(s.model),prediction)&&s.attempts<s.maximum;
    std::int32_t draft=prediction;
    if(pair&&s.force_wrong&&!s.forced&&s.attempts==1){draft=prediction?0:1;s.forced=true;}
    const auto before=s.hooks.decision();const auto serial=s.capture().serial();
    if(pair)s.hooks.stage("S1_online_before_original_target_verification");
    const auto token=pair?s.hooks.verify(draft):s.target->next();const auto after=s.hooks.decision();const auto&capture=s.capture();
    Json observation={{"kind",pair?"verification":"ordinary"},{"position",input.position},{"pending_token",input.token},
        {"input_hidden_sha256",digest(input.hidden)},{"prediction",prediction},{"used_draft",draft},{"returned_token",token.id},
        {"target_first_hidden_sha256",digest(capture.first())},{"target_last_hidden_sha256",digest(capture.last())},
        {"capture_serial_delta",capture.serial()-serial},{"last_process_width",capture.last_width()}};
    if(pair){
        ++s.attempts;need(after.attempts==before.attempts+1&&after.accepted+after.rejected==before.accepted+before.rejected+1,
            "Every online proposal requires one completed original target decision");
        const bool accepted=after.accepted==before.accepted+1;observation["accepted"]=accepted;
        if(accepted){
            ++s.accepted;s.checks&=token.id==draft&&capture.serial()==serial+1&&capture.last_width()==2;
            s.cursor.target_pair_accepted_await_bonus(draft,capture.first(),capture.last());
            s.auxiliary_step(s.cursor.accepted_draft_catchup_input(),true);s.cursor.accepted_draft_catchup_completed();
        }else{
            ++s.rejected;s.checks&=((capture.serial()==serial+1&&capture.last_width()==2)||(capture.serial()==serial+2&&capture.last_width()==1));
            s.cursor.target_pair_completed(draft,false,token.id,capture.first(),capture.last(),token.end_of_generation);
            if(s.attempts>=s.maximum)s.disabled=true;
        }
    }else{
        s.checks&=capture.serial()==serial+1&&capture.last_width()==1;
        s.cursor.target_single_completed(token.id,capture.last(),token.end_of_generation);
    }
    s.observations.push_back(std::move(observation));++s.calls;return token;
}
void PersistentMtpOnline::finish(){
    auto&s=*state_;s.guard();need(s.sampled&&s.aux&&s.batch&&s.lifetime_clears==s.request_ordinal+1,
        "A sampled request with one completed auxiliary clear is required before finish");s.target->finish();
    if(!s.retain_auxiliary)s.retire();else s.hooks.stage("S1_online_request_completed_auxiliary_retained");
    s.closed=true;
}
std::optional<ExpertCacheMetrics>PersistentMtpOnline::expert_cache_metrics()const{return state_->target->expert_cache_metrics();}
Json PersistentMtpOnline::report()const{
    const auto&s=*state_;need(s.closed&&!s.unknown,"Positive target and auxiliary retirement required");
    return {{"completed",true},{"causal_and_capture_checks_passed",s.checks},{"target_attempts",s.attempts},{"target_accepted",s.accepted},
        {"target_rejected",s.rejected},{"actual_queued_bonus_samples",s.bonus_samples},{"auxiliary_proposals",s.proposals},
        {"accepted_draft_catchups",s.catchups},{"auxiliary_KV_clear_count",1},{"maximum_simultaneous_auxiliary_contexts",1},
        {"auxiliary_contexts_positively_retired",!s.aux&&!s.batch},{"only_original_target_verified_tokens_emitted",true},
        {"auxiliary_retained_between_requests",s.retain_auxiliary},{"request_ordinal",s.request_ordinal},
        {"lifetime_auxiliary_context_creations",s.context_creations},{"lifetime_auxiliary_KV_clears",s.lifetime_clears},
        {"forced_wrong_draft_used",s.forced},{"context_setup_us",s.setup_us},{"complete_proposal_us",s.proposal_us},
        {"complete_catchup_us",s.catchup_us},{"auxiliary_retirement_us",s.retirement_us},{"observations",s.observations},
        {"single_native_completion",s.single_completion},{"required_native_completions",s.required_completions},
        {"extra_native_checkpoints",s.extra_checkpoints},{"complete_native_boundary_us",s.completion_us},
        {"auxiliary_causal_inputs",s.auxiliary_inputs},{"diagnostic_hashing_and_stages_enabled",true},
        {"broader_MTP_quality_qualified",false},{"whole_model_speed_qualified",false}};
}
}

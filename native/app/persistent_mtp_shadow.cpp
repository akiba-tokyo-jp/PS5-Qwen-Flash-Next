// SPDX-License-Identifier: MIT
#include "persistent_mtp_shadow.h"
#include "persistent_mtp_cursor.h"
#include "llama-ext.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <vector>

namespace qwen_app {
namespace {
using Clock=std::chrono::steady_clock;using Json=nlohmann::json;using Cursor=PersistentMtpCursor<>;
void need(bool condition,const char*message){if(!condition)throw std::runtime_error(message);}
double elapsed(Clock::time_point start){return std::chrono::duration<double,std::micro>(Clock::now()-start).count();}
}
struct PersistentMtpShadow::State {
    Engine&target;llama_model*model;llama_context*context;MtpShadowBoundaries boundary;
    std::array<llama_context*,2>aux{};std::array<llama_batch_ext*,2>batch{};
    Cursor cursor;Cursor::Input input{};
    Cursor::Hidden downloaded{},prompt_hidden{},live{};
    struct Frame {Cursor::Input input;std::int32_t target;bool end;Cursor::Hidden next_hidden;};
    std::vector<Frame>frames;
    Json observations=Json::array();
    std::uint32_t prompt=0,outputs=0,proposals=0;
    std::array<std::uint64_t,2>clears{},correct{};
    std::array<std::int32_t,2>predicted{};
    std::array<double,2>setup_us{},clear_us{},compute_fence_us{},proposal_complete_us{};
    double hidden_copy_us=0,retirement_us=0,replay_us=0;
    std::int32_t pending=-1,position=0;
    bool sampled=false,pending_valid=false,reverse=false,prefilled=false,unknown=false,closed=false;
    const Clock::time_point deadline=Clock::now()+std::chrono::seconds(180);
    State(Engine&t,llama_model*m,llama_context*c,MtpShadowBoundaries b,bool r):target(t),model(m),context(c),boundary(std::move(b)),reverse(r){frames.reserve(24);}
    void guard(){need(!unknown&&!closed&&Clock::now()<deadline,"Bounded healthy MTP shadow owner required");boundary.guard();
        need(boundary.target_is_ordinary(),"This shadow admits only the unchanged ordinary target path");}
    void begin(const char*stage){guard();boundary.stage(stage);boundary.begin();unknown=true;}
    void complete(){boundary.checkpoint();boundary.complete();unknown=false;}
    const Cursor::Hidden&hidden(){
        const auto start=Clock::now();begin("S1_shadow_before_target_hidden_download");
        const auto*h=llama_get_embeddings_nextn_ith(context,-1);
        llama_synchronize(context);
        // Copy before completing the epoch; any opaque download still owns the
        // deferred State array used as its destination.
        if(h)std::copy_n(h,downloaded.size(),downloaded.begin());
        complete();boundary.stage("S1_shadow_target_hidden_download_completed");
        hidden_copy_us+=elapsed(start);need(h,"Complete target NextN hidden row required");
        need(std::all_of(downloaded.begin(),downloaded.end(),[](float x){return std::isfinite(x);}),"Target NextN hidden row is non-finite");
        return downloaded;
    }
    void initialize(unsigned arm){
            need(!aux[0]&&!aux[1],"Only one auxiliary context may be live in this replay scope");
            const auto start=Clock::now();begin("S1_shadow_before_auxiliary_context_creation");
            auto p=llama_context_default_params();p.ctx_type=LLAMA_CONTEXT_TYPE_MTP;p.n_ctx=256;p.n_batch=p.n_ubatch=1;
            p.n_seq_max=p.n_rs_seq=1;p.n_threads=p.n_threads_batch=6;p.offload_kqv=p.op_offload=true;
            p.moe_cache_size=0;p.type_k=p.type_v=GGML_TYPE_F32;p.no_perf=false;
            aux[arm]=llama_init_from_model(model,p);need(aux[arm],"Shared-model MTP context unavailable; retain owner");
            batch[arm]=llama_batch_ext_init(aux[arm]);need(batch[arm],"MTP batch unavailable; retain owner");
            llama_memory_clear(llama_get_memory(aux[arm]),true);++clears[arm];
            complete();setup_us[arm]=elapsed(start);boundary.stage("S1_shadow_auxiliary_context_creation_completed");
    }
    void proposal(unsigned arm){
        const auto start=Clock::now();begin("S1_shadow_before_auxiliary_proposal");
        const auto clear_start=Clock::now();
        if(arm==0){llama_memory_clear(llama_get_memory(aux[arm]),true);++clears[arm];}
        clear_us[arm]=elapsed(clear_start);
        llama_batch_ext_clear(batch[arm]);const auto index=llama_batch_ext_add_token(batch[arm],0,input.token);
        const llama_pos position=input.position;
        need(index>=0&&llama_batch_ext_set_pos(batch[arm],index,&position)&&llama_batch_ext_set_output_logits(batch[arm],index,true)&&
             llama_batch_ext_set_embd_state(batch[arm],index,llama_embd{input.hidden.data(),1,input.hidden.size()}),
             "Exact actual pending token/hidden/position MTP batch required; retain owner");
        const auto process_start=Clock::now();
        need(llama_process(aux[arm],LLAMA_PROCESS_TYPE_DECODE,batch[arm])==0,"MTP shadow process failed; retain owner");
        llama_synchronize(aux[arm]);compute_fence_us[arm]=elapsed(process_start);
        const auto*logits=llama_get_logits_ith(aux[arm],-1);complete();
        boundary.stage("S1_shadow_auxiliary_proposal_positively_completed");
        const auto n=llama_vocab_n_tokens(llama_model_get_vocab(model));need(logits&&n==248320,"Complete MTP logits required");
        std::int32_t best=0;
        for(std::int32_t i=0;i<n;++i){need(std::isfinite(logits[i]),"Non-finite completed MTP logits");if(logits[i]>logits[best])best=i;}
        predicted[arm]=best;proposal_complete_us[arm]=elapsed(start);
    }
};
PersistentMtpShadow::PersistentMtpShadow(Engine&target,llama_model*model,llama_context*context,MtpShadowBoundaries b,bool reverse){
    need(model&&context&&llama_n_ctx(context)==256&&b.begin&&b.complete&&b.checkpoint&&b.stage&&b.guard&&b.target_is_ordinary,
         "Exact ordinary target, context and completion boundaries required");
    state_=new State(target,model,context,std::move(b),reverse);
    llama_set_embeddings_nextn(context,true,true);
}
PersistentMtpShadow::~PersistentMtpShadow(){if(state_&&state_->closed&&!state_->unknown)delete state_;}
std::uint32_t PersistentMtpShadow::tokenize(const std::string&text){
    auto&s=*state_;s.guard();need(!s.prompt,"One target request per shadow required");s.prompt=s.target.tokenize(text);
    need(s.prompt>0&&s.prompt<=64,"Bounded actual target prompt required");return s.prompt;
}
void PersistentMtpShadow::prefill(std::uint32_t n){
    auto&s=*state_;s.guard();need(n==s.prompt&&!s.prefilled,"One exact target prefill required");
    s.target.prefill(n);s.prompt_hidden=s.live=s.hidden();s.position=n;s.prefilled=true;
}
Token PersistentMtpShadow::next(){
    auto&s=*state_;s.guard();need(s.prefilled&&s.outputs<32&&s.proposals<24,"Finite ordinary MTP shadow bound required");
    const bool proposed=s.pending_valid;
    if(proposed)s.input={s.pending,s.position,s.live};
    const auto token=s.target.next();s.guard();
    if(proposed){
        ++s.proposals;s.live=s.hidden();s.frames.push_back({s.input,token.id,token.end_of_generation,s.live});++s.position;
    }else need(!s.sampled,"No token may follow a completed target end");
    s.sampled=true;s.pending=token.id;s.pending_valid=!token.end_of_generation;
    if(!token.end_of_generation)++s.outputs;
    return token;
}
void PersistentMtpShadow::finish(){
    auto&s=*state_;s.guard();s.target.finish();const auto start=Clock::now();
    // Replay the actual completed target inputs in two sequential contexts.
    // This preserves each arm's causal KV history while bounding live context
    // ownership to one; it is a component diagnostic, not an online speed test.
    need(!s.frames.empty(),"Completed real target proposals required");
    for(unsigned order=0;order<2;++order){
        const unsigned arm=s.reverse?1-order:order;s.initialize(arm);
        s.cursor.reset(s.prompt,s.prompt_hidden);s.cursor.first_sample(s.frames.front().input.token);
        for(const auto&frame:s.frames){
            s.input=s.cursor.proposal_input();
            need(s.input.token==frame.input.token&&s.input.position==frame.input.position&&s.input.hidden==frame.input.hidden,
                 "MTP replay must use the exact completed causal target input");
            s.proposal(arm);s.cursor.auxiliary_pending_completed();
            s.cursor.target_single_completed(frame.target,frame.next_hidden,frame.end);
            if(s.predicted[arm]==frame.target)++s.correct[arm];
            s.observations.push_back({{"arm",arm},{"position",s.input.position},{"pending_token",s.input.token},
                {"target_token",frame.target},{"target_end",frame.end},{"prediction",s.predicted[arm]},
                {"clear_us",s.clear_us[arm]},{"compute_fence_us",s.compute_fence_us[arm]},
                {"complete_proposal_us",s.proposal_complete_us[arm]}});
        }
        const auto retirement_started=Clock::now();s.begin("S1_shadow_before_auxiliary_retirement");
        llama_batch_ext_free(s.batch[arm]);s.batch[arm]=nullptr;llama_free(s.aux[arm]);s.aux[arm]=nullptr;
        s.complete();s.boundary.stage("S1_shadow_auxiliary_retirement_completed");s.retirement_us+=elapsed(retirement_started);
    }
    s.replay_us=elapsed(start);s.closed=true;
}
std::optional<ExpertCacheMetrics>PersistentMtpShadow::expert_cache_metrics()const{return state_->target.expert_cache_metrics();}
Json PersistentMtpShadow::report()const{
    const auto&s=*state_;need(s.closed&&!s.unknown,"Positive completed shadow retirement required");
    return {{"schema","ps5-qwen-persistent-MTP-shadow-v1"},{"completed",true},{"proposals",s.proposals},{"outputs",s.outputs},
        {"auxiliary_contexts_created",2},{"auxiliary_contexts_positively_retired",true},{"KV_clear_counts",s.clears},
        {"maximum_simultaneous_auxiliary_contexts",1},{"actual_causal_inputs_replayed_after_target_completion",true},
        {"first_auxiliary_arm",s.reverse?1:0},{"online_scheduling_qualified",false},
        {"target_prediction_matches",s.correct},{"context_setup_us",s.setup_us},{"target_hidden_copy_us",s.hidden_copy_us},
        {"auxiliary_retirement_us",s.retirement_us},{"observations",s.observations},{"target_tokens_selected_by_auxiliary",0},
        {"complete_auxiliary_replay_us",s.replay_us},
        {"ordinary_target_only",true},{"speculative_acceptance_or_rollback_exercised",false},{"whole_model_speed_qualified",false}};
}
}

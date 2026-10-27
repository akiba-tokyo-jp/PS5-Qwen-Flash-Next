// SPDX-License-Identifier: MIT
// API transaction stubs with opaque state tags; no learned arithmetic or GPU.
#include "llama_engine.h"
#include "expert_policy.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
struct llama_vocab {};
struct llama_model {llama_vocab vocab;};
struct llama_memory_i {
    int position=0,KV_tag=0,recurrent_tag=0,PLE_tag=0;
};
struct llama_context {
    llama_model *model;llama_memory_i memory,saved;std::array<float,64> logits{};
    std::array<std::array<float,64>,4> batch_logits{};unsigned row_count=0;
};
struct llama_batch_ext {std::vector<llama_token> tokens;std::vector<llama_pos> positions;};
namespace {
std::string scenario;unsigned begins=0,completed=0,retained=0,checkpoints=0,processes=0,captures=0,restores=0,freed=0;
bool active=false;std::vector<std::array<int,3>> routes;
void check(bool value){if(!value)throw std::runtime_error("Checkpoint adapter transaction failed");}
void begin(){check(!active);active=true;++begins;}
void complete(){check(active);active=false;++completed;}
void retain(){check(active);active=false;++retained;}
void checkpoint(){check(active);++checkpoints;}
}
#include "actual_checkpoint_greedy.inc"
extern "C" {
void llama_app_expert_counters(llama_app_expert_stats *s){*s={};}
llama_model_params llama_model_default_params(){return {};}
llama_context_params llama_context_default_params(){return {};}
const llama_model *llama_get_model(const llama_context *c){return c->model;}
const llama_vocab *llama_model_get_vocab(const llama_model *m){return &m->vocab;}
llama_batch_ext *llama_batch_ext_init(llama_context *){return new llama_batch_ext;}
void llama_batch_ext_free(llama_batch_ext *b){++freed;delete b;}
llama_sampler *llama_sampler_init_greedy(){return new llama_sampler;}
void llama_sampler_free(llama_sampler *s){++freed;delete s;}
void llama_sampler_reset(llama_sampler *){}
void llama_sampler_apply(llama_sampler *s,llama_token_data_array *data){llama_sampler_greedy_apply(s,data);}
void llama_sampler_accept(llama_sampler *,llama_token){}
int32_t llama_tokenize(const llama_vocab *,const char *text,int32_t length,llama_token *out,int32_t size,bool,bool){
    if(!out||size<30)return -30;for(int i=0;i<30;++i)out[i]=i+1;
    if(length>0&&text[0]=='!')out[29]=31;return 30;
}
void llama_batch_ext_clear(llama_batch_ext *b){b->tokens.clear();b->positions.clear();}
int32_t llama_batch_ext_add_token(llama_batch_ext *b,llama_seq_id seq,llama_token token){check(seq==0);b->tokens.push_back(token);b->positions.push_back(-1);return int(b->tokens.size()-1);}
bool llama_batch_ext_set_pos(llama_batch_ext *b,int32_t index,const llama_pos *position){b->positions.at(index)=*position;return true;}
bool llama_batch_ext_set_output_logits(llama_batch_ext *,int32_t,bool output){check(output);return true;}
int32_t llama_process(llama_context *c,llama_process_type,llama_batch_ext *b){
    check(active);++processes;
    if(scenario=="spec-process-failure"&&b->tokens.size()==2&&b->positions.front()>=30)return -1;
    if(c->memory.KV_tag!=c->memory.position||c->memory.recurrent_tag!=c->memory.position||c->memory.PLE_tag!=c->memory.position)return -1;
    check(!b->positions.empty()&&b->positions[0]==c->memory.position);
    c->memory.position=b->positions.back()+1;c->memory.KV_tag=c->memory.recurrent_tag=c->memory.PLE_tag=c->memory.position;
    c->row_count=unsigned(b->tokens.size());check(c->row_count<=4);
    for(unsigned i=0;i<c->row_count;++i) {
        const int position=b->positions[i]+1;int selected=position<30?0:std::min(33,position+1);
        if(scenario.rfind("auto-",0)==0&&scenario!="auto-no-draft"&&position>=30) {
            const std::array<int,9> accepted{{7,8,7,8,7,8,9,10,33}},rejected{{7,8,7,8,7,9,10,11,33}};
            if(scenario=="auto-limit")selected=(position-30)%2?8:7;
            else {const auto &sequence=scenario=="auto-rejected"?rejected:accepted;
                selected=sequence.at(std::min<std::size_t>(8,position-30));}
        }
        c->batch_logits[i].fill(-1.125f);c->batch_logits[i][selected]=10.25f;
    }
    c->logits=c->batch_logits[c->row_count-1];
    for(int layer=0;layer<48;++layer)routes.push_back({b->positions[0],int(b->tokens.size()),layer});return 0;
}
void llama_synchronize(llama_context *c){check(active);if(scenario=="spec-unknown-sync"&&c->row_count==2&&c->memory.position>=32)throw std::runtime_error("Synchronization completion unknown");}
uint32_t llama_n_ctx(const llama_context *){return 256;}
uint32_t llama_n_batch(const llama_context *){return 4;}
uint32_t llama_n_ubatch(const llama_context *){return 4;}
llama_memory_t llama_get_memory(const llama_context *c){return const_cast<llama_memory_i *>(&c->memory);}
void llama_memory_clear(llama_memory_t memory,bool){*memory={};}
llama_pos llama_memory_seq_pos_min(llama_memory_t,llama_seq_id seq){check(seq==0);return 0;}
llama_pos llama_memory_seq_pos_max(llama_memory_t m,llama_seq_id seq){check(seq==0);return m->position-1;}
int32_t llama_vocab_n_tokens(const llama_vocab *){return 64;}
float *llama_get_logits_ith(llama_context *c,int32_t row){
    if(row<0)return c->logits.data();if(scenario=="spec-missing-row"&&row==1)return nullptr;
    return unsigned(row)<c->row_count?c->batch_logits[row].data():nullptr;
}
llama_token llama_get_sampled_token_ith(llama_context *,int32_t){return LLAMA_TOKEN_NULL;}
float *llama_get_sampled_probs_ith(llama_context *,int32_t){return nullptr;}
float *llama_get_sampled_logits_ith(llama_context *,int32_t){return nullptr;}
llama_token llama_sampler_sample(llama_sampler *s,llama_context *c,int32_t){
    std::array<llama_token_data,64> items{};for(llama_token i=0;i<64;++i)items[i]={i,c->logits[i],0};
    llama_token_data_array array{items.data(),items.size(),-1,false};llama_sampler_apply(s,&array);return array.data[array.selected].id;
}
bool llama_vocab_is_eog(const llama_vocab *,llama_token token){return token==33;}
int32_t llama_token_to_piece(const llama_vocab *,llama_token token,char *out,int32_t size,int32_t,bool){check(size>0);out[0]=char('a'+token%26);return 1;}
size_t llama_state_seq_get_size_ext(llama_context *,llama_seq_id seq,llama_state_seq_flags flags){check(seq==0);return flags==LLAMA_STATE_SEQ_FLAGS_ON_DEVICE?16:32;}
size_t llama_state_seq_get_data_ext(llama_context *c,uint8_t *out,size_t size,llama_seq_id seq,llama_state_seq_flags flags){
    check(active&&size==16&&seq==0&&flags==LLAMA_STATE_SEQ_FLAGS_ON_DEVICE);++captures;c->saved=c->memory;std::memcpy(out,&c->memory,16);return scenario=="short_capture"?15:16;
}
size_t llama_state_seq_set_data_ext(llama_context *c,const uint8_t *,size_t size,llama_seq_id seq,llama_state_seq_flags flags){
    check(active&&size==16&&seq==0&&flags==LLAMA_STATE_SEQ_FLAGS_ON_DEVICE);++restores;c->memory=c->saved;
    if(scenario=="missing_PLE"||scenario=="prefix-missing-PLE"||scenario=="spec-missing-PLE")++c->memory.PLE_tag;
    return scenario=="short_restore"||scenario=="prefix-short-restore"||scenario=="spec-short-restore"?15:16;
}
}
int speculative_case() {
    const bool positive=scenario=="spec-accepted"||scenario=="spec-rejected"||scenario=="spec-discard"||scenario=="spec-target-EOG"||scenario=="spec-invalid";
    llama_model model,other;llama_context context{&model,{},{},{}};unsigned observed=0;std::vector<int> emitted;
    {
    qwen_app::LlamaEngine engine(&model,&context,4);engine.set_gpu_boundaries(begin,complete,retain,checkpoint);
    engine.set_logits_observer([&](const float *logits,std::size_t count){
        check(count==64&&observed<3);const auto id=31+observed;
        for(unsigned i=0;i<64;++i)check(logits[i]==(i==id?10.25f:-1.125f));++observed;
    });
    try {
        engine.enable_speculative_step_prototype([](std::uint64_t bytes){check(bytes==16);if(scenario=="spec-no-budget")throw std::runtime_error("Snapshot refused");});
        engine.tokenize("same bounded opaque prompt");engine.prefill(256);
        const auto first=engine.next();check(first.id==31&&!first.end_of_generation);emitted.push_back(first.id);
        if(scenario=="spec-wrong-model")context.model=&other;
        if(scenario=="spec-invalid") {
            const auto before=processes;bool refused=false;try{engine.next_with_one_draft(-1);}catch(const std::invalid_argument&){refused=true;}
            check(refused&&!engine.failed()&&processes==before);
        }
        if(scenario=="spec-target-EOG") {const auto second=engine.next();check(second.id==32);emitted.push_back(second.id);}
        const bool reject=scenario=="spec-rejected"||scenario=="spec-short-restore"||scenario=="spec-missing-PLE"||scenario=="spec-target-EOG";
        const auto next=engine.next_with_one_draft(reject?0:32);
        if(scenario=="spec-target-EOG")check(next.id==33&&next.end_of_generation);
        else {check(next.id==32&&!next.end_of_generation);emitted.push_back(next.id);}
        if(scenario=="spec-accepted"||scenario=="spec-invalid") {
            const auto before=processes;bool refused=false;try{engine.next_with_one_draft(0);}catch(const std::invalid_argument&){refused=true;}
            check(refused&&before==processes&&!engine.failed());
            refused=false;try{engine.prefill(256);}catch(const std::invalid_argument&){refused=true;}
            check(refused&&before==processes&&!engine.failed());
        }
        if(scenario!="spec-discard"&&scenario!="spec-target-EOG") {
            const auto end=engine.next();check(end.id==33&&end.end_of_generation);
        }
        check(positive);const auto stats=engine.speculative_step_stats();
        check(emitted==std::vector<int>({31,32})&&stats.enabled&&stats.attempts==1&&stats.accepted==unsigned(!reject)&&stats.rejected==unsigned(reject));
        check(captures==1&&restores==unsigned(reject)&&processes==(reject?11u:9u));
        check(stats.queued_bonus_samples==unsigned(!reject&&scenario!="spec-discard"));
        check(observed==(scenario=="spec-discard"?2u:3u));
        engine.finish();check(context.memory.position==0&&begins==completed&&!retained&&!active);
    }catch(...) {
        if(positive)throw;
        check(engine.failed()&&retained>0&&!active);const auto before=processes;
        bool blocked=false;try{engine.next();}catch(...){blocked=true;}check(blocked&&before==processes);
        check(emitted==std::vector<int>({31}));
    }
    }
    check(freed==(positive?2u:0u));
    std::cout<<"{\"scenario\":\""<<scenario<<"\",\"passed\":true,\"process_calls\":"<<processes
        <<",\"captures\":"<<captures<<",\"restores\":"<<restores<<",\"full_logit_observations\":"<<observed
        <<",\"PS5_operations\":0,\"learned_model_inference\":false}"<<std::endl;return 0;
}
int prefix_case() {
    const bool positive=scenario=="prefix-positive"||scenario=="prefix-miss";
    llama_model model,other;llama_context context{&model,{},{},{}};unsigned checked=0;
    std::vector<std::array<float,64>> observed;
    {
    qwen_app::LlamaEngine engine(&model,&context,4);engine.set_gpu_boundaries(begin,complete,retain,checkpoint);
    engine.set_logits_observer([&](const float *data,std::size_t count){
        check(count==64);if(scenario=="prefix-observer-failure")throw std::runtime_error("Observer failed");
        std::array<float,64> copy{};std::copy_n(data,64,copy.data());observed.push_back(copy);
    });
    try {
        engine.enable_prefix_reuse([](std::uint64_t n){check(n==16);if(scenario=="prefix-no-budget")throw std::runtime_error("Not admitted");});
        for(unsigned request=0;request<2;++request) {
            engine.tokenize(request&&scenario=="prefix-miss"?"!different prefix":"same prefix");engine.prefill(256);
            std::vector<int> emitted;
            for(unsigned i=0;i<4;++i){const auto token=engine.next();if(token.end_of_generation)break;emitted.push_back(token.id);}
            check(emitted==std::vector<int>({31,32}));engine.finish();
            check(!engine.prefix_reuse_stats().request_hit||request==1);
            if(!request&&scenario=="prefix-wrong-model")context.model=&other;
        }
        check(positive);const auto stats=engine.prefix_reuse_stats();const bool miss=scenario=="prefix-miss";
        check(stats.enabled&&stats.captures==(miss?2u:1u)&&stats.restores==(miss?0u:1u)&&stats.last_reused_prompt_tokens==(miss?0u:30u));
        check(captures==stats.captures&&restores==stats.restores&&processes==(miss?20u:12u));
        check(observed.size()==6&&observed[0]==observed[3]&&observed[1]==observed[4]&&observed[2]==observed[5]);
        check(!engine.checkpoint_validation_stats().enabled&&begins==completed&&!retained&&!active);checked=2;
    }catch(...) {
        if(positive)throw;check(engine.failed());const auto before=processes;
        try{engine.next();}catch(...){checked=1;}check(checked&&processes==before);
    }
    }
    check(freed==(positive?2u:0u));
    std::cout<<"{\"scenario\":\""<<scenario<<"\",\"passed\":true,\"bounded_prefix_controls\":"<<checked
        <<",\"process_calls\":"<<processes<<",\"captures\":"<<captures<<",\"restores\":"<<restores
        <<",\"full_logit_observations\":"<<observed.size()<<",\"PS5_operations\":0,\"learned_model_inference\":false}"<<std::endl;return 0;
}
int automatic_case() {
    llama_model model;llama_context context{&model,{},{},{}};
    const unsigned requests=scenario=="auto-repeat"?2:scenario=="auto-limit"?3:1;
    unsigned online_before=0,online_ordinary=0,online_choices=0,online_verified=0;
    {
        qwen_app::LlamaEngine engine(&model,&context,4);engine.set_gpu_boundaries(begin,complete,retain,checkpoint);
        if(scenario.rfind("auto-expert-",0)==0) {
            qwen_app::ExpertVerificationHooks hooks;
            hooks.before_process=[&]{++online_before;};
            hooks.completed_ordinary=[&](int token,std::uint64_t elapsed){check(token>=0&&elapsed>0);++online_ordinary;};
            hooks.choose=[&](int pending,int draft){check(pending>=0&&draft>=0);++online_choices;
                return scenario=="auto-expert-ordinary"?1u:2u;};
            hooks.verified=[&](bool accepted,double capture,double restore){check(accepted&&capture>=0&&restore==0);++online_verified;};
            engine.enable_expert_aware_speculation([](std::uint64_t bytes){check(bytes==16);},std::move(hooks));
        }else engine.enable_model_free_speculation([](std::uint64_t bytes){check(bytes==16);});
        for(unsigned request=0;request<requests;++request) {
            engine.tokenize("past tokens only");engine.prefill(256);std::vector<int> emitted;
            for(unsigned i=0;i<32;++i){const auto token=engine.next();if(token.end_of_generation)break;emitted.push_back(token.id);}
            const std::vector<int> expected=scenario=="auto-no-draft"?std::vector<int>{31,32}:
                scenario=="auto-rejected"?std::vector<int>{7,8,7,8,7,9,10,11}:std::vector<int>{7,8,7,8,7,8,9,10};
            if(scenario=="auto-limit") {
                check(emitted.size()==32);for(unsigned i=0;i<32;++i)check(emitted[i]==(i%2?8:7));
                const auto before=processes;bool stopped=false;try{engine.next();}catch(const std::invalid_argument&){stopped=true;}
                check(stopped&&before==processes&&!engine.failed());
            }else check(emitted==expected);
            engine.finish();check(context.memory.position==0);
        }
        const auto stats=engine.speculative_step_stats();check(stats.enabled&&stats.controller_enabled&&stats.attempts<=32);
        if(scenario=="auto-expert-ordinary")check(stats.attempts==0&&captures==0&&processes==16&&
            stats.expert_cost_enabled&&online_choices>0&&online_verified==0&&online_ordinary==8&&online_before==processes&&stats.cost_ordinary==online_choices);
        else if(scenario=="auto-expert-accepted")check(stats.attempts==1&&stats.accepted==1&&captures==1&&restores==0&&
            stats.expert_cost_enabled&&online_choices==1&&online_verified==1&&online_ordinary==6&&online_before==processes&&stats.cost_width_two==1);
        else if(scenario=="auto-limit")check(stats.attempts==32&&stats.accepted==32&&captures==32&&restores==0);
        else if(scenario=="auto-no-draft")check(stats.attempts==0&&captures==0&&processes==10);
        else if(scenario=="auto-rejected")check(stats.attempts==1&&stats.rejected==1&&restores==1&&processes==17);
        else check(stats.attempts==requests&&stats.accepted==requests&&restores==0&&processes==15*requests);
        check(begins==completed&&!retained&&!active);
    }
    check(freed==2);std::cout<<"{\"scenario\":\""<<scenario<<"\",\"passed\":true,\"PS5_operations\":0}"<<std::endl;return 0;
}
int main(int argc,char **argv) {
    check(argc==2);scenario=argv[1];if(scenario.rfind("prefix-",0)==0)return prefix_case();
    if(scenario.rfind("spec-",0)==0)return speculative_case();
    if(scenario.rfind("auto-",0)==0)return automatic_case();
    llama_model model;llama_context context{&model,{},{},{}};
    unsigned checked=0;std::vector<int> emitted;
    {
    qwen_app::LlamaEngine engine(&model,&context,4);engine.set_gpu_boundaries(begin,complete,retain,checkpoint);
    try {
        engine.enable_checkpoint_validation([](std::uint64_t bytes){check(bytes==16);if(scenario=="no_budget")throw std::runtime_error("Allocation not admitted");},
            []{return std::uint32_t(routes.size());},[](std::uint32_t a,std::uint32_t b,std::uint32_t count){
                check(a+count<=routes.size()&&b+count<=routes.size());
                if(scenario=="wrong_routes")throw std::runtime_error("Original routes differ");
                for(unsigned i=0;i<count;++i)check(routes[a+i]==routes[b+i]);
            });
        engine.tokenize("metadata-only prompt");engine.prefill(256);
        for(unsigned n=0;n<4;++n){const auto token=engine.next();if(token.end_of_generation)break;emitted.push_back(token.id);}
        engine.finish();const auto s=engine.checkpoint_validation_stats();
        check(scenario=="positive"&&emitted==std::vector<int>({31,32})&&s.completed&&s.captures==5&&s.restores==5&&s.prefill_replays==2&&s.next_replays==3&&s.route_rows_compared==192);
        check(s.maximum_absolute_logit_error==0&&s.capture_positions[0]==4&&s.capture_positions[1]==28&&
            s.capture_positions[2]==30&&s.capture_positions[3]==30&&s.capture_positions[4]==31);
        check(processes==14&&routes.size()==672&&begins==completed&&!retained&&!active&&checkpoints==24);checked=5;
    }catch(...) {
        if(scenario=="positive")throw;
        check(engine.failed());const auto before=processes;try{engine.next();}catch(...){checked=1;}check(checked&&before==processes);
    }
    }
    check(freed==(scenario=="positive"?2u:0u));
    std::cout<<"{\"scenario\":\""<<scenario<<"\",\"passed\":true,\"prefill_and_next_replays_checked\":"<<checked
        <<",\"actual_greedy_source_used\":true,\"duplicate_emission\":false,\"process_calls\":"<<processes
        <<",\"capture_API_calls\":"<<captures<<",\"restore_API_calls\":"<<restores<<",\"positive_checkpoint_calls\":"<<checkpoints
        <<",\"adapter_objects_released\":"<<freed<<",\"PS5_operations\":0,\"learned_model_inference\":false}"<<std::endl;
}

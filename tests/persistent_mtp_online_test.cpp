// SPDX-License-Identifier: MIT
#include "persistent_mtp_online.h"
#include "mtp_target_hidden_capture_runtime.h"
#include "first_generation.h"
#include "llama-ext.h"
#include <algorithm>
#include <cassert>
#include <memory>
#include <vector>
struct llama_model {};
struct llama_vocab {};
struct llama_memory_i {llama_context*context=nullptr;};
struct llama_context {
    bool auxiliary=false;llama_memory_i memory{this};
    qwen_app::MtpTargetHiddenCapture<>::Hidden first{},last{};
    std::vector<float>logits;std::vector<int>tokens,positions;unsigned clears=0;
};
struct llama_batch_ext {llama_context*context=nullptr;int token=-1,position=-1;llama_embd hidden{};};
namespace {
using Capture=qwen_app::MtpTargetHiddenCapture<>;
Capture*capture=nullptr;llama_vocab vocabulary;
unsigned live=0,created=0,freed=0,begins=0,completions=0,checkpoints=0,prompt_tokens=30;bool active=false,wrong_first=false;
unsigned fail_at_completion=0;const float*submitted_hidden=nullptr;
std::vector<int>completed_auxiliary_tokens;
void begin(){assert(!active);active=true;++begins;}
void complete(){assert(active);if(fail_at_completion&&completions+1==fail_at_completion)throw std::runtime_error("Mock unknown positive boundary");active=false;++completions;}
void checkpoint(){assert(active);++checkpoints;}
float*hidden(void*pointer,int index){assert(active);capture->original_synchronize_returned(pointer);
    auto&context=*static_cast<llama_context*>(pointer);return index==0?context.first.data():context.last.data();}
void synchronize(void*pointer){assert(active);capture->original_synchronize_returned(pointer);}
}
namespace qwen_app {const MtpTargetHiddenCapture<>*mtp_target_hidden_capture()noexcept{return capture;}}
extern "C" {
llama_context_params llama_context_default_params(){return {};}
llama_context*llama_init_from_model(llama_model*,llama_context_params p){
    assert(active&&p.ctx_type==LLAMA_CONTEXT_TYPE_MTP&&p.n_ctx==256&&p.n_batch==1&&p.n_ubatch==1&&p.n_seq_max==1&&p.n_rs_seq==0);
    auto*c=new llama_context;c->auxiliary=true;c->logits.resize(248320);++live;++created;assert(live==1);return c;
}
void llama_free(llama_context*c){assert(active&&c->auxiliary&&c->clears>=1&&c->clears<=3);completed_auxiliary_tokens=c->tokens;--live;++freed;delete c;}
std::uint32_t llama_n_ctx(const llama_context*){return 256;}
llama_memory_t llama_get_memory(const llama_context*c){return const_cast<llama_memory_i*>(&c->memory);}
void llama_memory_clear(llama_memory_t memory,bool data){
    assert(active&&data&&memory->context->auxiliary);++memory->context->clears;
    memory->context->tokens.clear();memory->context->positions.clear();
}
void llama_synchronize(llama_context*){assert(active);}
const llama_vocab*llama_model_get_vocab(const llama_model*){return &vocabulary;}
int32_t llama_vocab_n_tokens(const llama_vocab*){return 248320;}
bool llama_vocab_is_eog(const llama_vocab*,llama_token token){return token==104;}
llama_batch_ext*llama_batch_ext_init(llama_context*c){assert(active);auto*b=new llama_batch_ext;b->context=c;return b;}
void llama_batch_ext_free(llama_batch_ext*b){assert(active);delete b;}
void llama_batch_ext_clear(llama_batch_ext*b){assert(active);const auto context=b->context;*b={};b->context=context;}
int32_t llama_batch_ext_add_token(llama_batch_ext*b,llama_seq_id seq,llama_token token){assert(active&&seq==0);b->token=token;return 0;}
bool llama_batch_ext_set_pos(llama_batch_ext*b,int32_t index,const llama_pos*position){assert(active&&index==0);b->position=*position;return true;}
bool llama_batch_ext_set_output_logits(llama_batch_ext*,int32_t index,bool value){assert(active&&index==0&&value);return true;}
bool llama_batch_ext_set_embd_state(llama_batch_ext*b,int32_t index,llama_embd value){assert(active&&index==0&&value.n_rows==1&&value.n_embd==10240);b->hidden=value;return true;}
int32_t llama_process(llama_context*c,llama_process_type type,llama_batch_ext*b){
    assert(active&&type==LLAMA_PROCESS_TYPE_DECODE&&c==b->context&&c->auxiliary&&b->position==b->token-100+int(prompt_tokens));
    assert(std::all_of(b->hidden.data,b->hidden.data+10240,[&](float x){return x==float(b->token-90);}));
    if(!c->positions.empty())assert(b->position==c->positions.back()+1);
    submitted_hidden=b->hidden.data;c->positions.push_back(b->position);c->tokens.push_back(b->token);std::fill(c->logits.begin(),c->logits.end(),-1);
    c->logits[wrong_first&&b->token==100?199:b->token+1]=1;return 0;
}
float*llama_get_logits_ith(llama_context*c,int32_t index){assert(active&&index==-1);return c->logits.data();}
}
class Target final:public qwen_app::Engine {
    llama_context&context_;int batch_=0;unsigned emitted_=0,position_=prompt_tokens;bool bonus_=false;
    void process(unsigned count){
        begin();capture->batch_cleared(&batch_);for(unsigned i=0;i<count;++i)capture->token_added(&batch_,i);
        context_.first.fill(float(position_-prompt_tokens+11));context_.last.fill(float(position_-prompt_tokens+10+count));
        capture->original_process_returned(&context_,&batch_,0);capture->original_synchronize_returned(&context_);complete();
    }
    qwen_app::Token emit(){const int token=100+int(emitted_++);return {token,token==104?"":std::to_string(token),token==104};}
public:
    qwen_app::MtpOnlineDecision stats{};unsigned finishes=0;
    explicit Target(llama_context&context):context_(context){capture->batch_created(&batch_,&context_);capture->bind_target(&context_);}
    ~Target()override{capture->batch_freed(&batch_);}
    std::uint32_t tokenize(const std::string&)override{return prompt_tokens;}
    void prefill(std::uint32_t capacity)override{
        assert(capacity==256);
        for(unsigned offset=0;offset<prompt_tokens;){const auto count=std::min(32u,prompt_tokens-offset);
            begin();capture->batch_cleared(&batch_);capture->token_added(&batch_,count-1);context_.last.fill(10);
            capture->original_process_returned(&context_,&batch_,0);capture->original_synchronize_returned(&context_);complete();offset+=count;}
    }
    qwen_app::Token next()override{
        if(bonus_){bonus_=false;++stats.queued_bonus;return emit();}
        if(emitted_){process(1);++position_;}return emit();
    }
    qwen_app::Token verify(int draft){
        assert(emitted_&&!bonus_);++stats.attempts;process(2);
        if(draft==100+int(emitted_)){++stats.accepted;bonus_=true;position_+=2;}
        else{++stats.rejected;++position_;context_.first.fill(0);context_.last.fill(0);}
        return emit();
    }
    void finish()override{++finishes;}
};
int main(){
    for(bool single:{false,true})for(unsigned scenario=0;scenario<6;++scenario){
        live=created=freed=begins=completions=checkpoints=0;active=false;wrong_first=scenario==3;completed_auxiliary_tokens.clear();
        prompt_tokens=scenario==4?33:scenario==5?64:30;
        Capture captured({hidden,synchronize});capture=&captured;llama_model model;llama_context context;Target target(context);
        qwen_app::MtpOnlineHooks hooks{begin,complete,checkpoint,[](const char*){},[]{},[&](int draft){return target.verify(draft);},[&]{return target.stats;}};
        const unsigned maximum=scenario==2||scenario==3?1:6;const bool forced=scenario==1;
        qwen_app::PersistentMtpOnline online(target,&model,&context,std::move(hooks),maximum,forced,single);
        qwen_app::FirstGeneration generation(online);
        const auto&result=generation.run({"online_controls","causal control",256,32},[](const auto&){},[](const auto&,const auto&){},[](const char*){});
        assert(result.request_reset_completed&&result.token_ids==std::vector<int>({100,101,102,103})&&target.finishes==1);
        assert(!active&&begins==completions&&live==0&&created==1&&freed==1);
        const auto report=online.report();assert(report.at("causal_and_capture_checks_passed")==true&&report.at("auxiliary_KV_clear_count")==1);
        const unsigned required=2+report.at("auxiliary_proposals").get<unsigned>()+report.at("accepted_draft_catchups").get<unsigned>();
        assert(report.at("required_native_completions")==required&&report.at("extra_native_checkpoints")==checkpoints&&checkpoints==(single?0:required));
        if(scenario==0||scenario>=4)assert(target.stats.accepted==2&&target.stats.rejected==0&&completed_auxiliary_tokens==std::vector<int>({100,101,102,103}));
        if(scenario==1)assert(target.stats.accepted==1&&target.stats.rejected==1&&completed_auxiliary_tokens==std::vector<int>({100,101,102,103}));
        if(scenario==2)assert(target.stats.attempts==1&&target.stats.accepted==1&&completed_auxiliary_tokens==std::vector<int>({100,101}));
        if(scenario==3)assert(target.stats.attempts==1&&target.stats.rejected==1&&completed_auxiliary_tokens==std::vector<int>({100}));
    }
    for(bool single:{false,true})for(bool forced:{false,true}){
        live=created=freed=begins=completions=checkpoints=0;active=false;wrong_first=false;completed_auxiliary_tokens.clear();
        Capture captured({hidden,synchronize});capture=&captured;llama_model model,other_model;
        std::unique_ptr<qwen_app::PersistentMtpOnline>online;
        for(unsigned request=0;request<3;++request){
            prompt_tokens=request==0?30:request==1?33:64;
            llama_context context;Target target(context);
            auto hooks=[&]{return qwen_app::MtpOnlineHooks{begin,complete,checkpoint,[](const char*){},[]{},
                [&](int draft){return target.verify(draft);},[&]{return target.stats;}};};
            if(!online)online=std::make_unique<qwen_app::PersistentMtpOnline>(target,&model,&context,hooks(),6,forced,single,true);
            else{
                bool declined=false;
                try{online->begin_request(target,&other_model,&context,hooks());}catch(const std::runtime_error&){declined=true;}
                assert(declined&&live==1&&freed==0);
                online->begin_request(target,&model,&context,hooks());
            }
            bool early_declined=false;
            try{online->begin_request(target,&model,&context,hooks());}catch(const std::runtime_error&){early_declined=true;}
            assert(early_declined);
            qwen_app::FirstGeneration generation(*online);
            const auto&result=generation.run({"retained_controls","causal control",256,32},[](const auto&){},[](const auto&,const auto&){},[](const char*){});
            assert(result.request_reset_completed&&result.token_ids==std::vector<int>({100,101,102,103})&&target.finishes==1);
            const auto report=online->report();
            assert(!active&&begins==completions&&live==1&&created==1&&freed==0);
            assert(report.at("causal_and_capture_checks_passed")==true&&report.at("auxiliary_contexts_positively_retired")==false);
            assert(report.at("request_ordinal")==request&&report.at("lifetime_auxiliary_context_creations")==1&&report.at("lifetime_auxiliary_KV_clears")==request+1);
            assert(target.stats.accepted==(forced?1:2)&&target.stats.rejected==(forced?1:0));
            const unsigned required=1+report.at("auxiliary_proposals").get<unsigned>()+report.at("accepted_draft_catchups").get<unsigned>();
            assert(report.at("required_native_completions")==required&&report.at("extra_native_checkpoints")== (single?0:required));
            if(request==2){
                bool declined=false;
                try{online->begin_request(target,&model,&context,hooks());}catch(const std::runtime_error&){declined=true;}
                assert(declined&&live==1&&freed==0);
                online->retire_auxiliary();const auto retired=online->report();
                assert(retired.at("auxiliary_contexts_positively_retired")==true&&retired.at("required_native_completions")==required+1);
                assert(live==0&&created==1&&freed==1&&!active&&begins==completions);
            }
        }
    }
    // A failed mandatory boundary must retain the batch, context and the exact
    // owned input pointer. This is a CPU mock; no real GPU work is submitted.
    live=created=freed=begins=completions=checkpoints=0;active=false;wrong_first=false;prompt_tokens=30;submitted_hidden=nullptr;
    Capture captured({hidden,synchronize});capture=&captured;llama_model model;llama_context context;Target target(context);
    fail_at_completion=3;bool failed=false;
    {
        qwen_app::MtpOnlineHooks hooks{begin,complete,checkpoint,[](const char*){},[]{},[&](int draft){return target.verify(draft);},[&]{return target.stats;}};
        qwen_app::PersistentMtpOnline online(target,&model,&context,std::move(hooks),6,false,true,true);
        qwen_app::FirstGeneration generation(online);
        try{generation.run({"unknown_boundary","causal control",256,32},[](const auto&){},[](const auto&,const auto&){},[](const char*){});}
        catch(const std::runtime_error&){failed=true;}
        assert(failed&&target.finishes==0&&live==1&&created==1&&freed==0&&active&&begins==3&&completions==2);
        bool refused=false;try{online.retire_auxiliary();}catch(const std::runtime_error&){refused=true;}assert(refused&&freed==0);
    }
    assert(submitted_hidden&&std::all_of(submitted_hidden,submitted_hidden+10240,[](float value){return value==10;})&&freed==0&&live==1);
}

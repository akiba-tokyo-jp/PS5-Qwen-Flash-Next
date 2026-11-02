// SPDX-License-Identifier: MIT
#include "persistent_mtp_shadow.h"
#include "first_generation.h"
#include "llama-ext.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <vector>

struct llama_model {};
struct llama_vocab {};
struct llama_memory_i {llama_context*context=nullptr;};
struct llama_context {
    bool auxiliary=false,embeddings=false;
    llama_memory_i memory{this};
    std::array<float,10240>hidden{};
    std::vector<float>logits;
    std::vector<int>positions;
    unsigned clears=0;
};
struct llama_batch_ext {llama_context*context=nullptr;int token=-1,position=-1;llama_embd hidden{};bool logits=false;};
namespace {
llama_vocab vocabulary;
unsigned live_aux=0,maximum_live=0,created=0,freed=0,begins=0,completions=0;
bool active=false;
void begin(){assert(!active);active=true;++begins;}
void complete(){assert(active);active=false;++completions;}
void checkpoint(){assert(active);}
}
void llama_set_embeddings_nextn(llama_context*c,bool enabled,bool masked){assert(c&&enabled&&masked);c->embeddings=true;}
float*llama_get_embeddings_nextn_ith(llama_context*c,int32_t index){assert(active&&c&&c->embeddings&&index==-1);return c->hidden.data();}
extern "C" {
llama_context_params llama_context_default_params(){return {};}
llama_context*llama_init_from_model(llama_model*m,llama_context_params p){
    assert(m&&p.ctx_type==LLAMA_CONTEXT_TYPE_MTP&&p.n_ctx==256&&p.n_batch==1&&p.n_ubatch==1&&p.n_seq_max==1&&p.n_rs_seq==0);
    assert(p.moe_cache_size==0&&p.type_k==GGML_TYPE_F32&&p.type_v==GGML_TYPE_F32&&p.offload_kqv&&p.op_offload);
    auto*c=new llama_context;c->auxiliary=true;c->logits.resize(248320);++live_aux;++created;maximum_live=std::max(maximum_live,live_aux);return c;
}
void llama_free(llama_context*c){assert(active&&c&&c->auxiliary&&live_aux==1);--live_aux;++freed;delete c;}
std::uint32_t llama_n_ctx(const llama_context*c){assert(c);return 256;}
llama_memory_t llama_get_memory(const llama_context*c){assert(c);return const_cast<llama_memory_i*>(&c->memory);}
void llama_memory_clear(llama_memory_t memory,bool data){assert(active&&memory&&data&&memory->context->auxiliary);memory->context->positions.clear();++memory->context->clears;}
void llama_synchronize(llama_context*c){assert(active&&c);}
const llama_vocab*llama_model_get_vocab(const llama_model*m){assert(m);return &vocabulary;}
int32_t llama_vocab_n_tokens(const llama_vocab*v){assert(v==&vocabulary);return 248320;}
llama_batch_ext*llama_batch_ext_init(llama_context*c){assert(active&&c&&c->auxiliary);auto*b=new llama_batch_ext;b->context=c;return b;}
void llama_batch_ext_free(llama_batch_ext*b){assert(active&&b);delete b;}
void llama_batch_ext_clear(llama_batch_ext*b){assert(active&&b);const auto context=b->context;*b={};b->context=context;}
int32_t llama_batch_ext_add_token(llama_batch_ext*b,llama_seq_id seq,llama_token token){assert(active&&b&&seq==0&&b->token==-1);b->token=token;return 0;}
bool llama_batch_ext_set_pos(llama_batch_ext*b,int32_t index,const llama_pos*position){assert(active&&b&&index==0&&position);b->position=*position;return true;}
bool llama_batch_ext_set_output_logits(llama_batch_ext*b,int32_t index,bool value){assert(active&&b&&index==0&&value);b->logits=value;return true;}
bool llama_batch_ext_set_embd_state(llama_batch_ext*b,int32_t index,llama_embd hidden){assert(active&&b&&index==0&&hidden.data&&hidden.n_rows==1&&hidden.n_embd==10240);b->hidden=hidden;return true;}
int32_t llama_process(llama_context*c,llama_process_type type,llama_batch_ext*b){
    assert(active&&c&&b&&c==b->context&&type==LLAMA_PROCESS_TYPE_DECODE&&b->logits&&b->position==b->token-70);
    assert(std::all_of(b->hidden.data,b->hidden.data+10240,[&](float x){return x==float(b->token-90);}));
    if(!c->positions.empty())assert(b->position==c->positions.back()+1);
    c->positions.push_back(b->position);std::fill(c->logits.begin(),c->logits.end(),-1.0f);c->logits[b->token+1]=1.0f;return 0;
}
float*llama_get_logits_ith(llama_context*c,int32_t index){assert(active&&c&&c->auxiliary&&index==-1);return c->logits.data();}
}
class Target final:public qwen_app::Engine {
    llama_context&context_;unsigned step_=0;
public:
    unsigned capacity=0,finishes=0;
    explicit Target(llama_context&c):context_(c){}
    std::uint32_t tokenize(const std::string&)override{return 30;}
    void prefill(std::uint32_t context_tokens)override{assert(context_tokens==256);capacity=context_tokens;context_.hidden.fill(10);}
    qwen_app::Token next()override{
        const unsigned current=step_++;if(current)context_.hidden.fill(float(10+current));
        return {int(100+current),current==3?"":std::to_string(100+current),current==3};
    }
    void finish()override{++finishes;}
};
int main(){
    for(bool reverse:{false,true}){
        maximum_live=created=freed=begins=completions=0;active=false;
        llama_model model;llama_context context;Target target(context);
        qwen_app::MtpShadowBoundaries boundaries{begin,complete,checkpoint,[](const char*){},[]{},[]{return true;}};
        qwen_app::PersistentMtpShadow shadow(target,&model,&context,std::move(boundaries),reverse);
        qwen_app::FirstGeneration generation(shadow);unsigned tokens=0;
        const auto&r=generation.run({"actual_first_generation","host control",256,32},[](const auto&){},
            [&](const auto&,const auto&){++tokens;},[](const char*){});
        assert(r.request_reset_completed&&r.metrics.prompt_tokens==30&&r.token_ids==std::vector<int>({100,101,102})&&tokens==3);
        assert(target.capacity==256&&target.finishes==1&&!active&&begins==completions&&live_aux==0&&maximum_live==1&&created==2&&freed==2);
        const auto report=shadow.report();assert(report.at("proposals")==3&&report.at("outputs")==3);
        assert(report.at("KV_clear_counts")==nlohmann::json::array({4,1})&&report.at("target_prediction_matches")==nlohmann::json::array({3,3}));
        assert(report.at("first_auxiliary_arm")==unsigned(reverse)&&report.at("observations").size()==6);
    }
}

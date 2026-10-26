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
int32_t llama_tokenize(const llama_vocab *,const char *,int32_t,llama_token *out,int32_t size,bool,bool){
    if(!out||size<30)return -30;for(int i=0;i<30;++i)out[i]=i+1;return 30;
}
void llama_batch_ext_clear(llama_batch_ext *b){b->tokens.clear();b->positions.clear();}
int32_t llama_batch_ext_add_token(llama_batch_ext *b,llama_seq_id seq,llama_token token){check(seq==0);b->tokens.push_back(token);b->positions.push_back(-1);return int(b->tokens.size()-1);}
bool llama_batch_ext_set_pos(llama_batch_ext *b,int32_t index,const llama_pos *position){b->positions.at(index)=*position;return true;}
bool llama_batch_ext_set_output_logits(llama_batch_ext *,int32_t,bool output){check(output);return true;}
int32_t llama_process(llama_context *c,llama_process_type,llama_batch_ext *b){
    check(active);++processes;
    if(c->memory.KV_tag!=c->memory.position||c->memory.recurrent_tag!=c->memory.position||c->memory.PLE_tag!=c->memory.position)return -1;
    check(!b->positions.empty()&&b->positions[0]==c->memory.position);
    c->memory.position=b->positions.back()+1;c->memory.KV_tag=c->memory.recurrent_tag=c->memory.PLE_tag=c->memory.position;
    const int position=c->memory.position;const int selected=position<30?0:std::min(33,position+1);
    c->logits.fill(-1.125f);c->logits[selected]=10.25f;
    for(int layer=0;layer<48;++layer)routes.push_back({b->positions[0],int(b->tokens.size()),layer});return 0;
}
void llama_synchronize(llama_context *){check(active);}
uint32_t llama_n_ctx(const llama_context *){return 256;}
uint32_t llama_n_batch(const llama_context *){return 4;}
uint32_t llama_n_ubatch(const llama_context *){return 4;}
llama_memory_t llama_get_memory(const llama_context *c){return const_cast<llama_memory_i *>(&c->memory);}
void llama_memory_clear(llama_memory_t memory,bool){*memory={};}
llama_pos llama_memory_seq_pos_min(llama_memory_t,llama_seq_id seq){check(seq==0);return 0;}
llama_pos llama_memory_seq_pos_max(llama_memory_t m,llama_seq_id seq){check(seq==0);return m->position-1;}
int32_t llama_vocab_n_tokens(const llama_vocab *){return 64;}
float *llama_get_logits_ith(llama_context *c,int32_t){return c->logits.data();}
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
    if(scenario=="missing_PLE")++c->memory.PLE_tag;return scenario=="short_restore"?15:16;
}
}
int main(int argc,char **argv) {
    check(argc==2);scenario=argv[1];llama_model model;llama_context context{&model,{},{},{}};
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

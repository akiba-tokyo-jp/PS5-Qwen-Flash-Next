// SPDX-License-Identifier: MIT
#include "prefill_row_generation.h"
#include <iostream>
using namespace qwen_app;
void need(bool value){if(!value)throw std::runtime_error("Short diagnostic request control failed");}
struct Fake final:Engine {
    unsigned tokenizations=0,prefills=0,nexts=0,finishes=0;bool fail=false;
    std::uint32_t tokenize(const std::string&)override{++tokenizations;return 30;}
    void prefill(std::uint32_t n)override{need(n==256);++prefills;}
    Token next()override{++nexts;if(fail)throw std::runtime_error("Synthetic unknown operation");return{16,"1",false};}
    void finish()override{++finishes;}
};
template<class F>void reject(F f){try{f();}catch(const std::exception&){return;}throw std::runtime_error("Invalid short request accepted");}
int main(){try{
    Request request{"prefill-row","original rendered prompt",256,1};
    auto intent=[](const Request&){};auto token=[](const Token&,const Metrics&){};auto stage=[](const char*){};
    Fake good;PrefillRowGeneration once(good);unsigned persisted=0;
    const auto&r=once.run(request,intent,[&](const Token&,const Metrics&){++persisted;},stage);
    need(r.request_reset_completed&&r.metrics.generated_tokens==1&&persisted==1&&good.tokenizations==1&&good.prefills==1&&good.nexts==1&&good.finishes==1);
    reject([&]{once.run(request,intent,token,stage);});
    for(unsigned bound:{0u,2u,32u}){Fake e;PrefillRowGeneration trial(e);auto invalid=request;invalid.max_output_tokens=bound;
        reject([&]{trial.run(invalid,intent,token,stage);});need(!e.tokenizations&&!e.prefills&&!e.nexts&&!e.finishes);}
    Fake stopped;PrefillRowGeneration durable(stopped);reject([&]{durable.run(request,[](const Request&){throw std::runtime_error("Synthetic persistence failure");},token,stage);});need(!stopped.tokenizations);
    Fake uncertain;uncertain.fail=true;PrefillRowGeneration no_release(uncertain);reject([&]{no_release.run(request,intent,token,stage);});need(uncertain.nexts==1&&!uncertain.finishes);
    Fake original;FirstGeneration unchanged(original);reject([&]{unchanged.run(request,intent,token,stage);});need(!original.tokenizations);
    std::cout<<"Eight short request controls passed\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}

// SPDX-License-Identifier: MIT
#define QWEN_F32_OBSERVER_SETTER "mock_F32_setter"
#define QWEN_F32_OBSERVER_COLUMNS 4
#include "full_f32_observer.cpp"
#include <cassert>
#include <string>
#include <vector>
static Observer installed;
static std::vector<std::string> stages;
extern "C" void qwen_native_stage(const char*text){stages.emplace_back(text);}
extern "C" void qwen_f32_real_setter(qwen_app::LlamaEngine*,Observer observer){installed=std::move(observer);}
int main(){
    unsigned forwarded=0;const float values[]={1.0f,-2.5f,0.0f,3.0f};
    qwen_f32_wrap_setter(nullptr,[&](const float*v,std::size_t n){assert(v==values&&n==4);++forwarded;});
    installed(values,4);installed(values,4);qwen_f32_wrap_setter(nullptr,{});
    assert(forwarded==2&&!installed&&stages.size()==3);
    assert(stages[0].find("request=1 row=1 columns=4 sha256=")!=std::string::npos);
    assert(stages[0].substr(stages[0].find("sha256="))==stages[1].substr(stages[1].find("sha256=")));
    assert(stages[2]=="F32_request_completed request=1 rows=2 failures=0");
    qwen_f32_wrap_setter(nullptr,[&](const float*,std::size_t){++forwarded;});
    installed(values,3);qwen_f32_wrap_setter(nullptr,{});
    assert(forwarded==3&&stages.back()=="F32_request_completed request=2 rows=1 failures=1");
    std::puts(stages[0].c_str());
    return 0;
}

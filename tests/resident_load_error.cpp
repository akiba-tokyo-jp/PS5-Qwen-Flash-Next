// SPDX-License-Identifier: MIT
#include <atomic>
#include <thread>
enum ggml_log_level {GGML_LOG_LEVEL_INFO=1,GGML_LOG_LEVEL_ERROR=2};
static std::atomic<unsigned> forwarded{0};
static void native_log(ggml_log_level,const char *,void *){++forwarded;}
#include "resident_load_error.h"
#include <iostream>
int main(){
    qwen_app::resident_native_log(GGML_LOG_LEVEL_INFO,"ordinary",nullptr);
    if(!qwen_app::resident_last_model_error().empty())throw std::runtime_error("Non-error captured");
    const std::string huge(8192,'x');qwen_app::resident_native_log(GGML_LOG_LEVEL_ERROR,huge.c_str(),nullptr);
    if(qwen_app::resident_last_model_error()!=std::string(2048,'x'))throw std::runtime_error("Diagnostic bound differs");
    std::thread a([]{for(unsigned i=0;i<100;++i)qwen_app::resident_native_log(GGML_LOG_LEVEL_ERROR,"abc",nullptr);});
    std::thread b([]{for(unsigned i=0;i<100;++i)qwen_app::resident_native_log(GGML_LOG_LEVEL_ERROR,"def",nullptr);});
    a.join();b.join();qwen_app::resident_native_log(GGML_LOG_LEVEL_ERROR,"final-error",nullptr);
    const auto text=qwen_app::resident_last_model_error();if(text.size()!=2048||text.substr(text.size()-11)!="final-error"||forwarded!=203)
        throw std::runtime_error("Concurrent error capture or original forwarding differs");
    std::cout<<"{\"bounded_concurrent_error_capture\":true,\"original_log_forwarded\":true}\n";
}

// SPDX-License-Identifier: MIT
// Execute real admission control against fixed, synthetic API-stub readbacks.
#include "operator_admission.h"
#include "model_integrity.h"
#include "ggml.h"
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
namespace {
int mode, creates, frees, computes, reads, backends, checks;
bool synchronized, release_admitted, reference_done;
ggml_context context; ggml_cgraph graph;
ggml_tensor weights, input, matvec, norm, silu;
void check(bool value) { if (!value) throw std::runtime_error("Operation ownership contract failed"); }
void reset(int value) {
    mode=value;creates=frees=computes=reads=backends=checks=0;
    synchronized=release_admitted=reference_done=false;
}
void stage(const char * text) {
    if (!std::strcmp(text,"operators_CPU_double_references_completed_before_compute_backend")) {
        check(backends==0);reference_done=true;
    }
    if (!std::strcmp(text,"operators_all_supported_before_device_allocation")) check(checks==3);
    if (!std::strcmp(text,"operators_synchronized_before_readbacks")) check(synchronized&&reads==0);
    if (!std::strcmp(text,"operators_all_numerical_gates_passed_before_release")) {
        check(mode==0&&computes==1&&synchronized&&reads==3&&frees==0);release_admitted=true;
    }
    if (!std::strcmp(text,"operators_numerical_failure_backing_retained")) check(frees==0&&!release_admitted);
}
}
namespace qwen_app {
void verify_model_file(const std::string &,std::uint64_t bytes,const std::string & sha,
                      const std::function<void(std::uint64_t)> &,unsigned timeout) {
    check(bytes==81920&&sha==original_weight_fixture_sha256&&timeout==30&&backends==0);
    if(mode==9)throw std::runtime_error("synthetic hash refusal");
}
}
extern "C" {
std::size_t ggml_tensor_overhead(){return 64;}
std::size_t ggml_graph_overhead_custom(std::size_t count,bool gradients){check(count==32&&!gradients);return 256;}
ggml_context *ggml_init(ggml_init_params p){check(p.no_alloc&&!p.mem_buffer&&p.mem_size==896);return &context;}
ggml_tensor *ggml_new_tensor_2d(ggml_context *c,ggml_type type,std::int64_t width,std::int64_t height){
    check(c==&context&&width==2560);++creates;
    auto *out=creates==1?&weights:&input;*out={type,width,height,creates};
    check((creates==1&&type==GGML_TYPE_BF16&&height==16)||(creates==2&&type==GGML_TYPE_F32&&height==1));return out;
}
ggml_tensor *ggml_mul_mat(ggml_context *c,ggml_tensor *a,ggml_tensor *b){check(c==&context&&a==&weights&&b==&input);matvec={GGML_TYPE_F32,16,1,3};return &matvec;}
ggml_tensor *ggml_rms_norm(ggml_context *c,ggml_tensor *a,float eps){check(c==&context&&a==&input&&eps==1e-6f);norm={GGML_TYPE_F32,2560,1,4};return &norm;}
ggml_tensor *ggml_silu(ggml_context *c,ggml_tensor *a){check(c==&context&&a==&norm);silu={GGML_TYPE_F32,2560,1,5};return &silu;}
void ggml_set_input(ggml_tensor *t){check(t==&weights||t==&input);}
void ggml_set_output(ggml_tensor *t){check(t==&matvec||t==&norm||t==&silu);}
ggml_cgraph *ggml_new_graph_custom(ggml_context *c,std::size_t n,bool gradients){check(c==&context&&n==32&&!gradients);return &graph;}
void ggml_build_forward_expand(ggml_cgraph *g,ggml_tensor *t){check(g==&graph&&(t==&matvec||t==&norm||t==&silu));}
float ggml_bf16_to_fp32(ggml_bf16_t value){std::uint32_t bits=std::uint32_t(value.bits)<<16;float out;std::memcpy(&out,&bits,4);return out;}
ggml_backend_t ggml_backend_vk_init(std::size_t i){check(i==0&&reference_done);++backends;return mode==6?nullptr:&context;}
const char *ggml_backend_name(ggml_backend_t b){check(b==&context);return "host_API_stub";}
void *ggml_backend_get_device(ggml_backend_t b){check(b==&context);return b;}
bool ggml_backend_dev_supports_op(void *b,const ggml_tensor *t){check(b==&context&&(t==&matvec||t==&norm||t==&silu));++checks;return !(mode==1&&t==&norm);}
ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors(ggml_context *c,ggml_backend_t b){check(c==&context&&b==&context&&checks==3);return mode==2?nullptr:&graph;}
void ggml_backend_tensor_set(ggml_tensor *t,const void *data,std::size_t offset,std::size_t bytes){
    check(offset==0&&data);
    if(t==&weights)check(bytes==81920&&static_cast<const std::uint16_t *>(data)[0]==0x3d80);
    else check(t==&input&&bytes==10240&&static_cast<const float *>(data)[0]==-1.5f);
}
ggml_status ggml_backend_graph_compute(ggml_backend_t b,ggml_cgraph *g){check(b==&context&&g==&graph&&computes==0);++computes;return mode==3?GGML_STATUS_FAILED:GGML_STATUS_SUCCESS;}
void ggml_backend_synchronize(ggml_backend_t b){check(b==&context&&computes==1);synchronized=true;}
void ggml_backend_tensor_get(const ggml_tensor *t,void *data,std::size_t offset,std::size_t bytes){
    check(synchronized&&frees==0&&offset==0);++reads;
    if(mode==7&&t==&norm)throw std::runtime_error("synthetic readback refusal");
    auto *values=static_cast<float *>(data);
    if(t==&matvec){check(bytes==64);for(int i=0;i<16;++i)values[i]=-.15625f;if(mode==4)values[0]+=.01f;}
    else {
        check((t==&norm||t==&silu)&&bytes==10240);
        const double scale=1/std::sqrt(2558.75/2560+1e-6);
        for(unsigned i=0;i<2560;++i){const double value=(int(i%7)-3)*.5*scale;values[i]=t==&norm?value:value/(1+std::exp(-value));}
        if(mode==5&&t==&norm)values[0]=std::numeric_limits<float>::quiet_NaN();
    }
}
void ggml_backend_buffer_free(ggml_backend_buffer_t b){check(b==&graph&&release_admitted);++frees;}
void ggml_free(ggml_context *c){check(c==&context&&release_admitted);++frees;}
void ggml_backend_free(ggml_backend_t b){check(b==&context&&release_admitted);++frees;}
}
int main(int argc,char **argv){
    try{
        check(argc==2);
        const std::vector<std::uint16_t> bits(2560*16,0x3d80);
        for(int scenario=0;scenario<=8;++scenario){
            reset(scenario);bool threw=false;
            try{
                auto selected=bits;if(mode==8)selected.pop_back();
                const auto result=qwen_app::admit_original_weight_operations(selected,stage);
                check(mode==0||mode==4||mode==5);
                check(result.passed==(mode==0)&&result.matvec.values==16&&result.rms_norm.values==2560&&result.silu.values==2560);
                check(computes==1&&reads==3&&frees==(mode==0?3:0));
            }catch(const std::exception &){threw=true;}
            check(threw==(mode==1||mode==2||mode==3||mode==6||mode==7||mode==8));
            if(mode!=0)check(frees==0);if(mode==1||mode==2||mode==6||mode==8)check(computes==0);
        }
        reset(0);
        {std::ofstream out(argv[1],std::ios::binary);out.write(reinterpret_cast<const char *>(bits.data()),bits.size()*2);}
        check(qwen_app::load_original_weight_fixture(argv[1],qwen_app::original_weight_fixture_sha256)==bits);
        {std::ofstream out(argv[1],std::ios::binary);out.write("xx",2);}
        bool rejected=false;try{qwen_app::load_original_weight_fixture(argv[1],qwen_app::original_weight_fixture_sha256);}catch(const std::exception &){rejected=true;}check(rejected&&backends==0);
        auto nonfinite=bits;nonfinite[0]=0x7f80;
        {std::ofstream out(argv[1],std::ios::binary);out.write(reinterpret_cast<const char *>(nonfinite.data()),nonfinite.size()*2);}
        rejected=false;try{qwen_app::load_original_weight_fixture(argv[1],qwen_app::original_weight_fixture_sha256);}catch(const std::exception &){rejected=true;}check(rejected&&backends==0);
        std::cout<<"Original-weight graph shape, all readbacks, fixed numerical gates, loader failures and no-retry retention passed; synthetic API stubs only\n";
    }catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}
}

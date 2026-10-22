// SPDX-License-Identifier: MIT
// Execute the actual admission owner with API stubs, including failures that
// must retain backing. This is not GPU execution or a model inference result.
#include "../native/app/gpu_admission.h"
#include "ggml.h"
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
namespace {
int mode = 0, tensors = 0, frees = 0, computes = 0;
bool allocated = false, synchronized = false, readback = false;
bool release_admitted = false, stage_seen = false;
ggml_context context;
ggml_cgraph graph;
ggml_tensor weight{}, input{}, output{};
std::array<ggml_bf16_t,512> matrix{};
std::array<float,32> vector{};
std::array<float,16> actual{};
constexpr std::array<float,16> reference = {-1.5f,9,6.75f,-1.875f,-2,-8.5f,-0.125f,4,-0.375f,3.75f,1.5f,-7.125f,3.375f,3.25f,-3.25f,-1.25f};
void check(bool value) { if (!value) throw std::runtime_error("GPU admission ownership contract failed"); }
void * backend() { return &context; }
void stage(const char * value) {
    if (!stage_seen) { check(!std::strcmp(value,"BF16_before_backend_init")); stage_seen=true; }
    if (!std::strcmp(value,"BF16_graph_compute_returned_success")) check(computes==1&&!synchronized);
    if (!std::strcmp(value,"BF16_synchronize_returned_before_readback")) check(synchronized&&!readback);
    if (!std::strcmp(value,"BF16_numerical_gate_passed_before_release")) {
        check(mode==0&&synchronized&&readback&&frees==0); release_admitted=true;
    }
    if (!std::strcmp(value,"BF16_numerical_gate_failed_backing_retained")) check((mode==4||mode==5)&&!release_admitted&&frees==0);
}
}
extern "C" std::size_t ggml_tensor_overhead() { return 64; }
extern "C" std::size_t ggml_graph_overhead_custom(std::size_t nodes, bool gradients) { check(nodes==32&&!gradients); return 256; }
extern "C" ggml_context * ggml_init(ggml_init_params p) { check(p.no_alloc&&!p.mem_buffer); return &context; }
extern "C" ggml_tensor * ggml_new_tensor_2d(ggml_context * c, ggml_type type, std::int64_t w, std::int64_t h) {
    check(c==&context); auto * result = tensors++ ? &input : &weight; *result={type,w,h,tensors}; return result;
}
extern "C" ggml_tensor * ggml_mul_mat(ggml_context * c, ggml_tensor * a, ggml_tensor * b) {
    check(c==&context&&a==&weight&&b==&input&&a->type==GGML_TYPE_BF16&&b->type==GGML_TYPE_F32);
    check(a->width==32&&a->height==16&&b->width==32&&b->height==1); output={GGML_TYPE_F32,16,1,3}; return &output;
}
extern "C" void ggml_set_input(ggml_tensor * t) { check(t==&weight||t==&input); }
extern "C" void ggml_set_output(ggml_tensor * t) { check(t==&output); }
extern "C" ggml_cgraph * ggml_new_graph_custom(ggml_context * c,std::size_t n,bool g) { check(c==&context&&n==32&&!g); return &graph; }
extern "C" void ggml_build_forward_expand(ggml_cgraph * g,ggml_tensor * t) { check(g==&graph&&t==&output); }
extern "C" ggml_bf16_t ggml_fp32_to_bf16(float value) { std::uint32_t bits;std::memcpy(&bits,&value,4);return {std::uint16_t(bits>>16)}; }
extern "C" ggml_backend_t ggml_backend_vk_init(std::size_t index) { check(index==0);return mode==6?nullptr:backend(); }
extern "C" const char * ggml_backend_name(ggml_backend_t b) { check(b==backend());return "host_API_stub"; }
extern "C" void * ggml_backend_get_device(ggml_backend_t b) { check(b==backend());return b; }
extern "C" bool ggml_backend_dev_supports_op(void * b,const ggml_tensor * t) { check(b==backend()&&t==&output);return mode!=1; }
extern "C" ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors(ggml_context * c,ggml_backend_t b) {
    check(c==&context&&b==backend()&&mode!=1);allocated=mode!=2;return allocated?&weight:nullptr;
}
extern "C" void ggml_backend_tensor_set(ggml_tensor * t,const void * data,std::size_t offset,std::size_t bytes) {
    check(allocated&&offset==0);
    if(t==&weight){check(bytes==sizeof(matrix));std::memcpy(matrix.data(),data,bytes);}
    else{check(t==&input&&bytes==sizeof(vector));std::memcpy(vector.data(),data,bytes);}
}
extern "C" ggml_status ggml_backend_graph_compute(ggml_backend_t b,ggml_cgraph * g) {
    check(b==backend()&&g==&graph&&allocated);++computes;if(mode==3)return GGML_STATUS_FAILED;
    for(unsigned r=0;r<16;++r)for(unsigned k=0;k<32;++k) {
        std::uint32_t bits=std::uint32_t(matrix[r*32+k].bits)<<16;float value;std::memcpy(&value,&bits,4);
        actual[r]+=value*vector[k];
    }
    check(actual==reference);
    if(mode==4)actual[0]+=0.125f;if(mode==5)actual[0]=std::numeric_limits<float>::quiet_NaN();
    return GGML_STATUS_SUCCESS;
}
extern "C" void ggml_backend_synchronize(ggml_backend_t b) { check(b==backend()&&mode!=3);synchronized=true; }
extern "C" void ggml_backend_tensor_get(const ggml_tensor * t,void * data,std::size_t offset,std::size_t bytes) {
    check(synchronized&&t==&output&&offset==0&&bytes==sizeof(actual));std::memcpy(data,actual.data(),bytes);readback=true;
}
extern "C" void ggml_backend_buffer_free(ggml_backend_buffer_t b) { check(mode==0&&release_admitted&&readback&&b==&weight);++frees; }
extern "C" void ggml_free(ggml_context * c) { check(mode==0&&readback&&c==&context);++frees; }
extern "C" void ggml_backend_free(ggml_backend_t b) { check(mode==0&&readback&&b==backend());++frees; }
int main(int argc,char ** argv) {
    try {
        check(argc==2);mode=std::atoi(argv[1]);check(mode>=0&&mode<=6);bool threw=false;
        try {
            const auto result=qwen_app::admit_bf16_gpu(stage);
            check(mode==0||mode==4||mode==5);check(result.passed==(mode==0));
            for(unsigned i=0;i<16;++i)check(result.expected[i]==reference[i]);
            check(readback&&synchronized&&computes==1);
        } catch(const std::runtime_error & error) {
            if(mode==0||mode==4||mode==5)throw;
            const char * expected = mode==1 ? "Original-BF16 admission operation is unsupported" :
                mode==2 ? "BF16 admission device allocation failed" :
                mode==3 ? "BF16 admission compute failed; resources retained" : "Vulkan admission backend is unavailable";
            check(std::strcmp(error.what(),expected)==0);threw=true;
        }
        check(threw==(mode==1||mode==2||mode==3||mode==6));check(frees==(mode==0?3:0));check(stage_seen&&release_admitted==(mode==0));
        if(mode==1||mode==2||mode==6)check(computes==0&&!readback);
        std::cout<<"Admission dimensions, exact BF16 data, finite gate and success-only release passed; API stubs only\n";
    } catch(const std::exception & e){std::cerr<<e.what()<<'\n';return 1;}
}

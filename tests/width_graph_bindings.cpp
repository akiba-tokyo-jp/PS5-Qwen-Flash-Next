// SPDX-License-Identifier: MIT
#include "width_graph_bindings.h"
#include <iostream>
using namespace qwen_app;
void check(bool b){if(!b)throw std::runtime_error("Width topology check failed");}
int main(){try{
    ggml_tensor weight{},state{},input{},product{},view{},copy{};
    weight.data=reinterpret_cast<void*>(0x1000);weight.buffer=reinterpret_cast<ggml_backend_buffer*>(0x2000);
    state.data=reinterpret_cast<void*>(0x3000);state.buffer=reinterpret_cast<ggml_backend_buffer*>(0x4000);
    product.src[0]=&weight;product.src[1]=&input;view.src[0]=&product;view.view_src=&product;
    product.flags=GGML_TENSOR_FLAG_OUTPUT;input.extra=reinterpret_cast<void*>(0x1234);
    ggml_tensor*nodes[]{&product,&view};ggml_tensor*leaves[]{&weight,&state,&input};WidthGraphBindings plan;plan.capture(nodes,2,leaves,3);
    product.flags=0;input.extra=reinterpret_cast<void*>(0x5678);
    product.src[1]=&copy;view.src[0]=&copy;
    for(auto*t:{&input,&product,&view}){t->data=reinterpret_cast<void*>(0xdead);t->buffer=reinterpret_cast<ggml_backend_buffer*>(0xbeef);}
    plan.restore_after_positive_sync();check(product.src[1]==&input&&view.src[0]==&product&&view.view_src==&product);
    for(auto*t:{&input,&product,&view})check(!t->data&&!t->buffer);
    check(product.flags==GGML_TENSOR_FLAG_OUTPUT&&input.extra==reinterpret_cast<void*>(0x1234));
    check(weight.data==reinterpret_cast<void*>(0x1000)&&state.data==reinterpret_cast<void*>(0x3000)&&weight.buffer&&state.buffer);
    plan.clear();bool refused=false;try{plan.restore_after_positive_sync();}catch(const std::exception&){refused=true;}check(refused);
    std::cout<<"Original source links restored, stale compute bindings cleared, external weights/KV retained.\n";
}catch(const std::exception&e){std::cerr<<e.what();return 1;}}

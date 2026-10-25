// SPDX-License-Identifier: MIT
#include "bf16_decode_queue.h"
#include "bf16_decode_probe_io.h"
namespace {qwen_app::BF16DecodeQueue *queue=nullptr;}
extern "C" int bf16_probe_start(){
    if(queue)return 0;
    try{queue=new qwen_app::BF16DecodeQueue;queue->start();return 1;}catch(...){return 0;}
}
extern "C" int bf16_probe_decode(const unsigned char *input,size_t bytes,unsigned char *output,size_t capacity,
    unsigned char *scratch,size_t scratch_bytes){
    qwen_bf16_decode_plan plan;
    if(!queue||!qwen_bf16_prepare(input,bytes,output,capacity,scratch,scratch_bytes,&plan))return 0;
    try{return queue->decode(plan)?1:0;}catch(...){return -1;}
}
extern "C" int bf16_probe_stop(){
    if(!queue)return 0;
    try{queue->stop_completed();delete queue;queue=nullptr;return 1;}catch(...){return 0;}
}

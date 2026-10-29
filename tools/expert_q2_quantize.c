// SPDX-License-Identifier: MIT
// Q2_0: pinned ggml's 64-value block, FP16 scale and 16 packed bytes.
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#if defined(_WIN32)
#define Q2_EXPORT __declspec(dllexport)
#else
#define Q2_EXPORT __attribute__((visibility("default")))
#endif
Q2_EXPORT int qwen_quantize_bf16_q2_0(const uint16_t *input,uint8_t *output,size_t values){
    if(!input||!output||!values||values%64)return 1;
    for(size_t b=0;b<values/64;++b){
        float x[64],scale=0;
        for(unsigned j=0;j<64;++j){
            const uint32_t bits=(uint32_t)input[b*64+j]<<16;
            memcpy(x+j,&bits,4);
            if(!isfinite(x[j]))return 2;
            if(fabsf(x[j])>scale)scale=fabsf(x[j]);
        }
        const _Float16 half=(_Float16)scale;
        if(!isfinite((float)half))return 3;
        memcpy(output+b*18,&half,2);memset(output+b*18+2,0,16);
        const float inverse=scale?1.0f/scale:0;
        for(unsigned j=0;j<64;++j){
            int q=(int)roundf(x[j]*inverse)+1;
            if(q<0)q=0;if(q>3)q=3;
            output[b*18+2+j/4]|=(uint8_t)(q<<(2*(j%4)));
        }
    }
    return 0;
}

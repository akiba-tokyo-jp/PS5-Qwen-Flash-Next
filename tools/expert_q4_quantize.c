// SPDX-License-Identifier: MIT
// Independent Q4_0 encoder. The file format is the pinned ggml 32-value block:
// one IEEE FP16 scale followed by sixteen paired signed four-bit values.
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#if defined(_WIN32)
#define Q4_EXPORT __declspec(dllexport)
#else
#define Q4_EXPORT __attribute__((visibility("default")))
#endif

Q4_EXPORT int qwen_quantize_bf16_q4_0(const uint16_t *input,uint8_t *output,size_t values){
    if(!input||!output||!values||values%32)return 1;
    for(size_t block=0;block<values/32;++block){
        float data[32],largest=0,selected=0;
        for(unsigned j=0;j<32;++j){
            const uint32_t bits=(uint32_t)input[block*32+j]<<16;
            memcpy(data+j,&bits,4);
            if(!isfinite(data[j]))return 2;
            if(fabsf(data[j])>largest){largest=fabsf(data[j]);selected=data[j];}
        }
        const float scale=selected/-8.0f,inverse=scale?1.0f/scale:0;
        const _Float16 half=(_Float16)scale;
        if(!isfinite((float)half))return 3;
        memcpy(output+block*18,&half,2);
        for(unsigned j=0;j<16;++j){
            int lo=(int)(data[j]*inverse+8.5f),hi=(int)(data[j+16]*inverse+8.5f);
            if(lo<0)lo=0;if(lo>15)lo=15;
            if(hi<0)hi=0;if(hi>15)hi=15;
            output[block*18+2+j]=(uint8_t)(lo|(hi<<4));
        }
    }
    return 0;
}

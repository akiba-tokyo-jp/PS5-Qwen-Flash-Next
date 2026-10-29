// SPDX-License-Identifier: MIT
// Q2_0 storage with fitted signed FP16 scales; decode remains (q - 1) * d.
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#if defined(_WIN32)
#define Q2_EXPORT __declspec(dllexport)
#else
#define Q2_EXPORT __attribute__((visibility("default")))
#endif
static int level(float x,float d){
    int q=(int)roundf(x/d);return q< -1?-1:q>2?2:q;
}
static double error(const float*x,float d){
    double total=0;
    for(unsigned j=0;j<64;++j){const double delta=(double)x[j]-(d?level(x[j],d)*d:0);total+=delta*delta;}
    return total;
}
Q2_EXPORT int qwen_quantize_bf16_q2_0(const uint16_t*input,uint8_t*output,size_t values){
    if(!input||!output||!values||values%64)return 1;
    for(size_t b=0;b<values/64;++b){
        float x[64],maximum=0;
        for(unsigned j=0;j<64;++j){const uint32_t bits=(uint32_t)input[b*64+j]<<16;memcpy(x+j,&bits,4);
            if(!isfinite(x[j]))return 2;if(fabsf(x[j])>maximum)maximum=fabsf(x[j]);}
        if(!isfinite((float)(_Float16)maximum))return 3;
        float best=0;double best_error=error(x,0);
        for(int sign=-1;sign<=1;sign+=2)for(unsigned step=1;step<=32;++step){
            const float d=(float)(_Float16)(sign*maximum*(float)step/32.0f);
            if(!d)continue;const double e=error(x,d);if(e<best_error){best_error=e;best=d;}
        }
        for(unsigned iteration=0;best&&iteration<4;++iteration){
            double numerator=0,denominator=0;
            for(unsigned j=0;j<64;++j){const int q=level(x[j],best);numerator+=(double)x[j]*q;denominator+=q*q;}
            if(!denominator)break;
            // The qualified PS5 ABI supplies F32-to-F16 conversion. Keep the
            // intermediate F32 rounding explicit on both host and console.
            const float d=(float)(_Float16)(float)(numerator/denominator);if(!d||!isfinite(d))break;
            const double e=error(x,d);if(e>=best_error)break;best_error=e;best=d;
        }
        const _Float16 half=(_Float16)best;memcpy(output+b*18,&half,2);memset(output+b*18+2,0,16);
        for(unsigned j=0;j<64;++j){const unsigned q=best?(unsigned)(level(x[j],best)+1):1;
            output[b*18+2+j/4]|=(uint8_t)(q<<(2*(j%4)));}
    }
    return 0;
}

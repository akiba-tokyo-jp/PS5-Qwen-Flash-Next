/* SPDX-License-Identifier: MIT
 * Deterministic BF16 -> Q8_0 weight conversion; no model evaluation.
 * Match the pinned quantize_row_q8_0_ref scaling and roundf rules.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <immintrin.h>
__attribute__((target("f16c")))
int qwen_resident_bf16_to_q8(const uint16_t*input,uint8_t*output,size_t values){
    if(!input||!output||!values||values%32)return 0;
    for(size_t block=0;block<values/32;++block){float x[32],maximum=0;
        for(unsigned j=0;j<32;++j){uint32_t bits=(uint32_t)input[block*32+j]<<16;memcpy(&x[j],&bits,4);
            const float magnitude=x[j]<0?-x[j]:x[j];if(magnitude>maximum)maximum=magnitude;}
        const float scale=maximum/127.0f,inverse=scale?1.0f/scale:0.0f;
        const uint16_t half=(uint16_t)_cvtss_sh(scale,_MM_FROUND_TO_NEAREST_INT|_MM_FROUND_NO_EXC);
        memcpy(output+block*34,&half,2);
        for(unsigned j=0;j<32;++j){const float v=x[j]*inverse;
            /* The double addition preserves every F32 half-way neighbor before
             * integer truncation; a rounded F32 v+0.5 can misround neighbors. */
            const int q=(int)((double)v+(v<0?-0.5:0.5));
            if(q< -127||q>127)return 0;output[block*34+2+j]=(uint8_t)(int8_t)q;
        }
    }
    return 1;
}

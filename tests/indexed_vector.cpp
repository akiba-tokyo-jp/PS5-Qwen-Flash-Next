// SPDX-License-Identifier: MIT
#include "indexed_vector.h"
#include <cstddef>
#include <initializer_list>
#include <stdexcept>

static ggml_tensor tensor(ggml_type type,std::int64_t a,std::int64_t b,std::int64_t c,std::size_t bytes) {
    ggml_tensor t{};t.type=type;t.ne[0]=a;t.ne[1]=b;t.ne[2]=c;t.ne[3]=1;
    t.nb[0]=bytes;t.nb[1]=bytes*a;t.nb[2]=bytes*a*b;t.nb[3]=bytes*a*b*c;return t;
}
static void require(bool condition) {if(!condition)throw std::runtime_error("Indexed-vector layout control failed");}
int main() {
    for(const bool down:{false,true})for(const int vectors:{1,10})for(const int experts:{10,53}) {
        const int k=down?640:2560,n=down?2560:640;
        auto a=tensor(GGML_TYPE_BF16,k,n,experts,2),b=tensor(GGML_TYPE_F32,k,vectors,1,4);
        auto ids=tensor(GGML_TYPE_I32,10,1,1,4),out=tensor(GGML_TYPE_F32,n,10,1,4);
        out.src[0]=&a;out.src[1]=&b;out.src[2]=&ids;
        require(qwen_app::bf16_indexed_vector_layout(&out));
        const auto original_a=a,original_b=b,original_ids=ids,original_out=out;
        a.type=GGML_TYPE_F16;require(!qwen_app::bf16_indexed_vector_layout(&out));a=original_a;
        a.ne[2]=54;require(!qwen_app::bf16_indexed_vector_layout(&out));a=original_a;
        a.ne[2]=9;require(!qwen_app::bf16_indexed_vector_layout(&out));a=original_a;
        a.nb[2]+=64;require(!qwen_app::bf16_indexed_vector_layout(&out));a=original_a;
        a.ne[0]=1280;require(!qwen_app::bf16_indexed_vector_layout(&out));a=original_a;
        b.type=GGML_TYPE_F16;require(!qwen_app::bf16_indexed_vector_layout(&out));b=original_b;
        b.ne[1]=2;require(!qwen_app::bf16_indexed_vector_layout(&out));b=original_b;
        b.ne[2]=4;require(!qwen_app::bf16_indexed_vector_layout(&out));b=original_b;
        b.nb[1]+=4;require(!qwen_app::bf16_indexed_vector_layout(&out));b=original_b;
        ids.ne[1]=4;require(!qwen_app::bf16_indexed_vector_layout(&out));ids=original_ids;
        ids.nb[0]=8;require(!qwen_app::bf16_indexed_vector_layout(&out));ids=original_ids;
        out.nb[1]+=4;require(!qwen_app::bf16_indexed_vector_layout(&out));out=original_out;
        out.ne[1]=9;require(!qwen_app::bf16_indexed_vector_layout(&out));out=original_out;
        out.src[2]=nullptr;require(!qwen_app::bf16_indexed_vector_layout(&out));
    }
    require(!qwen_app::bf16_indexed_vector_layout(nullptr));
}

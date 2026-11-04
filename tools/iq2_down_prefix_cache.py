#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Omit only unreachable carrier padding from existing Down cache uploads."""
from build_speculative_batch_probe import once

PLANE_BYTES = 460800
PREFIX_BYTES = 64 + 422400 + 2560

COUNTER = '''#include <atomic>
#include <cstdint>
namespace {std::atomic<std::uint64_t> iq2_down_omitted_padding_bytes{0};}
extern "C" std::uint64_t qwen_iq2_down_omitted_carrier_padding_bytes(){
    return iq2_down_omitted_padding_bytes.load(std::memory_order_relaxed);
}
'''

BRANCH = '''                // All custom Down loads end at byte425024 of the460800-byte plane.
                // Keep the original source/slot stride and omit only unused tail padding.
                if(n==1&&w->type==GGML_TYPE_Q2_0&&expert_size==460800&&[](const char*name){
                    if(std::strncmp(name,"blk.",4))return false;
                    const char*p=name+4;unsigned layer=0,digits=0;
                    while(*p>='0'&&*p<='9'&&digits<2){layer=10*layer+unsigned(*p-'0');++p;++digits;}
                    return digits&&layer<48&&!std::strcmp(p,".ffn_down_exps.weight");
                }(w->name)){
                    constexpr size_t prefix_bytes=425024;
                    const unsigned count=i+1<fills.size()&&(!(six_refill||bundle_refill)||!delivered[i+1])?2:1;
                    const auto*first=static_cast<const uint8_t*>(w->data)+fills[i].expert*expert_size;
                    if(count==2&&qwen_app_model_source_pair_enabled(prefix_bytes)){
                        struct PrefixUpload{ggml_tensor*bank;size_t stride;int32_t slots[2];};
                        PrefixUpload job{bank,expert_size,{fills[i].slot,fills[i+1].slot}};
                        const auto*second=static_cast<const uint8_t*>(w->data)+fills[i+1].expert*expert_size;
                        ggml_backend_synchronize(backend);
                        qwen_app_model_source_upload_pair(first,second,prefix_bytes,&job,
                            [](void*opaque,unsigned index,const void*window){
                                const auto&u=*static_cast<const PrefixUpload*>(opaque);
                                if(index>=2||u.slots[index]<0)throw std::runtime_error("Down prefix slot is unowned");
                                const size_t offset=size_t(u.slots[index])*u.stride;
                                if(offset>ggml_nbytes(u.bank)||425024>ggml_nbytes(u.bank)-offset)
                                    throw std::runtime_error("Down prefix upload exceeds its bank");
                                ggml_backend_tensor_set(u.bank,window,offset,425024);
                            });
                        iq2_down_omitted_padding_bytes.fetch_add(2*(460800-prefix_bytes),std::memory_order_relaxed);
                        bytes+=2*prefix_bytes;i+=2;continue;
                    }
                    ggml_backend_synchronize(backend);
                    const size_t destination=size_t(fills[i].slot)*expert_size;
                    if(fills[i].slot<0||destination>ggml_nbytes(bank)||prefix_bytes>ggml_nbytes(bank)-destination)
                        throw std::runtime_error("Down prefix upload exceeds its bank");
                    for(size_t done=0;done<prefix_bytes;){
                        size_t copied=0;
                        const void*window=qwen_app_model_source_chunk(first+done,prefix_bytes-done,&copied);
                        if(!copied||copied>prefix_bytes-done)throw std::runtime_error("Down prefix did not advance");
                        ggml_backend_tensor_set(bank,window,destination+done,copied);
                        qwen_app_model_source_chunk_completed();done+=copied;
                    }
                    iq2_down_omitted_padding_bytes.fetch_add(460800-prefix_bytes,std::memory_order_relaxed);
                    bytes+=prefix_bytes;++i;continue;
                }
'''


def transform(source):
    marker = '                // Queue only the next known miss while the producer consumes\n'
    return COUNTER + once(source, marker, BRANCH + marker)


def accounting_entry(source):
    """Keep actual transfer counters and independently certify omitted padding."""
    source = once(source, 'struct CompletedRouteEvidence {',
        'extern "C" std::uint64_t qwen_iq2_down_omitted_carrier_padding_bytes();\n'
        'struct CompletedRouteEvidence {\n    std::uint64_t omitted_carrier_padding_bytes=0;')
    source = once(source, 'std::uint64_t before_predictive) {',
        'std::uint64_t before_predictive,std::uint64_t before_omitted_padding) {')
    source = once(source, '    if(hits+misses!=result.unique||uploaded!=misses*1536000ull+result.predictive_bytes)',
        '''    const auto omitted_after=qwen_iq2_down_omitted_carrier_padding_bytes();
    if(omitted_after<before_omitted_padding)throw qwen_app::ExpertRouteCaptureError("Down padding counter moved backwards");
    result.omitted_carrier_padding_bytes=omitted_after-before_omitted_padding;
    if(result.omitted_carrier_padding_bytes%35776||result.omitted_carrier_padding_bytes>misses*35776ull)
        throw qwen_app::ExpertRouteCaptureError("Down padding counter exceeds complete demand fills");
    if(hits+misses!=result.unique||uploaded+result.omitted_carrier_padding_bytes!=misses*1536000ull+result.predictive_bytes)''')
    source = once(source, '            const auto predicted=predictive_cache_bytes();',
        '            const auto predicted=predictive_cache_bytes();\n'
        '            const auto omitted_padding_before=qwen_iq2_down_omitted_carrier_padding_bytes();')
    source = once(source,
        'routes[ordinal]=completed_route_evidence(*engine,perf.at("process_calls").get<std::uint64_t>(),*cache,predicted);',
        'routes[ordinal]=completed_route_evidence(*engine,perf.at("process_calls").get<std::uint64_t>(),*cache,predicted,omitted_padding_before);')
    return once(source, '{"uploaded_bytes",result.uploaded},',
        '{"uploaded_bytes",result.uploaded},{"omitted_carrier_padding_bytes",result.omitted_carrier_padding_bytes},'
        '{"logical_admitted_weight_bytes",result.uploaded+result.omitted_carrier_padding_bytes},')

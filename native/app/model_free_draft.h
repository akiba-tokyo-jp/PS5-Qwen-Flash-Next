// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
enum class DraftOrigin {none,generated,prompt};
enum class DraftEvidence {single_latest,consistent_pair};
struct ModelFreeDraft {
    bool found=false;
    std::int32_t token=-1;
    DraftOrigin origin=DraftOrigin::none;
    std::size_t matched_tokens=0,source_offset=0,historical_matches=0;
};
// Pure token metadata prototype, not linked into inference. Only committed past
// tokens enter this API. Width-two verification would process one pending token
// plus this single draft; no model probabilities or future targets are inputs.
inline ModelFreeDraft propose_model_free_token(const std::int32_t *prompt,std::size_t prompt_count,
        const std::int32_t *generated,std::size_t generated_count,std::size_t vocabulary,
        DraftEvidence evidence=DraftEvidence::single_latest) {
    if(!vocabulary||vocabulary>262144||prompt_count>64||generated_count>256||prompt_count>256-generated_count||
       (prompt_count&&!prompt)||(generated_count&&!generated)||
       (evidence!=DraftEvidence::single_latest&&evidence!=DraftEvidence::consistent_pair))
        throw std::invalid_argument("Bounded original prompt and committed history are required");
    for(std::size_t i=0;i<prompt_count;++i)
        if(prompt[i]<0||std::size_t(prompt[i])>=vocabulary)throw std::invalid_argument("Prompt token exceeds original vocabulary");
    for(std::size_t i=0;i<generated_count;++i)
        if(generated[i]<0||std::size_t(generated[i])>=vocabulary)throw std::invalid_argument("Committed token exceeds original vocabulary");
    if(!generated_count)return {};
    const auto search=[&](const std::int32_t *source,std::size_t count,std::size_t minimum,DraftOrigin origin) {
        const auto maximum=std::min<std::size_t>({4,generated_count,count?count-1:0});
        if(maximum<minimum)return ModelFreeDraft{};
        for(std::size_t n=maximum;;--n) {
            const auto *suffix=generated+generated_count-n;
            ModelFreeDraft candidate;bool ambiguous=false;
            for(std::size_t end=count-n;end;--end) {
                const auto at=end-1;
                if(!std::equal(suffix,suffix+n,source+at))continue;
                if(evidence==DraftEvidence::single_latest)
                    return ModelFreeDraft{true,source[at+n],origin,n,at,1};
                if(!candidate.found)candidate={true,source[at+n],origin,n,at,0};
                else if(candidate.token!=source[at+n])ambiguous=true;
                ++candidate.historical_matches;
            }
            // This is a causal recurrence screen, not a calibrated probability
            // or a substitute for target verification and rollback.
            if(candidate.found&&!ambiguous&&candidate.historical_matches>=2)return candidate;
            if(n==minimum)break;
        }
        return ModelFreeDraft{};
    };
    // Generated-history recurrence is more diagnostic than a prompt unigram.
    // Prompt lookup requires at least two matching already-emitted tokens.
    const auto own=search(generated,generated_count,1,DraftOrigin::generated);
    return own.found?own:search(prompt,prompt_count,2,DraftOrigin::prompt);
}
}

// SPDX-License-Identifier: MIT
// A finite refinement: narrow outputs only for the actual cold request.
// The unchanged selector continues to restore caller flags and ends prefill
// at the first sampling call; retained/prefix requests keep all output rows.
namespace {bool cold_prefill_selected=false;unsigned cold_next_request=0;bool cold_candidate=false;}
#define QWEN_PERF_PREFILL_POST_TRUNK cold_prefill_selected
#include "prefill_process_candidate.cpp"
extern "C" void qwen_P1_select_request(unsigned ordinal,bool candidate){
    if(ordinal>=3||ordinal!=cold_next_request||prefill_context||
       (ordinal&&candidate!=cold_candidate))
        throw std::runtime_error("P1 requires three ordered completed ordinary request scopes");
    if(!ordinal)cold_candidate=candidate;
    cold_prefill_selected=candidate&&!ordinal;++cold_next_request;
    char line[128];std::snprintf(line,sizeof(line),"P1_before_request_phase ordinal=%u cold_output_crop=%u",ordinal,unsigned(cold_prefill_selected));
    qwen_native_stage(line);
}

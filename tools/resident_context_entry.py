#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep the original context while resetting original memory and Expert metadata."""


def generate(text):
    main=text.index('int main(int argc, char ** argv)')
    helper='''static const llama_context *resident_reused_context=nullptr;
struct ResidentReuseVM {qwen_kernel_memory_sample memory;const char *phase;bool valid;};
static ResidentReuseVM resident_reuse_VM[96]{};static unsigned resident_reuse_VM_count=0;
static int resident_reuse_scalar(void *,const char *name,std::uint32_t *value){
    struct {std::uint64_t a;std::uint32_t value;std::uint64_t b;}s{0x194dba62e5307fc8ull,0,0x194dba62e5307fc8ull};
    std::size_t size=4;if(sysctlbyname(name,&s.value,&size,nullptr,0)||size!=4||s.a!=0x194dba62e5307fc8ull||s.a!=s.b)return 0;
    *value=s.value;return 1;
}
static void resident_reuse_sample(const char *phase){
    if(resident_reuse_VM_count>=96)throw std::runtime_error("Bounded context reuse observations exhausted");
    auto &row=resident_reuse_VM[resident_reuse_VM_count];row.phase=phase;
    const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(qwen_app::ProfileClock::now().time_since_epoch()).count();
    row.valid=qwen_kernel_memory_observe(nullptr,resident_reuse_scalar,ns,resident_reuse_VM_count,&row.memory);
    ++resident_reuse_VM_count;if(!row.valid)throw std::runtime_error("Context reuse VM observation unavailable");
}
static Json resident_reuse_VM_report(){
    Json rows=Json::array();for(unsigned i=0;i<resident_reuse_VM_count;++i){const auto &r=resident_reuse_VM[i];const auto &s=r.memory;
        rows.push_back({{"ordinal",i},{"phase",r.phase},{"valid",r.valid},{"ns",s.monotonic_ns},{"free",s.free_last},
            {"active",s.active},{"inactive",s.inactive},{"wired",s.wired},{"cache",s.cache},{"total",s.total}});}
    return {{"same_original_context",true},{"samples",rows},{"GPU_calls_added",0},{"global_not_exclusive_attribution",true},
        {"registered_cache_owners",qwen_app_resident_cache_reuse_live_owners()}};
}
static void resident_reset_empty_context(llama_context *context,llama_model *model,const std::string &prefix){
    if(!context||llama_get_model(context)!=model||llama_n_ctx(context)!=256||llama_n_batch(context)!=4||
       !llama_get_memory(context)||llama_memory_seq_pos_max(llama_get_memory(context),0)>=0||
       (resident_reused_context&&resident_reused_context!=context))
        throw std::runtime_error("One original context after positive complete request memory reset required");
    resident_reused_context=context;resident_reuse_sample("before_cache_metadata_reset");
    const auto before=qwen_app::native_model_device_stats();qwen_resident_cache_reset_stats reset{};
    qwen_app_reset_resident_expert_cache(&reset);const auto after=qwen_app::native_model_device_stats();
    if(before.live!=after.live||before.allocations!=after.allocations||reset.groups!=1||reset.maps!=48||
       reset.slots!=qwen_app::selected_padded_cache_geometry().active_slots||reset.occupied_after||
       !reset.original_banks_retained||!reset.cumulative_counters_preserved)
        throw std::runtime_error("Cache reset changed device owners, geometry or cumulative counters");
    resident_reuse_sample("after_cache_metadata_reset");
    write_fresh_report(prefix+".resident.cache-reuse-"+std::to_string(reset.reset_ordinal),{{"reset_ordinal",reset.reset_ordinal},
        {"occupied_before",reset.occupied_before},{"occupied_after",reset.occupied_after},{"maps",reset.maps},{"slots",reset.slots},
        {"original_banks_retained",true},{"device_allocation_count_unchanged",true},{"device_live_bytes",after.live},
        {"cumulative_counters_preserved",true},{"original_model_memory_empty",true},{"same_original_context",true},{"predictive",reset.predictive}});
}
'''
    text='#include "resident_cache_reset.h"\n#include "kernel_memory_trace.h"\n'+text[:main]+helper+text[main:]
    # Configure only the explicit new test scope, before its original context.
    candidates=['qwen_app::require_resident_combined_policy(policy);','qwen_app::require_resident_additional_policy(policy,"cache");','qwen_app::require_resident_refill_policy(policy);']
    matches=[needle for needle in candidates if text.count(needle)==1];assert len(matches)==1
    activation='''
        const Json reuse_scope={{"schema","ps5-qwen-resident-context-reuse-v1"},{"enabled",true},
            {"original_contexts",1},{"empty_expert_cache_before_independent_request",true},{"original_memory_reset_required",true},
            {"preserve_cumulative_counters",true},{"retain_all_original_bank_allocations",true},{"GPU_or_ordinary_floor_changes",0},
            {"all_original_precision_and_complete_F32_comparison_required",true},{"automatic_retries",0}};
        if(policy.at("native_resident_context_reuse")!=reuse_scope)throw std::runtime_error("Exact retained-context scope required");
        qwen_app_configure_resident_cache_reuse(true);
'''
    text=text.replace(matches[0],matches[0]+activation)
    shapes=['qwen_native_driver_begin();engine.reset();llama_free(context);context=nullptr;\n            qwen_native_driver_complete();',
            'qwen_native_driver_begin();engine.reset();llama_free(context);context=nullptr;qwen_native_driver_complete();']
    removed=0
    for old in shapes:
        count=text.count(old);removed+=count
        text=text.replace(old,'resident_reuse_sample("before_engine_release");\n            qwen_native_driver_begin();engine.reset();qwen_native_driver_complete();resident_reuse_sample("after_engine_release");')
    old='context=llama_init_from_model(model,qwen_app::streaming_context_params(256,cache_bytes,4));'
    assert removed in (1,2) and text.count(old)==removed
    text=text.replace(old,'resident_reset_empty_context(context,model,startup.admission_report);')
    for stage in ('resident_comparison_arm_completed_positive_request_reset','resident_additional_arm_completed_positive_request_reset'):
        needle='qwen_native_stage("'+stage+'");'
        text=text.replace(needle,'resident_reuse_sample("after_completed_request");'+needle)
    # Capture complete F32 continuations in each combined arm as well.
    if 'retained_prefix_routes'in text:
        old='if(ordinal==0||rejection)engine->set_logits_observer(';assert text.count(old)==1
        text=text.replace(old,'engine->set_logits_observer(')
        text=text.replace('{"full_F32_logit_rows_compared",rejection?logits_seen:0}','{"full_F32_logit_rows_compared",ordinal?logits_seen:0}')
        old='if(!result.request_reset_completed||logit_geometry_error||logit_value_error)';assert text.count(old)==1
        text=text.replace(old,'if(!result.request_reset_completed||logit_geometry_error||logit_value_error||(ordinal&&logits_seen!=reference_rows))')
    terminal='        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);';index=text.rfind(terminal);assert index>text.index('int main(')
    text=text[:index]+'''        if(qwen_app_resident_cache_reuse_live_owners())throw std::runtime_error("Original cache reset owner was not retired");
        write_fresh_report(startup.admission_report+".resident.context-reuse-VM",resident_reuse_VM_report());
'''+text[index:]
    old='{"last_model_load_error",qwen_app::resident_last_model_error()},';assert text.count(old)==1
    text=text.replace(old,old+'{"context_reuse_VM",resident_reuse_VM_report()},')
    assert text.count('llama_init_from_model(model,qwen_app::streaming_context_params(256,cache_bytes,4));')==0
    return text

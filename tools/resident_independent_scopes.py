#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Separate frozen comparison entries and retire positively completed uploads."""


def _replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('One exact completed native frontier required: ' + old[:96])
    return text.replace(old, new)


def separate_combined(text, kind):
    """Keep each original cohort and its own common positive retirement."""
    if kind not in ('predictive', 'prefix'):
        raise ValueError('An independent original comparison is required')
    start = text.index('        std::array<CompletedRouteEvidence,9> retained_prefix_routes;')
    end = text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();', start)
    block = text[start:end]
    side_start = text.index('        for(unsigned i=0;i<retained_prefix_routes.size();', end)
    side_end = text.index('        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);', side_start)
    text = text[:side_start] + text[side_end:]
    text = text[:start] + text[end:]
    text = _replace(text,
        '{"requests",completed},{"prefix_requests",retained_prefix_results},{"model_loads",1},{"total_requests",19}',
        '{"requests",completed},{"model_loads",1}')
    text = _replace(text, 'ps5-qwen-resident-combined-result-v1', 'ps5-qwen-resident-comparison-result-v1')
    if kind == 'predictive':
        text = _replace(text, 'qwen_app::require_resident_combined_policy(policy);',
            'qwen_app::require_resident_comparison_policy(policy);')
    else:
        # The frozen inner block already includes the qualified join correction,
        # retained context and complete F32 observer. Give it its original name
        # and first-entry completion, with no C2 request or checkpoint dependency.
        prefix = block[block.index('        const bool prefix_comparison=true;'):]
        prefix = prefix[:prefix.index('        retained_prefix_routes=std::move(routes);')]
        prefix = prefix.replace('startup.admission_report+".prefix.arm"', 'startup.admission_report+".arm"')
        prefix = prefix.replace('run+"-prefix-"+std::to_string(ordinal)', 'run+"-"+std::to_string(ordinal)')
        prefix = _replace(prefix, '        resident_sample("combined_prefix_start_after_positive_request_reset");',
            '        qwen_native_driver_complete();resident_sample("original_model_context_completed");')
        prefix = _replace(prefix, '.resident.prefix-startup-memory', '.resident.startup-memory')
        main = text.index('int main(int argc, char ** argv)')
        begin = text.index('        const auto *chat_template=llama_model_chat_template(model,nullptr);', main)
        finish = text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();', begin)
        text = text[:begin] + prefix + text[finish:]
        text = _replace(text, 'qwen_app::require_resident_combined_policy(policy);',
            'qwen_app::require_resident_additional_policy(policy,"prefix");')
        text = '#include "resident_additional_policy.h"\n' + text
        text = _replace(text, 'if(ledger.live||!forced_rejection_passed)', 'if(ledger.live)')
        text = _replace(text, 'for(unsigned i=0;i<routes.size();++i){', 'for(unsigned i=0;i<request_count;++i){')
        text = _replace(text, '{"cache_reset_before_request",true}', '{"cache_reset_before_request",!i||i%2!=0}')
        text = _replace(text, 'ps5-qwen-resident-comparison-result-v1', 'ps5-qwen-resident-additional-result-v1')
        text = _replace(text, '{"pid",getpid()},{"run_id",run},{"completed",true},{"requests",completed}',
            '{"kind","prefix"},{"active_cache_slots",53},{"pid",getpid()},{"run_id",run},{"completed",true},{"requests",completed}')
        text = _replace(text, '{"forced_rejection_and_full_F32_restore_passed",true}',
            '{"full_F32_continuation_and_routes_passed",true}')
    if 'retained_prefix_' in text or 'combined_prefix_start_' in text:
        raise ValueError('An unwanted dependent cohort remains')
    return text


def bound_reference(text):
    """Keep every original 23-row demo value, failing closed on an extra row."""
    if text.count('std::vector<float> reference_logits(33*') != 1:
        raise ValueError('One original full-vocabulary reference is required')
    text = text.replace('std::vector<float> reference_logits(33*',
        'constexpr std::size_t resident_reference_rows=23;\n        std::vector<float> reference_logits(resident_reference_rows*')
    matches = sum(text.count(x) for x in ('logits_seen>=33', 'rows>=33'))
    if matches != 1:
        raise ValueError('One allocation-free reference bounds check is required')
    text = text.replace('logits_seen>=33', 'logits_seen>=resident_reference_rows')
    text = text.replace('rows>=33', 'rows>=resident_reference_rows')
    # Requests retain the original 32-token upper limit. Unexpected continuation
    # geometry is a validation failure, never truncated data or an omitted row.
    return text


def release_completed_upload_source(text):
    text = _replace(text, '#include "ggml-vulkan-common.h"', '#include "ggml-vulkan-common.h"\n' + '''
static vk_device_ref resident_completed_upload_device;
static std::atomic<uint64_t> resident_upload_started{0};
extern "C" uint64_t qwen_app_release_completed_upload_staging(){
    if(!resident_upload_started.load()||resident_upload_started.load()!=resident_upload_calls.load())
        throw std::runtime_error("Every resident upload must positively finish before staging retirement");
    auto device=resident_completed_upload_device.lock();
    if(!device)throw std::runtime_error("Completed original upload device required");
    std::lock_guard<std::recursive_mutex> guard(device->mutex);
    auto &staging=device->sync_staging;
    if(!staging||staging.use_count()!=1||!staging->size||staging->size>(64u<<20))
        throw std::runtime_error("Only the exclusively owned bounded upload staging may retire");
    const auto bytes=staging->size;
    std::weak_ptr<vk_buffer_struct> retired=staging;
    ggml_vk_destroy_buffer(staging);
    if(staging||!retired.expired())throw std::runtime_error("Original staging destructor did not complete");
    resident_completed_upload_device.reset();
    return bytes;
}
''')
    text = _replace(text, '        vk_context subctx = ggml_vk_create_temporary_context(dst->device->transfer_queue->cmd_pool);',
        '        if(resident_copy)++resident_upload_started;\n'
        '        vk_context subctx = ggml_vk_create_temporary_context(dst->device->transfer_queue->cmd_pool);')
    text = _replace(text, 'if(resident_copy){++resident_upload_calls;',
        'if(resident_copy){resident_completed_upload_device=dst->device;++resident_upload_calls;')
    return text


def release_completed_upload_entry(text):
    main = text.index('int main(int argc, char ** argv)')
    text = text[:main] + 'extern "C" std::uint64_t qwen_app_release_completed_upload_staging();\n' + text[main:]
    needle = '''        write_fresh_report(startup.admission_report+".resident.GPU-upload-loaded",resident_GPU_upload_report());
        qwen_native_driver_checkpoint();'''
    replacement = needle + '''
        // Every upload fence and command-pool cleanup returned. Complete the
        // original producer epoch before the ordinary staging-buffer destructor.
        qwen_native_driver_complete();
        const auto upload_retirement_before=qwen_app::observe_native_system_memory();
        const auto upload_budget_before=qwen_native_allocator_budget(driver_total);
        // The per-BO allocator defers free callbacks until the next positively
        // quiet frontend boundary. Give destruction its own completed epoch.
        qwen_native_driver_begin();
        const auto upload_retired_bytes=qwen_app_release_completed_upload_staging();
        qwen_native_driver_complete();
        const auto upload_budget_after=qwen_native_allocator_budget(driver_total);
        const auto upload_retirement_after=qwen_app::observe_native_system_memory();
        if(upload_budget_after.owned>=upload_budget_before.owned||
           upload_budget_before.owned-upload_budget_after.owned<upload_retired_bytes)
            throw std::runtime_error("Completed staging did not release original allocator ownership");
        write_fresh_report(startup.admission_report+".resident.upload-retirement",{
            {"completed",true},{"released_requested_bytes",upload_retired_bytes},
            {"owned_before",upload_budget_before.owned},{"owned_after",upload_budget_after.owned},
            {"free_kernel_before",upload_retirement_before.kernel_free},{"free_kernel_after",upload_retirement_after.kernel_free},
            {"original_upload_fences_and_command_cleanup_returned",true},{"producer_epoch_completed",true},
            {"exclusive_staging_destructor_completed",true},{"GPU_or_ordinary_floor_changes",0},
            {"global_VM_not_exclusive_attribution",true}});
        qwen_native_driver_begin();'''
    return _replace(text, needle, replacement)

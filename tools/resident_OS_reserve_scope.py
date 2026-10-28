#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Select an explicit post-context reserve experiment, preserving OS reserves."""
import json

SCOPE = dict(schema='ps5-qwen-post-context-OS-reserve-v1', enabled=True,
    activation_after_original_context_and_positive_completion=True,
    original_GPU_initialization_and_context_floors_unchanged=True,
    preserve_full_observed_OS_reserved_pages=True, measured_component_screen_pages=64,
    component_observations=dict(Direct_metadata=17, idle=2, context_interval=41, context_margin=2, selected_rounding=2),
    selected_extra_formula='max(observed_OS_reserved_pages,64)',
    current_boot_OS_reserved_pages=206, current_boot_kernel_minimum_pages=898,
    original_precision_and_full_F32_comparison_required=True,
    universal_peak_bound_established=False, original_wait_and_retirement_guards=True,
    automatic_retries=0)


def system_header(text):
    old = '21ull:std::max<std::uint64_t>(s.kernel_reserved,kernel_memory_margin/s.page_size)'
    if text.count(old) != 1:
        raise ValueError('Qualified original CPU/GPU selector required')
    return text.replace(old,
        '21ull:(qwen_app_resident_GPU_OS_reserve_active()?std::max<std::uint64_t>(s.kernel_reserved,64):'
        'std::max<std::uint64_t>(s.kernel_reserved,kernel_memory_margin/s.page_size))')


def implementation(text):
    marker = '\nnamespace qwen_app {'
    if text.count(marker) != 1:
        raise ValueError('One original CPU metadata phase implementation required')
    extra = '''
static std::atomic<bool> resident_GPU_OS_reserve_selected{false};
extern "C" bool qwen_app_resident_GPU_OS_reserve_active(){
    return resident_CPU_metadata_phase.load()==2&&resident_GPU_OS_reserve_selected.load();
}
extern "C" void qwen_app_activate_resident_GPU_OS_reserve(){
    bool expected=false;
    if(resident_CPU_metadata_phase.load()!=2||!resident_GPU_OS_reserve_selected.compare_exchange_strong(expected,true))
        throw std::runtime_error("The post-context OS reserve scope is once-only after the original CPU/GPU boundary");
}
'''
    return text.replace(marker, extra + marker)


def source_header(text):
    old = 'std::max<std::uint64_t>(m.kernel_reserved,256)'
    if text.count(old) != 1:
        raise ValueError('One actual new-source-allocation VM selector required')
    return text.replace(old,
        '(qwen_app_resident_GPU_OS_reserve_active()?std::max<std::uint64_t>(m.kernel_reserved,64):'
        'std::max<std::uint64_t>(m.kernel_reserved,256))')


def entry(text):
    main = text.index('int main(int argc, char ** argv)')
    needles = ['qwen_app::require_resident_additional_policy(policy,"prefix");',
        'qwen_app::require_resident_refill_policy(policy);', 'qwen_app::require_resident_comparison_policy(policy);']
    found = [needle for needle in needles if text[main:].count(needle) == 1]
    if len(found) != 1:
        raise ValueError('One independent native comparison contract required')
    validation = '\n        const Json OS_reserve_scope=' + json.dumps(SCOPE, separators=(',', ':')) + ';\n'
    # Use native Json parsing rather than a C++ initializer containing JSON booleans.
    validation = '\n        const Json OS_reserve_scope=Json::parse(R"qwen(' + json.dumps(SCOPE, separators=(',', ':')) + ')qwen");\n'
    validation += '        if(policy.at("native_resident_OS_reserve")!=OS_reserve_scope)throw std::runtime_error("Exact post-context OS reserve experiment required");\n'
    text = text.replace(found[0], found[0] + validation)
    marker = 'resident_sample("original_model_context_completed");'
    if text[main:].count(marker) != 1:
        raise ValueError('Original positively completed context activation frontier required')
    activation = '''
        if(!model||!context||llama_n_ctx(context)!=256||llama_n_batch(context)!=4||qwen_app_resident_CPU_metadata_scope_active())
            throw std::runtime_error("Original completed model/context required before reserve selection");
        const auto OS_scope_memory=qwen_app::observe_native_system_memory();
        if(OS_scope_memory.kernel_minimum!=898||OS_scope_memory.kernel_reserved!=206||
           OS_scope_memory.kernel_free<1104)throw qwen_app::KernelMemoryPressure();
        qwen_app_activate_resident_GPU_OS_reserve();
        write_fresh_report(startup.admission_report+".resident.OS-reserve",{
            {"activated_after_original_context",true},{"original_setup_GPU_floor",1154},{"context_allowance_pages",43},
            {"selected_kernel_minimum_pages",898},{"selected_full_OS_reserved_pages",206},{"selected_operational_floor_pages",1104},
            {"component_screen_pages",64},{"free_pages_at_activation",OS_scope_memory.kernel_free},
            {"universal_peak_bound_established",false},{"original_wait_and_retirement_guards",true}});
'''
    text = text.replace(marker, marker + activation)
    old = 'qwen_app_resident_CPU_metadata_scope_active()?21ull*16384:qwen_app::kernel_memory_margin'
    if text.count(old) != 3:
        raise ValueError('All original bounded memory reports must expose the selected policy')
    text = text.replace(old,
        'qwen_app_resident_CPU_metadata_scope_active()?21ull*16384:(qwen_app_resident_GPU_OS_reserve_active()?206ull*16384:qwen_app::kernel_memory_margin)')
    text = text.replace('{"memory_reserves_unchanged",true}',
        '{"memory_reserves_unchanged",!qwen_app_resident_GPU_OS_reserve_active()},'
        '{"OS_reserved_pages_preserved",true},{"post_context_OS_reserve_scope_active",qwen_app_resident_GPU_OS_reserve_active()}')
    if text.index('if(context_memory.kernel_free<context_floor+43)') > text.index('qwen_app_activate_resident_GPU_OS_reserve();', main):
        raise ValueError('Original setup admission must precede experimental activation')
    return text

// SPDX-License-Identifier: MIT
#pragma once
#include "padded_cache_geometry.h"
#include "padded_bank_layout.h"
#include "memory_admission.h"
#include "system_memory.h"
#include <nlohmann/json.hpp>
#include <cmath>
#include <set>
#include <tuple>
namespace qwen_app {
inline std::uint64_t large_cache_layout_requirement(const MemoryBudget &budget) {
    // The isolated fixture retains one expanded bank at a time, with no loaded
    // model or inference context. Preserve every independent working reserve.
    const auto bank=(PaddedCacheGeometry{128}.tensor_bytes()+(2ull<<20)-1)&~((2ull<<20)-1);
    auto required=bank;
    for(const auto bytes:{budget.workspace,budget.cpu_working,budget.staging,budget.platform_margin,budget.direct_reserve})
        required=checked_memory_sum(required,bytes);
    return required;
}
inline void admit_large_cache_layout_memory(const MemoryBudget &budget,const MemoryObservation &observed) {
    const auto alignment=observed.device_buffer_alignment;
    if(!alignment||alignment>65536||(alignment&(alignment-1))||
       observed.device_max_buffer<PaddedCacheGeometry{128}.tensor_bytes()||
       observed.driver_free<large_cache_layout_requirement(budget)||
       observed.direct_largest<large_cache_layout_requirement(budget)||
       observed.flexible_available<budget.flexible_reserve)
        throw std::runtime_error("The isolated 128-slot graph lacks observed bank/working/reserve capacity");
}
inline bool cache_evidence_hex(const std::string &text,std::size_t bytes) {
    return text.size()==bytes&&text.find_first_not_of("0123456789abcdef")==std::string::npos;
}
inline bool require_large_cache_scope(const nlohmann::json &policy,bool first,bool display,unsigned prefill) {
    using J=nlohmann::json;
    const auto &scope=policy.at("native_large_cache_scope");
    const bool layout=scope.at("stage")=="layout";
    J expected={{"schema","ps5-qwen-cache-128-experiment-v1"},{"stage",layout?"layout":"model"},
        {"active_slots",128},{"physical_planes",129},{"cache_request_bytes",PaddedCacheGeometry{128}.cache_bytes()},
        {"context_tokens",256},{"context_allowance_bytes",256u<<20},{"CPU_heap_cap_bytes",512u<<20},
        {"device_ledger_cap_bytes",1792u<<20},{"precision_unchanged",true},{"automatic_retries",0}};
    if(!layout)expected["layout_qualification"]=scope.at("layout_qualification");
    if(scope!=expected||!first||display||(!layout&&prefill!=4)||
       policy.contains("native_model_checkpoint_validation")||policy.contains("native_prefix_validation")||
       policy.contains("native_model_free_speculation"))
        throw std::runtime_error("The isolated exact 128-slot scope and unchanged heap/ledger caps are required");
    if(layout!=policy.contains("native_padded_bank_layout_probe")||
       layout==policy.contains("native_padded_expert_cache"))
        throw std::runtime_error("The 128-slot layout and model stages are mutually exclusive");
    if(!layout) {
        const auto &p=scope.at("layout_qualification");
        const auto run=p.at("run_id").get<std::string>();
        if(p.size()!=6||!cache_evidence_hex(run,32)||
           p.at("report_path")!="/app0/qwen-runtime/plan-"+run+".json.padded-layout"||
           !p.at("report_bytes").is_number_unsigned()||p.at("report_bytes")==0||p.at("report_bytes")>131072||
           !p.at("pid").is_number_integer()||p.at("pid")<=0||
           !cache_evidence_hex(p.at("report_sha256").get<std::string>(),64)||
           !cache_evidence_hex(p.at("SELF_sha256").get<std::string>(),64))
            throw std::runtime_error("Complete bounded native 128-slot qualification is required before model load");
    }
    return layout;
}
inline void require_large_cache_layout_phase_scope(const nlohmann::json &policy,bool first,bool display,unsigned prefill) {
    using J=nlohmann::json;
    if(!require_large_cache_scope(policy,first,display,prefill))
        throw std::runtime_error("The scoped slice path is exclusive to unloaded 128-slot layout qualification");
    const J phase={{"schema","ps5-qwen-cache-layout-phase-memory-v1"},{"enabled",true},
        {"single_original_slice_only",true},{"whole_model_metadata_files",0},{"virtual_source_probes",0},
        {"source_workers",0},{"model_loads",0},{"GPU_extra_operational_pages",512},
        {"historical_small_GPU_interval_decline_pages",32},{"GPU_cost_for_this_scope_qualified",false},
        {"regular_model_startup_target_unchanged",true},{"automatic_retries",0}};
    const J layout={{"schema","ps5-qwen-padded-bank-layout-v2"},{"enabled",true},
        {"model_member_index",7},{"source_offset",131072},{"envelope_bytes",3293184},
        {"source_SHA256","16fffd6b293d7d218adff19ba8a4f2d5176341b43b15fda3c9d63aa3f0677b1a"},
        {"maximum_Direct_reads",1},{"maximum_GPU_graphs",360},{"CPU_deadline_seconds",120},
        {"actual_residues",30},{"layouts",4},{"active_slots",128},{"physical_planes",129},
        {"model_loads",0},{"VideoOut_starts",0},{"automatic_retries",0}};
    if(policy.at("native_cache_layout_phase_memory")!=phase||policy.at("native_padded_bank_layout_probe")!=layout||
       !policy.contains("native_shader_storage")||policy.at("native_shader_storage").at("verify_all_original_assets_before_Vulkan")!=false||
       !policy.at("native_shader_storage").contains("prior_native_CPU"))
        throw std::runtime_error("Exact isolated geometry, current-boot shader proof and scoped memory policy are required");
    for(const auto key:{"native_bf16_indexed_vector","native_indexed_vector_fixture","native_owned_mapped_probe",
            "native_mapped_streaming_copy","native_shader_startup_memory_diagnostic","native_mini_shader_title",
            "native_mini_shader_bootstrap","native_model_checkpoint_validation","native_prefix_validation",
            "native_model_free_speculation"})
        if(policy.contains(key))throw std::runtime_error("The single-slice layout path cannot combine other experiments");
}
inline std::uint64_t large_cache_layout_kernel_requirement(const SystemMemoryObservation &s) {
    (void)qualified_system_headroom(s);
    // The old OS free target is not a per-operation allocation minimum. Retain
    // the original operational reserve and an explicit additional 8 MiB for
    // this one-bank experiment. The observed small-GPU decline was 32 pages;
    // 512 extra pages are a provisional policy, not a measured cost bound.
    return std::uint64_t(s.kernel_minimum)+std::max<std::uint64_t>(s.kernel_reserved,
        kernel_memory_margin/s.page_size)+512;
}
inline void require_large_cache_layout_report(const nlohmann::json &r,const nlohmann::json &proof) {
    if(r.at("schema")!="ps5-qwen-padded-bank-layout-result-v2"||r.at("pid")!=proof.at("pid")||
       r.at("run_id")!=proof.at("run_id")||r.at("candidate_SELF_sha256")!=proof.at("SELF_sha256")||
       r.at("driver_revision")!="872cc1264ad8ba5d6b888b092968fa5858a38c58"||r.at("profile")!="cumulative-idle"||
       r.at("native_archive_sha256")!="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"||
       r.at("active_slots")!=128||r.at("physical_planes")!=129||r.at("bank_stride")!=padded_bank_stride||
       r.at("source_SHA256")!="16fffd6b293d7d218adff19ba8a4f2d5176341b43b15fda3c9d63aa3f0677b1a"||
       r.at("eligible")!=true||r.at("all_started_IO_closed")!=true||r.at("positive_resource_retirement")!=true||
       r.at("source_workers_stopped")!=true||r.at("Direct_reads")!=1||r.at("GPU_graphs")!=360||
       r.at("device_ledger_live_bytes")!=0||r.at("device_ledger_allocations")<4||
       r.at("device_ledger_peak_bytes")<=0||r.at("device_ledger_peak_bytes")>(1792u<<20)||
       r.at("model_loaded")!=false||r.at("VideoOut_started")!=false||r.at("automatic_retries")!=0||
       r.at("maximum_absolute_error_limit")!=1e-6||r.at("reference_accumulation")!="F64")
        throw std::runtime_error("Native 128-slot geometry or positive completion proof differs");
    const auto alignment=r.at("descriptor_alignment").get<std::size_t>();
    if(!alignment||alignment>bank_read_alignment||(alignment&(alignment-1))||
       (r.at("memory_flags").get<std::uint64_t>()&7)!=7)
        throw std::runtime_error("Actual mapped native alignment and memory flags are required");
    using Key=std::tuple<unsigned,unsigned,unsigned,std::size_t>;
    std::set<Key> expected,actual;
    for(const auto residue:original_bank_residues) {
        if(residue%alignment)throw std::runtime_error("Original source residue violates descriptor alignment");
        for(unsigned k:{2560u,640u})for(unsigned v:{1u,10u})expected.emplace(k,k==2560?640:2560,v,residue);
    }
    if(r.at("cases").size()!=120)throw std::runtime_error("All original 128-slot layout cases are required");
    for(const auto &row:r.at("cases")) {
        const Key key{row.at("columns"),row.at("rows"),row.at("input_vectors"),row.at("residue")};
        const auto error=row.at("maximum_absolute_error").get<double>();
        if(!actual.insert(key).second||row.at("matrix_passed")!=true||row.at("vector_passed")!=true||
           row.at("non_dyadic_vector_passed")!=true||row.at("padding_intact")!=true||
           row.at("non_BF16_exact_F32_inputs")<=0||!std::isfinite(error)||error<0||error>1e-6)
            throw std::runtime_error("128-slot numerical, F32, padding or duplicate-case proof refused");
    }
    if(actual!=expected)throw std::runtime_error("128-slot native cases do not cover all original shapes and residues");
}
}

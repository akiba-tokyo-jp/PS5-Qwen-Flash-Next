// SPDX-License-Identifier: MIT
#include "large_cache_policy.h"
#include <functional>
#include <iostream>
using J=nlohmann::json;
using namespace qwen_app;
static void check(bool v){if(!v)throw std::runtime_error("Large-cache policy control failed");}
static unsigned failures=0;
static void refused(const std::function<void()> &action){
    bool caught=false;try{action();}catch(const std::exception&){caught=true;}
    check(caught);++failures;
}
int main(){try{
    MemoryBudget memory;memory.cpu_working=512ull<<20;memory.workspace=256ull<<20;
    check(large_cache_layout_requirement(memory)==(2070ull<<20));
    MemoryObservation observed{2070ull<<20,2070ull<<20,256ull<<20,512ull<<20,16384};
    admit_large_cache_layout_memory(memory,observed);
    for(unsigned field=0;field<5;++field){auto bad=observed;
        if(field==0)--bad.driver_free;if(field==1)--bad.direct_largest;if(field==2)--bad.flexible_available;
        if(field==3)bad.device_max_buffer=128u<<20;if(field==4)bad.device_buffer_alignment=3;
        refused([&]{admit_large_cache_layout_memory(memory,bad);});}
    J scope={{"schema","ps5-qwen-cache-128-experiment-v1"},{"stage","layout"},
        {"active_slots",128},{"physical_planes",129},{"cache_request_bytes",1274462208u},
        {"context_tokens",256},{"context_allowance_bytes",256u<<20},{"CPU_heap_cap_bytes",512u<<20},
        {"device_ledger_cap_bytes",1792u<<20},{"precision_unchanged",true},{"automatic_retries",0}};
    J policy={{"native_large_cache_scope",scope},{"native_padded_bank_layout_probe",J::object()}};
    check(require_large_cache_scope(policy,true,false,1));
    SystemMemoryObservation kernel{440401920,16384,138739,1666,898,2974,206};
    check(large_cache_layout_kernel_requirement(kernel)==1666);
    auto invalid_kernel=kernel;invalid_kernel.kernel_free=1153;
    refused([&]{large_cache_layout_kernel_requirement(invalid_kernel);});
    invalid_kernel=kernel;invalid_kernel.page_size=4096;
    refused([&]{large_cache_layout_kernel_requirement(invalid_kernel);});
    auto phase=policy;
    phase["native_cache_layout_phase_memory"]={{"schema","ps5-qwen-cache-layout-phase-memory-v1"},{"enabled",true},
        {"single_original_slice_only",true},{"whole_model_metadata_files",0},{"virtual_source_probes",0},
        {"source_workers",0},{"model_loads",0},{"GPU_extra_operational_pages",512},
        {"historical_small_GPU_interval_decline_pages",32},{"GPU_cost_for_this_scope_qualified",false},
        {"regular_model_startup_target_unchanged",true},{"automatic_retries",0}};
    phase["native_padded_bank_layout_probe"]={{"schema","ps5-qwen-padded-bank-layout-v2"},{"enabled",true},
        {"model_member_index",7},{"source_offset",131072},{"envelope_bytes",3293184},
        {"source_SHA256","16fffd6b293d7d218adff19ba8a4f2d5176341b43b15fda3c9d63aa3f0677b1a"},
        {"maximum_Direct_reads",1},{"maximum_GPU_graphs",360},{"CPU_deadline_seconds",120},
        {"actual_residues",30},{"layouts",4},{"active_slots",128},{"physical_planes",129},
        {"model_loads",0},{"VideoOut_starts",0},{"automatic_retries",0}};
    phase["native_shader_storage"]={{"verify_all_original_assets_before_Vulkan",false},{"prior_native_CPU",J::object()}};
    require_large_cache_layout_phase_scope(phase,true,false,1);
    for(const auto member:{"native_cache_layout_phase_memory","native_padded_bank_layout_probe"})
        for(auto it=phase[member].begin();it!=phase[member].end();++it){auto bad=phase;bad[member].erase(it.key());
            refused([&]{require_large_cache_layout_phase_scope(bad,true,false,1);});}
    for(const auto member:{"native_bf16_indexed_vector","native_indexed_vector_fixture","native_owned_mapped_probe",
            "native_mapped_streaming_copy","native_shader_startup_memory_diagnostic","native_mini_shader_title",
            "native_model_checkpoint_validation","native_prefix_validation","native_model_free_speculation"}){
        auto bad=phase;bad[member]=J::object();refused([&]{require_large_cache_layout_phase_scope(bad,true,false,1);});}
    auto model_phase=phase;model_phase["native_large_cache_scope"]["stage"]="model";
    refused([&]{require_large_cache_layout_phase_scope(model_phase,true,false,4);});
    refused([&]{require_large_cache_scope(policy,false,false,1);});
    refused([&]{require_large_cache_scope(policy,true,true,1);});
    for(auto it=scope.begin();it!=scope.end();++it){auto bad=policy;bad["native_large_cache_scope"].erase(it.key());
        refused([&]{require_large_cache_scope(bad,true,false,4);});}
    for(const auto key:{"native_model_checkpoint_validation","native_prefix_validation","native_padded_expert_cache","native_model_free_speculation"}) {
        auto bad=policy;bad[key]=J::object();refused([&]{require_large_cache_scope(bad,true,false,4);});
    }
    J proof={{"run_id",std::string(32,'a')},{"pid",123},{"report_bytes",65536u},
        {"report_path","/app0/qwen-runtime/plan-"+std::string(32,'a')+".json.padded-layout"},
        {"report_sha256",std::string(64,'b')},{"SELF_sha256",std::string(64,'c')}};
    policy.erase("native_padded_bank_layout_probe");policy["native_padded_expert_cache"]=J::object();
    policy["native_large_cache_scope"]["stage"]="model";
    refused([&]{require_large_cache_scope(policy,true,false,4);});
    policy["native_large_cache_scope"]["layout_qualification"]=proof;
    check(!require_large_cache_scope(policy,true,false,4));
    refused([&]{require_large_cache_scope(policy,true,false,2);});
    for(const auto key:{"report_path","report_bytes","pid","run_id","report_sha256","SELF_sha256"}){
        auto bad=policy;bad["native_large_cache_scope"]["layout_qualification"][key]=nullptr;
        refused([&]{require_large_cache_scope(bad,true,false,4);});
    }
    J report={{"schema","ps5-qwen-padded-bank-layout-result-v2"},{"pid",123},{"run_id",proof["run_id"]},
        {"candidate_SELF_sha256",proof["SELF_sha256"]},
        {"driver_revision","872cc1264ad8ba5d6b888b092968fa5858a38c58"},{"profile","cumulative-idle"},
        {"native_archive_sha256","b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"},
        {"active_slots",128},{"physical_planes",129},{"bank_stride",3293184},
        {"source_SHA256","16fffd6b293d7d218adff19ba8a4f2d5176341b43b15fda3c9d63aa3f0677b1a"},
        {"eligible",true},{"all_started_IO_closed",true},{"positive_resource_retirement",true},
        {"source_workers_stopped",true},{"Direct_reads",1},{"GPU_graphs",360},
        {"device_ledger_live_bytes",0},{"device_ledger_allocations",4},{"device_ledger_peak_bytes",512u<<20},
        {"model_loaded",false},{"VideoOut_started",false},{"automatic_retries",0},
        {"maximum_absolute_error_limit",1e-6},{"reference_accumulation","F64"},{"descriptor_alignment",4},
        {"memory_flags",7},{"cases",J::array()}};
    for(auto residue:original_bank_residues)for(unsigned k:{2560u,640u})for(unsigned v:{1u,10u})
        report["cases"].push_back({{"columns",k},{"rows",k==2560?640:2560},{"input_vectors",v},{"residue",residue},
            {"maximum_absolute_error",0.0},{"matrix_passed",true},{"vector_passed",true},
            {"non_dyadic_vector_passed",true},{"padding_intact",true},{"non_BF16_exact_F32_inputs",1}});
    require_large_cache_layout_report(report,proof);
    for(auto it=report.begin();it!=report.end();++it){auto bad=report;bad.erase(it.key());
        refused([&]{require_large_cache_layout_report(bad,proof);});}
    for(const auto key:{"columns","rows","input_vectors","residue","non_BF16_exact_F32_inputs"}){
        auto bad=report;bad["cases"][0][key]=0;refused([&]{require_large_cache_layout_report(bad,proof);});
    }
    for(const auto key:{"matrix_passed","vector_passed","non_dyadic_vector_passed","padding_intact"}){
        auto bad=report;bad["cases"][0][key]=false;refused([&]{require_large_cache_layout_report(bad,proof);});
    }
    auto bad=report;bad["cases"][1]=bad["cases"][0];refused([&]{require_large_cache_layout_report(bad,proof);});
    bad=report;bad["cases"][0]["maximum_absolute_error"]=0.001;refused([&]{require_large_cache_layout_report(bad,proof);});
    bad=report;bad["active_slots"]=53;refused([&]{require_large_cache_layout_report(bad,proof);});
    bad=report;bad["driver_revision"]=std::string(40,'0');refused([&]{require_large_cache_layout_report(bad,proof);});
    std::cout<<failures<<" scope, identity, lifecycle and numerical refusals passed; no PS5 operations\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}

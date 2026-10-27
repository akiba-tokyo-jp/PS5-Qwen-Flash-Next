// SPDX-License-Identifier: MIT
// CPU-only attribution with the original GGUF parser and verbatim inspector.
#include "mini_metadata_memory_policy.h"
#include "metadata_memory_probe.h"
#include "memory_admission.h"
#include "model_receipt.h"
#include "split_model_integrity.h"
#include "model_identity_namespace.h"
#include "direct_metadata.h"
#include "direct_integrity.h"
#include "runtime_admission.h"
#include "startup.h"
#include "profile_clock.h"
#include "gguf.h"
#include <ps5platform/heap.h>
#include <array>
#include <cstring>
#include <fstream>
#include <memory>
#include <unordered_set>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_native_stage(const char *);
void qwen_native_log_bytes(const char *,std::size_t);
[[noreturn]] void qwen_native_halt(const char *);
// The shared Direct metadata adapter can never borrow a model source in this
// binary. Its unused lease entry points fail closed and start no worker.
bool qwen_app_model_reads_enabled(){return false;}
}
namespace qwen_app {
SourceReadRequest begin_native_metadata_window(const std::string &){throw std::runtime_error("CPU metadata has no model source lease");}
void end_native_metadata_window(){throw std::runtime_error("CPU metadata cannot retire a model source lease");}
std::string sha256_metadata_bytes(const std::string &bytes) {
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,reinterpret_cast<const unsigned char*>(bytes.data()),bytes.size());
    unsigned char digest[32];sha256_final(&hash,digest);std::string text;
    for(auto v:digest){text+="0123456789abcdef"[v>>4];text+="0123456789abcdef"[v&15];}return text;
}
}
using Json=nlohmann::json;
using ModelFileIdentity=std::array<std::uint64_t,10>;
// Extracted verbatim from native_main.cpp with the complete source binding.
#include "mini_metadata_inspection.inc"
static void require_CPU_metadata_budget() {
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    if(heap.libc_fallbacks||heap.mapped_bytes>(64u<<20)||heap.peak_bytes>(64u<<20))
        throw std::runtime_error("CPU metadata exceeded its scoped Direct heap allowance");
    if(qwen_app::qualified_system_headroom(qwen_app::admit_native_system_memory())<qwen_app::model_read_system_reserve)
        throw std::runtime_error("CPU metadata cannot retain the original Flexible reserve");
}
static void write_report(const std::string &path,const Json &value) {
    const auto raw=value.dump(2)+"\n";
    if(raw.empty()||raw.size()>(1u<<20))throw std::runtime_error("CPU metadata report exceeds its fixed cap");
    const int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(fd<0||fchmod(fd,0644))throw std::runtime_error("A new owned CPU metadata report is required");
    const auto written=write(fd,raw.data(),raw.size());
    if(written!=static_cast<ssize_t>(raw.size())||fsync(fd)||close(fd))
        throw std::runtime_error("CPU metadata report did not positively close");
}
static Json metadata_records() {
    static const char *phases[]={"before_size","after_size","after_parser","after_tensor_scan","after_container_returned"};
    Json records=Json::array();for(std::size_t i=0;i<metadata_memory.size();++i){const auto &s=metadata_memory.at(i);
        records.push_back({{"file_index",i/5},{"phase",phases[i%5]},{"monotonic_ns",s.monotonic_ns},
            {"kernel_free_pages",s.memory.kernel_free},{"Flexible_available_bytes",s.memory.flexible_available},
            {"CPU_heap_mapped_bytes",s.heap_mapped},{"CPU_heap_peak_bytes",s.heap_peak},
            {"cumulative_Direct_reads",s.direct_reads},{"cumulative_Direct_bytes",s.direct_bytes}});}
    return records;
}
int main(int argc,char **argv) {
    qwen_native_stage("mini_metadata_CPU_main_entered_GPU_not_started");
    std::string output;
    try {
        const auto startup=qwen_app::read_startup(argc,argv);output=startup.admission_report;
        std::ifstream input(startup.development_policy);const auto policy=Json::parse(input);
        const auto run=qwen_app::require_mini_metadata_memory_policy(policy,startup.first_generation_validation,
            startup.native_display,output);
        const auto &binding=policy.at("native_first_generation_validation");
        qwen_app::enable_native_memory_backpressure();require_CPU_metadata_budget();
        write_report(output+".first.start",{{"schema","ps5-qwen-first-generation-start-v1"},{"pid",getpid()},
            {"run_id",run},{"candidate_SELF_sha256",binding.at("candidate_SELF_sha256")},
            {"model_receipt_sha256",binding.at("model_receipt_sha256")},{"model_loaded",false},{"Vulkan_initialized",false}});
        qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",binding.at("candidate_SELF_bytes"),binding.at("candidate_SELF_sha256"),30);
        qwen_app::verify_native_startup_file_direct(startup.model_receipt,binding.at("model_receipt_bytes"),binding.at("model_receipt_sha256"),30);
        qwen_native_stage("complete_SELF_and_receipt_direct_SHA256_passed GPU_not_started=1");
        qwen_app::admit_cpu_runtime(qwen_native_stage);
        const auto receipt=qwen_app::read_model_receipt(startup.model_receipt);
        const auto total=qwen_app::validate_model_receipt(receipt);
        auto gate=binding;gate["split_native_integrity"]=policy.at("native_metadata_source_seal");
        const auto split=qwen_app::split_model_integrity(gate,receipt,total);
        if(!split||receipt.at("files").size()!=76)throw std::runtime_error("All 76 original sealed containers are required");
        const auto directory=startup.model_receipt.substr(0,startup.model_receipt.find_last_of('/'));
        const auto observed_directory=model_directory_identity(directory);
        const auto observed_receipt=model_file_identity(startup.model_receipt,binding.at("model_receipt_bytes"));
        qwen_app::ModelIdentityNamespace names(split->prior.directory,observed_directory,split->prior.receipt,observed_receipt,
            startup.model_receipt=="/app0/qwen-runtime/model/model-receipt.json");
        auto verify_namespace=[&]{
            if(!names.matches(model_directory_identity(directory),split->prior.directory)||
               !names.matches(model_file_identity(startup.model_receipt,binding.at("model_receipt_bytes")),split->prior.receipt)||
               !names.matches(model_directory_identity(directory+"/"+split->part_directory),split->part_directory_identity))
                throw std::runtime_error("The sealed metadata directory or receipt changed");
        };
        auto verify_parts=[&]{verify_namespace();for(const auto &part:split->physical)
            if(!names.matches(model_file_identity(directory+"/"+part.path,part.bytes),part.identity))
                throw std::runtime_error("A sealed original metadata source part changed");};
        const auto before_identities=diagnostic_VM_population();verify_parts();
        const auto before_metadata=diagnostic_VM_population();
        qwen_app::enable_native_direct_metadata();metadata_memory.enable();
        qwen_app::ModelFootprint footprint;std::unordered_set<std::string> tensors;
        for(std::size_t i=0;i<76;++i) {
            require_CPU_metadata_budget();verify_namespace();metadata_file_index=i;
            const auto &file=receipt.at("files").at(i);const auto path=model_file(startup.model_receipt,file.at("path"));
            const auto observed=model_file_identity(path,split->prior.files.at(i)[5]);
            if(!names.matches(observed,split->prior.files.at(i)))throw std::runtime_error("The original GGUF first part changed");
            qwen_app::register_native_direct_metadata(path,observed,file.at("bytes"));
            inspect_container(path,i==0,footprint,tensors,file.at("bytes"),observed[5]);
            sample_metadata_memory(4);require_CPU_metadata_budget();
            qwen_native_stage("mini_metadata_original_container_returned_GPU_not_started");
        }
        const auto after_metadata=diagnostic_VM_population();
        if(!metadata_memory.complete()||footprint.mapped_files!=total||footprint.device_weights!=8755105280ull||
           footprint.mapped_experts!=241591910400ull||footprint.lazy_ple!=102400491520ull||
           footprint.mapped_embeddings!=1271398400ull)
            throw std::runtime_error("Complete original metadata footprint or observations differ");
        verify_parts();require_CPU_metadata_budget();const auto after_identities=diagnostic_VM_population();
        write_report(output+".metadata-memory",{{"schema","ps5-qwen-metadata-memory-result-v1"},{"pid",getpid()},
            {"run_id",run},{"complete",true},{"files",76},{"records",metadata_records()},
            {"candidate_SELF_sha256",binding.at("candidate_SELF_sha256")},{"model_receipt_sha256",binding.at("model_receipt_sha256")},
            {"footprint",{{"device_weights",footprint.device_weights},{"mapped_experts",footprint.mapped_experts},
                {"lazy_ple",footprint.lazy_ple},{"mapped_embeddings",footprint.mapped_embeddings},
                {"mapped_files",footprint.mapped_files},{"largest_device_tensor",footprint.largest_device_tensor},
                {"skipped_mtp",footprint.skipped_mtp},{"trunk_layers",footprint.trunk_layers},{"tensors",footprint.tensors}}},
            {"all_original_integrity_and_footprint_checks_passed",true},{"all_metadata_parsers_and_descriptors_returned",true},
            {"whole_source_identity_checks_before_and_after",true},{"source_seal_sha256",split->prior.report_sha256},
            {"VM_before_identities",before_identities},{"VM_before_metadata",before_metadata},
            {"VM_after_metadata",after_metadata},{"VM_after_identities",after_identities},
            {"CPU_heap_allowance_bytes",64u<<20},{"CPU_metadata_only_binary",true},
            {"GPU_calls",0},{"source_workers",0},{"virtual_source_calls",0},{"model_loaded",false},{"ordinary_OS_close_required",true}});
        qwen_native_stage("metadata_memory_CPU_diagnostic_completed_GPU_not_started_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
    }catch(const std::exception &e){
        qwen_native_log_bytes(e.what(),std::strlen(e.what()));qwen_native_log_bytes("\n",1);
        if(!output.empty())try{write_report(output+".failure",{{"stage","mini_metadata_CPU"},{"message",e.what()},
            {"GPU_calls",0},{"model_loaded",false},{"records",metadata_records()},
            {"observation_count",metadata_memory.size()},{"final_source_identity_admission_claimed",false}});}catch(...){}
        qwen_native_stage("mini_metadata_CPU_known_returned_refusal_GPU_not_started");qwen_native_halt("mini_metadata_CPU_admission_refused");
    }
}

// SPDX-License-Identifier: MIT
// A bounded CPU-only comparison of original protected source keys and one arena.
#define main unused_mini_metadata_entry
#include "mini_metadata_memory.cpp"
#undef main
#include "mini_virtual_source_policy.h"
#include "virtual_source.h"
#include "source_virtual_addresses.h"
#include <ps5platform/kernel.h>
static void matched_journal_markers(unsigned count) {
    for(unsigned i=0;i<count;++i) {
        (void)qwen_app::admit_native_system_memory();
        qwen_native_stage("mini_virtual_matched_CPU_journal_control_GPU_not_started");
    }
}
static Json completed_metadata(const Json &proof,const Json &binding) {
    const auto path=proof.at("report_path").get<std::string>();const auto bytes=proof.at("report_bytes").get<std::uint64_t>();
    const auto before=model_file_identity(path,bytes);std::ifstream file(path,std::ios::binary);
    std::string raw(static_cast<std::size_t>(bytes),'\0');file.read(raw.data(),static_cast<std::streamsize>(bytes));
    if(file.gcount()!=static_cast<std::streamsize>(bytes)||file.peek()!=std::char_traits<char>::eof()||file.bad()||
       qwen_app::sha256_metadata_bytes(raw)!=proof.at("report_sha256")||model_file_identity(path,bytes)!=before)
        throw std::runtime_error("The completed CPU metadata proof changed");
    const auto r=Json::parse(raw);
    if(r.at("schema")!="ps5-qwen-metadata-memory-result-v1"||r.at("pid")!=proof.at("pid")||r.at("run_id")!=proof.at("run_id")||
       r.at("candidate_SELF_sha256")!=proof.at("SELF_sha256")||r.at("model_receipt_sha256")!=binding.at("model_receipt_sha256")||
       r.at("complete")!=true||r.at("files")!=76||r.at("records").size()!=380||r.at("CPU_metadata_only_binary")!=true||
       r.at("all_original_integrity_and_footprint_checks_passed")!=true||r.at("all_metadata_parsers_and_descriptors_returned")!=true||
       r.at("whole_source_identity_checks_before_and_after")!=true||r.at("GPU_calls")!=0||r.at("model_loaded")!=false)
        throw std::runtime_error("The original CPU metadata qualification differs");
    return r;
}
int main(int argc,char **argv) {
    qwen_native_stage("mini_virtual_source_CPU_main_entered_GPU_not_started");
    std::string output;Json rounds=Json::array(),quiet;
    try {
        const auto startup=qwen_app::read_startup(argc,argv);output=startup.admission_report;
        std::ifstream input(startup.development_policy);const auto policy=Json::parse(input);
        const auto run=qwen_app::require_mini_virtual_source_policy(policy,startup.first_generation_validation,startup.native_display,output);
        const auto &binding=policy.at("native_first_generation_validation");
        qwen_app::enable_native_memory_backpressure();require_CPU_metadata_budget();
        write_report(output+".first.start",{{"schema","ps5-qwen-first-generation-start-v1"},{"pid",getpid()},
            {"run_id",run},{"candidate_SELF_sha256",binding.at("candidate_SELF_sha256")},
            {"model_receipt_sha256",binding.at("model_receipt_sha256")},{"model_loaded",false},{"Vulkan_initialized",false}});
        qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",binding.at("candidate_SELF_bytes"),binding.at("candidate_SELF_sha256"),30);
        qwen_app::verify_native_startup_file_direct(startup.model_receipt,binding.at("model_receipt_bytes"),binding.at("model_receipt_sha256"),30);
        qwen_native_stage("complete_SELF_and_receipt_direct_SHA256_passed GPU_not_started=1");
        qwen_app::admit_cpu_runtime(qwen_native_stage);
        (void)completed_metadata(policy.at("native_completed_metadata"),binding);
        const auto receipt=qwen_app::read_model_receipt(startup.model_receipt);(void)qwen_app::validate_model_receipt(receipt);
        std::array<std::size_t,8> spans{};std::size_t total=0;
        for(unsigned i=0;i<8;++i){spans[i]=qwen_app::virtual_source_span(receipt.at("files").at(7+i).at("bytes"));
            total=qwen_app::checked_memory_sum(total,spans[i]);}
        if(total>(32ull<<30))throw std::runtime_error("The representative source span exceeds its fixed CPU scope");
        // Attribute asynchronous title startup before measuring journal costs.
        // No journal, allocation, model access or virtual reservation occurs
        // between these two VM observations. The result is written afterwards.
        require_CPU_metadata_budget();
        qwen_native_stage("mini_virtual_quiet_interval_before_no_logs_or_allocations");
        const auto quiet_before=diagnostic_VM_population();
        const auto quiet_started=qwen_app::ProfileClock::now();
        for(unsigned i=0;i<5;++i)if(usleep(1000000))
            throw std::runtime_error("The bounded CPU quiet observation was interrupted");
        const auto quiet_elapsed=qwen_app::profile_elapsed_ns(quiet_started);
        const auto quiet_after=diagnostic_VM_population();
        if(quiet_elapsed<5000000000ull)throw std::runtime_error("The CPU quiet observation ended early");
        quiet={{"seconds",5},{"elapsed_ns",quiet_elapsed},{"VM_before",quiet_before},{"VM_after",quiet_after},
            {"journal_writes",0},{"allocations",0},{"virtual_source_calls",0},{"model_payload_reads",0},{"GPU_calls",0}};
        write_report(output+".virtual-source-quiet",quiet);
        qwen_native_stage("mini_virtual_quiet_interval_completed_GPU_not_started");
        for(unsigned round=0;round<4;++round) {
            require_CPU_metadata_budget();const auto observation=qwen_app::admit_native_system_memory();
            const auto required=std::uint64_t(observation.kernel_minimum)+std::max<std::uint64_t>(observation.kernel_reserved,256)+512;
            if(observation.kernel_free<required)throw std::runtime_error("CPU source round cannot retain its operational reserve and 512 extra pages");
            const auto before=diagnostic_VM_population();const bool arena=round==1||round==2;
            std::array<std::uintptr_t,8> addresses{};std::uintptr_t root=0;const auto started=qwen_app::ProfileClock::now();
            if(arena){root=qwen_app::reserve_native_virtual_source(total);std::size_t offset=0;
                for(unsigned i=0;i<8;++i){addresses[i]=root+offset;offset+=spans[i];}}
            else for(unsigned i=0;i<8;++i){(void)qwen_app::admit_native_system_memory();addresses[i]=qwen_app::reserve_native_virtual_source(spans[i]);}
            const auto reserved_API=diagnostic_VM_population();
            // The original reserve/protection helper emits five markers per
            // region. Match 8 versus 1 regions before comparing VM populations.
            matched_journal_markers(arena?35:0);
            const auto reserved=diagnostic_VM_population();
            for(unsigned i=0;i<8;++i){void *first=nullptr,*last=nullptr;std::uint32_t bits=~std::uint32_t(0);
                qwen_native_stage("mini_virtual_slice_protection_before_native_call");
                const auto rc=sceKernelQueryMemoryProtection(reinterpret_cast<void*>(addresses[i]),&first,&last,&bits);
                qwen_native_stage("mini_virtual_slice_protection_native_call_returned");
                if(rc||reinterpret_cast<std::uintptr_t>(first)>addresses[i]||reinterpret_cast<std::uintptr_t>(last)<addresses[i]+spans[i]||bits)
                    throw std::runtime_error("CPU source slice ownership/protection is unknown; every range retained");}
            const auto checked=diagnostic_VM_population();
            if(arena)qwen_app::release_native_virtual_source(root,total);
            else for(unsigned i=8;i>0;--i)qwen_app::release_native_virtual_source(addresses[i-1],spans[i-1]);
            const auto released_API=diagnostic_VM_population();
            // The original release emits two markers per native region.
            matched_journal_markers(arena?14:0);
            const auto after=diagnostic_VM_population();require_CPU_metadata_budget();
            rounds.push_back({{"round",round},{"mode",arena?"shared_arena":"per_file"},{"logical_regions",8},
                {"native_reservations",arena?1:8},{"native_releases",arena?1:8},{"virtual_bytes",total},
                {"required_kernel_free_pages_before_round",required},{"VM_before",before},
                {"VM_after_reserve_API",reserved_API},{"VM_after_reserve_matched_journal",reserved},
                {"VM_after_queries",checked},{"VM_after_release_API",released_API},{"VM_after_retirement",after},
                {"native_and_matched_journal_markers",72},{"matched_control_markers",arena?49:0},
                {"elapsed_ns",qwen_app::profile_elapsed_ns(started)},{"all_logical_slices_PROT_NONE",true},{"all_ranges_positively_retired",true}});
            write_report(output+".virtual-source-round-"+std::to_string(round),rounds.back());
        }
        write_report(output+".virtual-source",{{"schema","ps5-qwen-mini-virtual-source-result-v1"},{"pid",getpid()},
            {"run_id",run},{"candidate_SELF_sha256",binding.at("candidate_SELF_sha256")},
            {"model_receipt_sha256",binding.at("model_receipt_sha256")},{"CPU_only",true},{"complete",true},
            {"rounds",rounds},{"quiet_control",quiet},{"representative_virtual_bytes",total},{"logical_regions_per_round",8},
            {"model_payload_reads",0},{"GPU_calls",0},{"source_workers",0},{"model_loaded",false},
            {"all_ranges_positively_retired",true},{"all_native_calls_returned",true},{"automatic_retries",0},
            {"full_model_speed_qualified",false},{"full_model_virtual_capacity_qualified",false}});
        qwen_native_stage("mini_virtual_source_CPU_completed_GPU_not_started_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
    }catch(const std::exception &e){qwen_native_log_bytes(e.what(),std::strlen(e.what()));qwen_native_log_bytes("\n",1);
        if(!output.empty())try{write_report(output+".failure",{{"stage","mini_virtual_source_CPU"},{"message",e.what()},
            {"completed_rounds",rounds},{"GPU_calls",0},{"model_loaded",false},{"unknown_GPU_completion",false},
            {"unretired_CPU_ranges_retained_until_normal_OS_close",true}});}catch(...){}
        qwen_native_stage("mini_virtual_source_CPU_known_returned_refusal_GPU_not_started");qwen_native_halt("mini_virtual_source_CPU_admission_refused");
    }
}

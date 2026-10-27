// SPDX-License-Identifier: MIT
#include "resident_phase_vm.h"
#include <fstream>
#include <iostream>
int main(int argc,char **argv) {
    if(argc!=2)return 2;using J=nlohmann::json;std::ifstream input(argv[1]);J report=J::parse(input);
    J policy={{"native_resident_phase_VM",{{"schema","ps5-qwen-resident-phase-VM-v1"},{"enabled",true},
        {"source_window_extra_pages",19},{"GPU_initializer_extra_pages",10},{"context_extra_pages",245},
        {"startup_settle_samples",51},{"startup_settle_interval_us",100000},
        {"historical_whole_interval_is_per_operation_cost",false},
        {"completed_indexed_fixture_uses_operational_and_next_window_reserves",true},
        {"original_Direct_Flexible_heap_and_completion_guards",true},{"automatic_retries",0}}},
        {"native_resident_buffer_qualification",{{"case",3643},{"pid",report.at("pid")},{"run_id",report.at("run_id")},
        {"report_bytes",3178},{"report_sha256","66ad9bbcb2e4fa45ecffee0e4f29a9367d934049759932970f49d85bcc30c94d"}}}};
    qwen_app::require_resident_phase_VM(policy,report);unsigned rejected=0;
    auto deny=[&](const J &p,const J &r){bool failed=false;try{qwen_app::require_resident_phase_VM(p,r);}catch(...){failed=true;}
        if(!failed)throw std::runtime_error("Altered phase qualification admitted");++rejected;};
    const auto expected=policy.at("native_resident_phase_VM");
    for(auto it=expected.begin();it!=expected.end();++it){auto changed=policy;changed["native_resident_phase_VM"].erase(it.key());deny(changed,report);
        changed=policy;changed["native_resident_phase_VM"][it.key()]=nullptr;deny(changed,report);}
    auto changed=report;changed["buffer_capacity_measurement"]["allocated_buffers"]=4;deny(policy,changed);
    changed=report;changed["unknown_completion"]=true;deny(policy,changed);
    qwen_app::SystemMemoryObservation memory;memory.page_size=16384;memory.kernel_pages=138739;memory.flexible_available=400ull<<20;
    memory.kernel_minimum=898;memory.kernel_reserved=206;memory.kernel_target=2974;memory.kernel_free=1173;
    qwen_app::require_resident_source_VM(memory);
    memory.kernel_free=1172;bool refused=false;try{qwen_app::require_resident_source_VM(memory);}catch(...){refused=true;}
    if(!refused)throw std::runtime_error("The next-window margin was omitted");
    memory.kernel_free=1154;(void)qwen_app::qualified_system_headroom(memory);
    std::cout<<rejected<<" altered phase bindings rejected; ordinary floor and 19-page next-window margin remain distinct\n";
}

// SPDX-License-Identifier: MIT
#include "split_model_integrity.h"
#include <functional>
#include <iostream>
using Json=nlohmann::json;
using namespace qwen_app;
static void check(bool b,const char*m){if(!b)throw std::runtime_error(m);}
int main(){try{
    const std::uint64_t total=model_source_part_bytes+12345;
    const std::string name="original.gguf",directory="split512-"+std::string(32,'a'),sha(64,'b');
    auto key=[](std::uint64_t inode,std::uint64_t bytes,bool dir){return SourceIdentity{1,inode,dir?0040755u:0100644u,0,0,bytes,100,0,100,0};};
    Json receipt={{"files",Json::array({{{"path",name},{"bytes",total},{"sha256",sha}}})}};
    Json report={{"schema","ps5-qwen-split512-native-integrity-v1"},{"original_receipt_sha256",sha},
        {"part_bytes",model_source_part_bytes},{"logical_bytes",total},{"all_original_logical_SHA256_matched",true},
        {"all_physical_part_SHA256_matched",true},{"all_copy_publish_truncate_operations_completed",true},
        {"pending_operations",0},{"model_loaded",false},{"Vulkan_initialized",false},{"GPU_calls",0},
        {"maximum_source_window_bytes",model_read_window},{"automatic_retries",0},
        {"directory_identity",key(1,4096,true)},{"receipt_identity",key(2,300,false)},
        {"part_directory",directory},{"part_directory_identity",key(3,4096,true)},
        {"physical_files",2},{"verification_elapsed_ms",1234},
        {"logical_files",Json::array({{{"path",name},{"bytes",total},{"sha256",sha},
            {"parts",Json::array({{{"path",name},{"offset",0},{"bytes",model_source_part_bytes},
                {"sha256",sha},{"identity",key(10,model_source_part_bytes,false)}},
                {{"path",directory+"/"+name+".part-1"},{"offset",model_source_part_bytes},{"bytes",12345},
                {"sha256",sha},{"identity",key(11,12345,false)}}})}}})}};
    auto gate_for=[&](const Json&r){const auto raw=r.dump();return Json{{"model_receipt_sha256",sha},{"model_receipt_bytes",300},
        {"split_native_integrity",{{"schema","ps5-qwen-split512-native-integrity-policy-v1"},
            {"same_boot_bound_by_launcher",true},{"host_originals_retained_and_verified",true},
            {"raw",raw},{"sha256",sha256_metadata_bytes(raw)}}}};};
    const auto gate=gate_for(report);const auto accepted=split_model_integrity(gate,receipt,total);
    check(accepted&&accepted->physical.size()==2&&accepted->logical.size()==1&&
        accepted->logical[0].bytes==total&&accepted->prior.files[0][5]==model_source_part_bytes,
        "Logical and physical source identities were conflated");
    check(!split_model_integrity(Json::object(),receipt,total),"An ordinary source was silently split");
    unsigned checks=2;
    auto flat=report;flat["part_directory"]="";flat["part_directory_identity"]=flat["directory_identity"];
    flat["logical_files"][0]["parts"][1]["path"]=name+".part-1";
    check(bool(split_model_integrity(gate_for(flat),receipt,total)),"Exact root-directory parts were rejected");++checks;
    const auto refuse=[&](Json changed){bool caught=false;try{split_model_integrity(changed,receipt,total);}catch(const std::exception&){caught=true;}
        check(caught,"Unsafe split integrity was accepted");++checks;};
    auto bad=gate;bad["split_native_integrity"]["raw"]="{}";refuse(bad);
    bad=gate;bad["prior_native_integrity"]=Json::object();refuse(bad);
    bad=gate;bad["split_native_integrity"]["same_boot_bound_by_launcher"]=false;refuse(bad);
    bad=gate;bad["split_native_integrity"]["host_originals_retained_and_verified"]=false;refuse(bad);
    const std::vector<std::function<void(Json&)>>faults={
        [](Json&r){r["pending_operations"]=1;},[](Json&r){r["model_loaded"]=true;},
        [](Json&r){r["all_original_logical_SHA256_matched"]=false;},[](Json&r){r["all_physical_part_SHA256_matched"]=false;},
        [](Json&r){r["all_copy_publish_truncate_operations_completed"]=false;},[](Json&r){r["automatic_retries"]=1;},
        [](Json&r){r["logical_bytes"]=1;},[](Json&r){r["physical_files"]=1;},
        [](Json&r){r["part_directory"]="../unsafe";},[](Json&r){r["receipt_identity"][5]=301;},
        [](Json&r){r["logical_files"][0]["parts"][1]["offset"]=0;},
        [](Json&r){r["logical_files"][0]["parts"][1]["path"]="../outside";},
        [](Json&r){r["logical_files"][0]["parts"][1]["identity"][1]=10;},
        [](Json&r){r["logical_files"][0]["parts"][1]["identity"][2]=0100666;},
        [](Json&r){r["logical_files"][0]["parts"][1]["identity"][3]=1;},
        [](Json&r){r["logical_files"][0]["parts"][1]["identity"][0]=2;},
        [](Json&r){r["logical_files"][0]["parts"][1]["identity"][5]=12346;},
        [](Json&r){r["logical_files"][0]["parts"][1]["sha256"]="invalid";},
        [](Json&r){r["logical_files"][0]["sha256"]=std::string(64,'c');},
        [](Json&r){r["logical_files"][0]["bytes"]=1;},
        [](Json&r){r["logical_files"][0]["parts"].erase(1);},
        [](Json&r){r["verification_elapsed_ms"]=7200001;}};
    for(const auto&fault:faults){auto changed=report;fault(changed);refuse(gate_for(changed));}
    std::cout<<checks<<" split integrity/namespace/completeness/digest refusal controls passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}

// SPDX-License-Identifier: MIT
// Metadata fixtures only: no GGUF/model data or GPU/backend API is accessed.
#include "model_receipt.h"
#include <iostream>
using namespace qwen_app;
using Json=nlohmann::json;
static unsigned rejected=0;
static void check(bool value) {if(!value)throw std::runtime_error("Model receipt check failed");}
template<class Function> void reject(Function function) {
    bool failed=false;try{function();}catch(const std::exception &){failed=true;}check(failed);++rejected;
}
int main(int argc,char ** argv) {
    try {
        if(argc!=4)throw std::invalid_argument("Fixture, oversized receipt and dependency lock are required");
        auto valid=read_model_receipt(argv[1]);
        reject([&]{validate_model_receipt(valid);});
        valid.erase("test_fixture_only"); // Only the in-memory test object becomes a positive metadata fixture.
        const auto mapped=validate_model_receipt(valid);
        Json dependencies;std::ifstream lock_file(argv[3]);lock_file>>dependencies;
        check(dependencies.at("model").at("revision")==original_model_revision);
        check(dependencies.at("llama_cpp").at("revision")==original_converter_revision);
        auto bad=valid;bad["schema"]="ps5-qwen-bf16-conversion-v1";reject([&]{validate_model_receipt(bad);});
        bad=valid;bad.erase("conversion_audit");reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["conversion_audit"]["schema"]="ps5-qwen-conversion-audit-v1";reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["original_revision"]="wrong";reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["upstream_revision"]="wrong";reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["converter_sources"]["python_files"]=236;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["conversion_audit"]["tensor_layout_sha256"]=std::string(64,'0');reject([&]{validate_model_receipt(bad);});
        for(const auto * field:{"tensor_count","PLE_parts_verified","PLE_payload_bytes_verified",
                               "expert_payload_bytes_verified","expert_projection_tensors_verified",
                               "embedding_payload_bytes_verified","dense_tensors_replayed","dense_payload_bytes_replayed"}) {
            bad=valid;bad["conversion_audit"][field]=receipt_integer(bad["conversion_audit"],field)-1;
            reject([&]{validate_model_receipt(bad);});
        }
        bad=valid;bad["conversion_audit"]["tensor_count"]=1256.0;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["conversion_audit"]["tensor_count"]=-1;reject([&]{validate_model_receipt(bad);});
        for(const auto * field:{"complete_tensor_set","exact_shapes_and_precision","exact_PLE_integer_constants",
                               "complete_converted_tensor_payload_verified","original_shards_verified"}) {
            bad=valid;bad["conversion_audit"][field]=false;reject([&]{validate_model_receipt(bad);});
        }
        bad=valid;bad["conversion_audit"]["complete_tensor_set"]=1;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["learned_inference_performed"]=true;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["conversion_audit"]["physical_memory_admitted"]=true;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["files"][0]["path"]="../model.gguf";reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["files"].push_back(bad["files"][0]);reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["files"][0]["sha256"]="missing";reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["files"][0]["bytes"]=1;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["files"][0]["bytes"]=513ull<<30;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["files"][0]["bytes"]=-1;reject([&]{validate_model_receipt(bad);});
        bad=valid;bad["conversion_audit"]["mapped_file_bytes"]=mapped+1;reject([&]{validate_model_receipt(bad);});
        reject([&]{read_model_receipt(argv[2]);});
        ModelFootprint model;model.trunk_layers=48;model.tensors=1256;model.device_weights=8755105280ull;
        model.mapped_experts=241591910400ull;model.lazy_ple=102400491520ull;model.mapped_embeddings=1271398400ull;
        model.skipped_mtp=5217016832ull;model.largest_device_tensor=1271398400ull;model.mapped_files=mapped;
        validate_original_footprint(model,mapped);
        auto changed=model;--changed.tensors;reject([&]{validate_original_footprint(changed,mapped);});
        changed=model;--changed.lazy_ple;reject([&]{validate_original_footprint(changed,mapped);});
        changed=model;--changed.device_weights;reject([&]{validate_original_footprint(changed,mapped);});
        changed=model;--changed.mapped_files;reject([&]{validate_original_footprint(changed,mapped);});
        std::cout<<"Original v2 receipt and native footprint accepted; "<<rejected<<" malformed/legacy metadata cases rejected\n";
    } catch(const std::exception & error) {std::cerr<<error.what()<<'\n';return 1;}
}

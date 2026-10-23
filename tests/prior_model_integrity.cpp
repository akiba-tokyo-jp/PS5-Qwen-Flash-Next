// SPDX-License-Identifier: MIT
#include "prior_model_integrity.h"
#include <fstream>
#include <iostream>
#include <functional>

using Json = nlohmann::json;
int main(int argc,char **argv) {
    try {
        if(argc!=3)throw std::runtime_error("Expected original receipt and prior-integrity fixture");
        std::ifstream a(argv[1]),b(argv[2]);const Json receipt=Json::parse(a),gate=Json::parse(b);
        std::uint64_t total=0;for(const auto &file:receipt.at("files"))total+=file.at("bytes").get<std::uint64_t>();
        unsigned checks=0;
        auto positive=qwen_app::prior_model_integrity(gate,receipt,total);
        if(!positive||positive->files.size()!=76||positive->original_elapsed_ms!=5370082)throw std::runtime_error("Prior native positive fixture was rejected");
        ++checks;
        auto fresh=gate;fresh.erase("prior_native_integrity");if(qwen_app::prior_model_integrity(fresh,receipt,total))throw std::runtime_error("Fresh hashing was replaced");++checks;
        auto reject=[&](Json changed){bool refused=false;try{qwen_app::prior_model_integrity(changed,receipt,total);}catch(const std::exception &){refused=true;}
            if(!refused)throw std::runtime_error("Unqualified prior integrity evidence was admitted");++checks;};
        auto rewrite=[&](const char *key,const std::function<void(Json&)> &change){auto changed=gate;
            auto &entry=changed["prior_native_integrity"][key];auto value=Json::parse(entry["raw"].get<std::string>());change(value);
            const auto raw=value.dump();entry["raw"]=raw;entry["sha256"]=qwen_app::sha256_metadata_bytes(raw);return changed;};
        auto tampered=gate;tampered["prior_native_integrity"]["snapshot"]["raw"]="{}";reject(tampered);
        reject(rewrite("integrity_report",[](Json &j){j["all_SHA256_matched"]=false;}));
        reject(rewrite("integrity_report",[](Json &j){j["verification_elapsed_ms"]=7200001;}));
        reject(rewrite("native_start",[](Json &j){j["model_receipt_sha256"]=std::string(64,'0');}));
        reject(rewrite("snapshot",[](Json &j){j["files"][0]["identity"][2]=0100666;}));
        reject(rewrite("snapshot",[](Json &j){j["files"][0]["identity"][3]=1;}));
        reject(rewrite("snapshot",[](Json &j){j["files"][0]["identity"][5]=1;}));
        reject(rewrite("snapshot",[](Json &j){j["files"][0]["identity"][8]=j["seal_evidence_identity"][6].get<std::uint64_t>()+1;}));
        reject(rewrite("snapshot",[](Json &j){j["directory_identity"][6]=j["seal_evidence_identity"][6].get<std::uint64_t>()+1;}));
        reject(rewrite("snapshot",[](Json &j){j["files"][1]["identity"][1]=j["files"][0]["identity"][1];}));
        reject(rewrite("snapshot",[](Json &j){j["files"][76]["path"]="wrong-receipt.json";}));
        reject(rewrite("snapshot",[](Json &j){j["files"][0]["identity"][7]=0.5;}));
        std::cout<<"Prior native integrity: "<<checks<<" positive, ownership, timestamp, identity, digest and deadline checks passed\n";
    } catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}
}

// SPDX-License-Identifier: MIT
#include "resident_worker_qualification.h"
#include <iostream>
int main() {
    using J=nlohmann::json;
    J proof={{"case",3538},{"report_bytes",223},{"report_sha256","17e3f65b643209240bbcd83435e48bf91a45bfec9ba8eec641546cb94e5bbf6b"}};
    J result={{"GPU_calls",0},{"IO_payload_reads",0},{"completed",true},{"lifetimes",4},
        {"maximum_matched_idle_decline_pages",0},{"maximum_sampled_worker_VM_decline_pages",2},
        {"sampled_maxima_not_universal_minima",true}};
    const auto price=qwen_app::resident_worker_price(proof,result);
    if(price.worker_pages!=2||price.idle_pages||price.completed!=4)throw std::runtime_error("Worker qualification price changed");
    unsigned rejected=0;
    const auto deny=[&](const J &p,const J &v){bool failed=false;try{qwen_app::resident_worker_price(p,v);}catch(...){failed=true;}
        if(!failed)throw std::runtime_error("Altered worker measurement admitted");++rejected;};
    for(auto it=result.begin();it!=result.end();++it){auto changed=result;changed.erase(it.key());deny(proof,changed);
        changed=result;changed[it.key()]=nullptr;deny(proof,changed);}
    auto changed=proof;changed["report_sha256"]=std::string(64,'0');deny(changed,result);
    changed=result;changed["maximum_sampled_worker_VM_decline_pages"]=2.0;deny(proof,changed);
    changed=result;changed["lifetimes"]=3;deny(proof,changed);
    std::cout<<rejected<<" altered worker qualifications rejected\n";
}

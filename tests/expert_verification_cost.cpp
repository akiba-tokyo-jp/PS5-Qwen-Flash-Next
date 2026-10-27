// SPDX-License-Identifier: MIT
#include "expert_verification_cost.h"
#include <limits>
#include <iostream>
using namespace qwen_app;
int main() {
    std::array<ExpertVerificationCost,3> c{{{1,1,1,true},{2,2,2,true},{4,4,4,true}}};
    if(choose_expert_verification_width(c)!=1)return 1;
    c[1].predicted_seconds=1;
    if(choose_expert_verification_width(c)!=2)return 2;
    c[2].predicted_seconds=1;
    if(choose_expert_verification_width(c)!=4)return 3;
    c[2].past_routes_available=false;
    if(choose_expert_verification_width(c)!=2)return 4;
    unsigned refused=0;
    const auto reject=[&](std::array<ExpertVerificationCost,3> row){
        try{choose_expert_verification_width(row);return false;}
        catch(const std::invalid_argument&){++refused;return true;}
    };
    for(unsigned index=0;index<3;++index) {
        auto bad=c;bad[index].width=3;if(!reject(bad))return 5;
        bad=c;bad[index].predicted_seconds=0;if(!reject(bad))return 6;
        bad=c;bad[index].predicted_seconds=std::numeric_limits<double>::infinity();if(!reject(bad))return 7;
        bad=c;bad[index].expected_committed=std::numeric_limits<double>::quiet_NaN();if(!reject(bad))return 8;
        bad=c;bad[index].expected_committed=bad[index].width+1;if(!reject(bad))return 9;
    }
    auto bad=c;bad[0].past_routes_available=false;if(!reject(bad))return 10;
    std::cout<<"{\"cost_controls_passed\":true,\"refusals\":"<<refused<<"}\n";
}

// SPDX-License-Identifier: MIT
#include "snapshot_replacement_budget.h"
#include <cassert>
int main(){
    using qwen_app::SnapshotReplacementBudget;SnapshotReplacementBudget b;int a=0,other=0;
    const auto cap=1792ull<<20,baseline=1600ull<<20,prefix=119267328ull,larger=120434688ull;
    b.bind(&a);auto first=b.begin(&a,prefix,baseline,cap);assert(first==SnapshotReplacementBudget::rounded(prefix));
    bool refused=false;try{b.begin(&a,prefix,baseline,cap);}catch(const std::runtime_error&){refused=true;}assert(refused);
    refused=false;try{b.completed(&a,prefix,false);}catch(const std::runtime_error&){refused=true;}assert(refused);
    b.completed(&a,prefix,true);const auto live=baseline+first;
    auto extra=b.begin(&a,larger,live,cap);assert(extra==SnapshotReplacementBudget::rounded(larger)-first);
    b.completed(&a,larger,true);assert(b.replacements()==1);
    assert(b.begin(&a,larger,live+extra,cap)==0);b.completed(&a,larger,true);
    refused=false;try{b.begin(&other,larger,live+extra,cap);}catch(const std::runtime_error&){refused=true;}assert(refused);
    refused=false;try{b.begin(&a,larger,1,cap);}catch(const std::runtime_error&){refused=true;}assert(refused);
    SnapshotReplacementBudget low;low.bind(&other);refused=false;
    try{low.begin(&other,prefix,cap-1,cap);}catch(const std::runtime_error&){refused=true;}assert(refused);
}

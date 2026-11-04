// SPDX-License-Identifier: MIT
#include "owned_stage_mode.h"
#include <cassert>
#include <cstdio>
int main(){
    qwen_stage_facts before{687931141,12670,6758400,0100777,0,0,1,1793708394,0},after=before;
    after.mode=0100444;assert(qwen_stage_after_seal(&before,&after,6758400));
    before.mode=0100644;assert(qwen_stage_after_seal(&before,&after,6758400));
    before.mode=0100444;assert(qwen_stage_after_seal(&before,&after,6758400));
    uint64_t qwen_stage_facts::* const fields[]={&qwen_stage_facts::device,&qwen_stage_facts::inode,&qwen_stage_facts::bytes,
        &qwen_stage_facts::mode,&qwen_stage_facts::uid,&qwen_stage_facts::gid,&qwen_stage_facts::links,
        &qwen_stage_facts::mtime_seconds,&qwen_stage_facts::mtime_nanoseconds};
    for(const auto member:fields){auto bad=after;++(bad.*member);
        assert(!qwen_stage_after_seal(&before,&bad,6758400));}
    auto bad=before;bad.mode=0120777;assert(!qwen_stage_before_seal(&bad,6758400));
    bad=before;bad.mode|=04000;assert(!qwen_stage_before_seal(&bad,6758400));
    assert(!qwen_stage_before_seal(&before,0));assert(!qwen_stage_before_seal(&before,6758401));
    assert(!qwen_stage_before_seal(&before,(512ULL<<20)+1));
    assert(!qwen_stage_after_seal(nullptr,&after,6758400));assert(!qwen_stage_after_seal(&before,nullptr,6758400));
    std::puts("{\"completed\":true,\"positive_controls\":3,\"negative_controls\":16,\"PS5_operations\":0}");
}

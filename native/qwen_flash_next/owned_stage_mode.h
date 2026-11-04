// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
struct qwen_stage_facts {uint64_t device,inode,bytes,mode,uid,gid,links,mtime_seconds,mtime_nanoseconds;};
static inline int qwen_stage_before_seal(const struct qwen_stage_facts*f,uint64_t expected){
    return f&&expected&&expected<=(512ULL<<20)&&f->device&&f->inode&&f->bytes==expected&&
        (f->mode&0170000)==0100000&&!(f->mode&07000)&&!f->uid&&!f->gid&&f->links==1&&f->mtime_nanoseconds<1000000000;
}
static inline int qwen_stage_after_seal(const struct qwen_stage_facts*before,const struct qwen_stage_facts*after,uint64_t expected){
    return qwen_stage_before_seal(before,expected)&&qwen_stage_before_seal(after,expected)&&
        (after->mode&07777)==0444&&before->device==after->device&&before->inode==after->inode&&
        before->bytes==after->bytes&&before->uid==after->uid&&before->gid==after->gid&&before->links==after->links&&
        before->mtime_seconds==after->mtime_seconds&&before->mtime_nanoseconds==after->mtime_nanoseconds;
}

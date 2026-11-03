/* SPDX-License-Identifier: MIT
 * Copy only explicitly owned new staging parts. No original model is written.
 */
#include "bounded_part_concat.h"
struct ConcatPart{const char*path;uint64_t bytes;const char*sha256;};
static const struct ConcatPart concat_parts[]=CONCAT_PARTS;
static _Alignas(16384) unsigned char concat_input[QWEN_CONCAT_WINDOW],concat_output[QWEN_CONCAT_WINDOW];
struct ConcatOwner{int input,output,part_initialized;unsigned index;int*calls;uint64_t deadline;struct stat before;struct ai_sha256 part,whole;};
static int concat_admit(struct ConcatOwner*owner){
    uint32_t free_pages=0;size_t n=4;const uint64_t now=qwen_launch_now(NULL);
    return now&&now<=owner->deadline&&!sysctlbyname("vm.stats.vm0.v_free_count",&free_pages,&n,NULL,0)&&n==4&&
        free_pages>=1201&&qwen_launch_headroom_sample(NULL);
}
static int64_t concat_read(void*opaque,unsigned part,uint64_t offset,void*data,size_t count){
    struct ConcatOwner*o=opaque;if(part>=sizeof(concat_parts)/sizeof(concat_parts[0])||!concat_admit(o))return -1;
    if(!offset){
        if(o->input>=0)return -1;
        o->input=open(concat_parts[part].path,O_RDONLY|O_NOFOLLOW|O_DIRECT);o->index=part;o->part_initialized=0;
        if(o->input<0)return -1;
        if(fstat(o->input,&o->before)||!S_ISREG(o->before.st_mode)||o->before.st_nlink!=1||
           (o->before.st_mode&0022)||o->before.st_size!=(off_t)concat_parts[part].bytes||
           !(fcntl(o->input,F_GETFL)&O_DIRECT))return -1;
        ai_sha256_init(&o->part);o->part_initialized=1;
    }
    if(o->input<0||o->index!=part)return -1;
    ++*o->calls;const ssize_t got=pread(o->input,data,count,(off_t)offset);
    const uint64_t left=concat_parts[part].bytes-offset;
    const size_t expected=left<count?(size_t)left:count;
    if(got!=(ssize_t)expected)return -1;
    ai_sha256_update(&o->part,data,expected);return got;
}
static int concat_write(void*opaque,uint64_t offset,const void*data,size_t bytes){
    struct ConcatOwner*o=opaque;if(!concat_admit(o))return 0;
    ++*o->calls;return pwrite(o->output,data,bytes,(off_t)offset)==(ssize_t)bytes;
}
static int concat_digest(void*opaque,const void*data,size_t bytes){
    struct ConcatOwner*o=opaque;ai_sha256_update(&o->whole,data,bytes);return 1;
}
static int concat_hash(struct ai_sha256*hash,const char*expected){
    unsigned char digest[32];char actual[65];ai_sha256_final(hash,digest);
    for(unsigned i=0;i<32;++i)snprintf(actual+2*i,3,"%02x",digest[i]);return !strcmp(actual,expected);
}
static int concat_end_part(void*opaque,unsigned part){
    struct ConcatOwner*o=opaque;if(o->input<0||o->index!=part)return 0;
    struct stat after;const int identity=!fstat(o->input,&after)&&unchanged(&o->before,&after);
    const int digest=identity&&o->part_initialized&&concat_hash(&o->part,concat_parts[part].sha256);
    const int closed=!close(o->input);o->input=-1;
    return report("CONCAT_PART index=%u SHA256=%d identity_exact=%d fd_closed=%d",part,digest,identity,closed)&&digest&&identity&&closed;
}
static int case_concatenate_model_parts(int*calls){
    const unsigned count=sizeof(concat_parts)/sizeof(concat_parts[0]);uint64_t sizes[128],total=0;
    if(!count||count>128||CONCAT_BYTES==0||CONCAT_BYTES>(512ULL<<20))return 0;
    for(unsigned i=0;i<count;++i){sizes[i]=concat_parts[i].bytes;if(!sizes[i]||sizes[i]>(512ULL<<20)-total)return 0;total+=sizes[i];}
    if(total!=CONCAT_BYTES)return 0;
    struct stat absent;if(lstat(CONCAT_TARGET,&absent)!=-1||errno!=ENOENT)return 0;
    struct ConcatOwner owner={.input=-1,.output=-1,.calls=calls,.deadline=qwen_launch_now(NULL)+UINT64_C(30000000000)};
    if(!concat_admit(&owner))return 0;
    owner.output=open(CONCAT_TARGET,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);if(owner.output<0)return 0;
    ai_sha256_init(&owner.whole);struct qwen_concat_stats stats={0};
    const struct qwen_concat_ops ops={&owner,concat_read,concat_write,concat_digest,concat_end_part};
    int valid=qwen_concat_copy(sizes,count,concat_input,concat_output,&ops,&stats)&&concat_hash(&owner.whole,CONCAT_SHA256);
    if(owner.input>=0){const int closed=!close(owner.input);owner.input=-1;valid=0;if(!closed)return 0;}
    if(valid)valid=!ftruncate(owner.output,(off_t)total)&&!fchmod(owner.output,0444)&&!fsync(owner.output);
    const int closed=!close(owner.output);owner.output=-1;
    if(valid&&closed)valid=qwen_launch_digest_matches(CONCAT_TARGET,total,CONCAT_SHA256);
    return report("CONCAT_COMPLETE success=%d logical_bytes=%llu physical_written=%llu reads=%u writes=%u closed_parts=%u target_closed=%d whole_SHA256_EOF=%d original_source_writes=0 GPU_calls=0",
        valid&&closed,(unsigned long long)stats.logical_bytes,(unsigned long long)stats.physical_written,stats.reads,stats.writes,
        stats.closed_parts,closed,valid&&closed)&&valid&&closed;
}

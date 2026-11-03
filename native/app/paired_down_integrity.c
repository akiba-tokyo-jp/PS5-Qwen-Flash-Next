/* SPDX-License-Identifier: MIT
 * Keep the qualified serial Direct reader in its original C compilation mode.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <time.h>
#include <unistd.h>
#include "sha256.h"
int qwen_paired_journal=-1;
uint32_t qwen_paired_minimum_free=UINT32_MAX;
static int paired_sysctl(const char*name,void*value,size_t*bytes,const void*set,size_t set_bytes){
    int result=sysctlbyname(name,value,bytes,set,set_bytes);
    if(!result&&value&&bytes&&*bytes==4&&!strcmp(name,"vm.stats.vm0.v_free_count")){
        uint32_t free=*(uint32_t*)value;if(free<qwen_paired_minimum_free)qwen_paired_minimum_free=free;
    }
    return result;
}
static int report(const char*format,...){
    char line[1024];va_list args;va_start(args,format);int n=vsnprintf(line,sizeof(line)-1,format,args);va_end(args);
    if(qwen_paired_journal<0||n<0||(size_t)n>=sizeof(line)-1)return 0;
    line[n++]='\n';return write(qwen_paired_journal,line,(size_t)n)==n&&!fsync(qwen_paired_journal);
}
static int unchanged(const struct stat*a,const struct stat*b){
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&a->st_mode==b->st_mode&&
        a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&
        a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
#define QWEN_LAUNCH_WINDOW 65536u
#define QWEN_LAUNCH_CPU_HEADROOM_WAIT 1
#include "app_named_stat.h"
#define lstat qwen_app_named_stat
#define sysctlbyname paired_sysctl
#include "launch_integrity_native.h"
#undef lstat
#undef sysctlbyname
int qwen_paired_digest(const char*path,size_t bytes,const char*sha){return qwen_launch_digest_matches(path,bytes,sha);}

/* SPDX-License-Identifier: GPL-3.0-or-later
 * Journaled exact-NID address observations. No dladdr, code read or APR call.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <dlfcn.h>
#include <sys/stat.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#include "binding_symbols.h"
/* A read-only, process-local lookup does not rely on an old HTTP-worker state.
 * Keep exact boot/idle ownership, and record current services for later scopes.
 */
static int context(unsigned phase){
    if(!boot(phase)||!idle(phase))return 0;
    for(size_t i=0;i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i){
        const struct expected_process*e=expected_processes+i;unsigned found=0;
        int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PID,e->pid};struct kinfo_proc k;memset(&k,0,sizeof(k));size_t n=sizeof(k);
        errno=0;int rc=sysctl(mib,4,&k,&n,NULL,0),error=errno;
        found=!rc&&n==sizeof(k)&&k.ki_structsize==sizeof(k)&&memchr(k.ki_comm,0,sizeof(k.ki_comm))&&!strcmp(k.ki_comm,e->name);
        if(!report("SERVICE_CURRENT phase=%u name=%s found=%u rc=%d errno=%d pid=%d ppid=%d uid=%u sec=%lld usec=%lld stat=%u flags=0x%x tracer=%d",phase,e->name,found,rc,error,k.ki_pid,k.ki_ppid,k.ki_uid,(long long)k.ki_start.tv_sec,(long long)k.ki_start.tv_usec,k.ki_stat,k.ki_flag,k.ki_tracer))return 0;
    }
    return boot(phase);
}
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;int ok=0;
    if(!report("BEGIN nonce=%s pid=%d ppid=%d scope=APR_exact_address CPU_only=1 APR_calls=0 GPU_calls=0 title_launches=0 module_loads=0",RECOVERY_NONCE,getpid(),getppid())||getuid()!=1||geteuid()!=0||!context(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    for(unsigned i=0;i<sizeof(binding_symbols)/sizeof(binding_symbols[0]);++i){
        const struct binding_symbol*s=binding_symbols+i;
        if(!report("BEFORE_EXACT index=%u name=%s nid=%s handle=0x1",i,s->name,s->nid))goto done;
        errno=0;intptr_t exact=kernel_dynlib_resolve(getpid(),1u,s->nid);int error=errno;
        if(!report("EXACT index=%u address=0x%llx errno=%d",i,(unsigned long long)exact,error))goto done;
        if(i){
            if(!report("BEFORE_SDK index=%u name=%s",i,s->name))goto done;
            void*p=dlsym(RTLD_DEFAULT,s->name);
            if(!report("SDK index=%u address=0x%llx matches_exact=%d",i,(unsigned long long)(uintptr_t)p,exact>0&&(uintptr_t)exact==(uintptr_t)p))goto done;
        }
    }
    const char*paths[]={"/app0","/app0/eboot.bin","/system/common/lib/libSceAmpr.sprx","/system_ex/common/lib/libSceAmpr.sprx"};
    for(unsigned i=0;i<sizeof(paths)/sizeof(paths[0]);++i){struct stat st;memset(&st,0,sizeof(st));errno=0;int rc=lstat(paths[i],&st),error=errno;
        if(!report("PATH index=%u path=%s rc=%d errno=%d mode=0%o bytes=%llu",i,paths[i],rc,error,st.st_mode,(unsigned long long)st.st_size))goto done;}
    if(!context(2))goto done;ok=1;
done:
    if(!report("END nonce=%s success=%d APR_calls=0 GPU_calls=0 title_launches=0 module_loads=0 no_retry=1",RECOVERY_NONCE,ok))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

/* SPDX-License-Identifier: GPL-3.0-or-later
 * Observe this helper's loaded APR/AMPR interface. No module load or I/O submit.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <dlfcn.h>
#include "sha256.h"
#include <sys/stat.h>
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"

static int context(unsigned phase){
    if(!boot(phase)||!idle(phase))return 0;
    for(size_t i=0;i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i)
        if(!service(expected_processes+i,phase))return 0;
    return boot(phase);
}
int main(int argc,char **argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    int ok=0;unsigned hashes=0;
    if(!report("BEGIN nonce=%s pid=%d scope=loaded_AMPR_metadata GPU_calls=0 title_launches=0 module_loads=0 IO_submits=0",RECOVERY_NONCE,getpid())||
       getuid()!=1||geteuid()!=0||!context(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i){
        if(!qwen_launch_digest_matches(files[i].path,(size_t)files[i].bytes,files[i].hash))goto done;
        ++hashes;
    }
    const char *module_names[]={"libkernel_web.sprx","libkernel.sprx","libSceAmpr.sprx"};
    uint32_t handles[3]={0};int present[3]={0};
    for(unsigned i=0;i<3;++i){
        struct {uint64_t a;uint32_t value,pad;uint64_t b;} handle={GUARD,0,0,GUARD};
        errno=0;int rc=kernel_dynlib_handle(getpid(),module_names[i],&handle.value);int error=errno;
        if(handle.a!=GUARD||handle.b!=GUARD||handle.pad)goto done;
        present[i]=rc==0;handles[i]=handle.value;
        if(!report("MODULE index=%u name=%s present=%d rc=%d errno=%d",i,module_names[i],present[i],rc,error))goto done;
    }
    const char *symbols[]={"pread","sceKernelAioSubmitReadCommands",
      "sceKernelAprResolveFilepathsToIds","sceKernelAprGetFileSize","sceKernelAprGetFileStat",
      "sceKernelAprSubmitCommandBuffer","sceKernelAprSubmitCommandBufferAndGetResult","sceKernelAprWaitCommandBuffer",
      "sceAmprCommandBufferConstructor","sceAmprAprCommandBufferConstructor","sceAmprCommandBufferSetBuffer",
      "sceAmprAprCommandBufferReadFile","sceAmprCommandBufferWriteAddressOnCompletion",
      "sceAmprCommandBufferWriteKernelEventQueue_04_00"};
    for(unsigned i=0;i<sizeof(symbols)/sizeof(symbols[0]);++i){
        void *sdk=dlsym(RTLD_DEFAULT,symbols[i]);int native_found[3]={0};
        for(unsigned j=0;j<3;++j)if(present[j])native_found[j]=kernel_dynlib_dlsym(getpid(),handles[j],symbols[i])>0;
        if(!report("SYMBOL index=%u name=%s SDK_found=%d kernel_web_found=%d kernel_found=%d AMPR_found=%d invoked=0",i,symbols[i],sdk!=NULL,native_found[0],native_found[1],native_found[2]))goto done;
    }
    if(!context(2))goto done;
    ok=1;
done:
    if(!report("END nonce=%s success=%d current_file_hashes=%u GPU_calls=0 title_launches=0 module_loads=0 IO_submits=0 no_retry=1",RECOVERY_NONCE,ok,hashes))ok=0;
    if(close(journal))ok=0;
    return ok?0:1;
}

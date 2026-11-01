/* SPDX-License-Identifier: GPL-3.0-or-later
 * Validate original OS PFS API bindings and option layouts before any image.
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
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;int ok=0;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s pid=%d ppid=%d scope=PFS_options CPU_only=1 APR_calls=0 GPU_calls=0 title_launches=0",RECOVERY_NONCE,getpid(),getppid())||getuid()!=1||geteuid()!=0||!boot(1)||!idle(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    if(!report("PFS_AUTH authid=0x%llx credentials_modified=0",(unsigned long long)kernel_get_ucred_authid(getpid()))||!report("BEFORE_FS_MODULE_LOAD original_system_module=1"))goto done;
    void*module=dlopen("libSceFsInternalForVsh.sprx",RTLD_LAZY);
    if(!report("FS_MODULE available=%d handle=%p",module!=NULL,module)||!module)goto done;
    const char*names[]={"sceFsInitCreatePprPfsSaveDataOpt","sceFsInitMountSaveDataOpt","sceFsInitUmountSaveDataOpt","sceFsCreatePprPfsSaveDataImage","sceFsMountSaveData","sceFsUmountSaveData","sceFsUfsAllocateSaveData"};
    for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i){
        void*fn=dlsym(module,names[i]);if(!report("PFS_BINDING index=%u name=%s available=%d",i,names[i],fn!=NULL)||!fn)goto done;
        if(i<3){
            struct{uint64_t a;unsigned char opt[256];uint64_t b;} v;memset(&v,0,sizeof(v));v.a=v.b=UINT64_C(0x581fa3329e081cd7);
            if(!report("BEFORE_OPTION_INIT index=%u",i))goto done;
            int rc=((int(*)(void*))fn)(v.opt);unsigned changed=0,last=0;
            for(unsigned j=0;j<sizeof(v.opt);++j)if(v.opt[j]){++changed;last=j;}
            int intact=v.a==UINT64_C(0x581fa3329e081cd7)&&v.b==UINT64_C(0x581fa3329e081cd7);
            uint32_t block=0;memcpy(&block,v.opt,4);
            if(!report("PFS_OPTION index=%u rc=%d canaries=%d nonzero_bytes=%u last_nonzero=%u first_word=%u",i,rc,intact,changed,last,block)||rc||!intact)goto done;
        }
    }
    if(!boot(2)||!idle(2))goto done;ok=1;
done:
    if(!report("END nonce=%s success=%d APR_calls=0 GPU_calls=0 title_launches=0 image_create_calls=0 mount_calls=0 credentials_modified=0",RECOVERY_NONCE,ok))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

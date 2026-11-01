/* SPDX-License-Identifier: GPL-3.0-or-later
 * Observe APR identity on an owned, positively mounted PFS control file.
 * A resolver rejection is a completed observation, not an APR speed result.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <dlfcn.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#include "pfs_fixture_context.h"
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;int ok=0,fd=-1,calls=0;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s pid=%d scope=owned_PFS_APR_identity GPU_calls=0 title_launches=0",RECOVERY_NONCE,getpid())||getuid()!=1||geteuid()!=0||!boot(1)||!idle(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    struct statfs fs;if(statfs(PFS_MOUNT,&fs)||strncmp(fs.f_fstypename,"pfs",3)||strcmp(fs.f_mntonname,PFS_MOUNT))goto done;
    char path[384];if(snprintf(path,sizeof(path),"%s/control.bin",PFS_MOUNT)>=(int)sizeof(path))goto done;
    unsigned char data[16384];fd=open(path,O_RDONLY|O_NOFOLLOW);if(fd<0||read(fd,data,sizeof(data))!=sizeof(data))goto done;
    if(close(fd))goto done;fd=-1;for(unsigned i=0;i<sizeof(data);++i)if(data[i]!=(unsigned char)(((i*17+29)^(i>>8))&255))goto done;
    if(!report("PFS_CONTROL name=%s bytes=16384 exact=1",fs.f_fstypename))goto done;
    typedef int(*resolve_fn)(const char*const*,uint32_t,uint32_t*,uint32_t*);
    typedef int(*size_fn)(uint32_t,uint64_t*);
    resolve_fn resolve=(resolve_fn)dlsym(RTLD_DEFAULT,"sceKernelAprResolveFilepathsToIds");
    size_fn size_api=(size_fn)dlsym(RTLD_DEFAULT,"sceKernelAprGetFileSize");if(!resolve||!size_api)goto done;
    struct{uint64_t a;uint32_t value,pad;uint64_t b;} id={GUARD,UINT32_MAX,0,GUARD},failed={GUARD,UINT32_MAX,0,GUARD};
    const char*name=path;if(!report("BEFORE_PFS_RESOLVE"))goto done;errno=0;++calls;
    int rc=resolve(&name,1,&id.value,&failed.value),error=errno;
    int intact=id.a==GUARD&&id.b==GUARD&&!id.pad&&failed.a==GUARD&&failed.b==GUARD&&!failed.pad;
    if(!report("PFS_RESOLVE rc=%d errno=%d id=%u error_index=%u canaries=%d",rc,error,id.value,failed.value,intact)||!intact)goto done;
    if(!rc){struct{uint64_t a,value,b;} size={GUARD,0,GUARD};errno=0;++calls;int sr=size_api(id.value,&size.value),se=errno;
        if(!report("PFS_SIZE rc=%d errno=%d bytes=%llu canaries=%d",sr,se,(unsigned long long)size.value,size.a==GUARD&&size.b==GUARD)||sr||size.value!=sizeof(data)||size.a!=GUARD||size.b!=GUARD)goto done;}
    if(!boot(2)||!idle(2))goto done;ok=1;
done:
    if(fd>=0&&close(fd))ok=0;
    if(!report("END nonce=%s success=%d APR_calls=%d APR_read_submits=0 GPU_calls=0",RECOVERY_NONCE,ok,calls))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

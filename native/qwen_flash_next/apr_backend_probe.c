/* SPDX-License-Identifier: GPL-3.0-or-later
 * Read-only current filesystem observations for APR/Kraken backend selection.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <sys/mount.h>
#include <sys/stat.h>
#include <stdlib.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
static const uint64_t fence=UINT64_C(0x38a25b108c3ef477);
static int valid_fs(const struct statfs*f){
    return f->f_version==STATFS_VERSION&&memchr(f->f_fstypename,0,sizeof(f->f_fstypename))&&
        memchr(f->f_mntonname,0,sizeof(f->f_mntonname))&&memchr(f->f_mntfromname,0,sizeof(f->f_mntfromname));
}
static int show(const char*kind,unsigned index,int rc,int error,const struct statfs*f,int intact){
    int valid=!rc&&valid_fs(f);
    return report("FILESYSTEM kind=%s index=%u rc=%d errno=%d canaries=%d valid=%d type=%u version=0x%x bsize=%llu iosize=%llu name=%s target=%s source=%s",kind,index,rc,error,intact,valid,
        valid?f->f_type:0,valid?f->f_version:0,(unsigned long long)(valid?f->f_bsize:0),(unsigned long long)(valid?f->f_iosize:0),
        valid?f->f_fstypename:"unavailable",valid?f->f_mntonname:"unavailable",valid?f->f_mntfromname:"unavailable");
}
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;int ok=0;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s pid=%d ppid=%d scope=APR_Kraken_filesystems CPU_only=1 APR_calls=0 GPU_calls=0 title_launches=0",RECOVERY_NONCE,getpid(),getppid())||getuid()!=1||geteuid()!=0||!boot(1)||!idle(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    const char*paths[]={"/data/ai","/system/common/lib","/system_ex","/mnt/pfs","/system_ex/app/PPSA99190"};
    for(unsigned i=0;i<sizeof(paths)/sizeof(paths[0]);++i){
        struct{uint64_t a;struct statfs value;uint64_t b;} f={0};f.a=f.b=fence;
        if(!report("BEFORE_STATFS index=%u path=%s structure_bytes=%u",i,paths[i],(unsigned)sizeof(f.value)))goto done;
        errno=0;int rc=statfs(paths[i],&f.value),error=errno;int intact=f.a==fence&&f.b==fence;
        if(!show("path",i,rc,error,&f.value,intact)||!intact||(!rc&&!valid_fs(&f.value)))goto done;
    }
    errno=0;int count=getfsstat(NULL,0,MNT_NOWAIT),count_error=errno;
    if(!report("GETFSSTAT_COUNT count=%d errno=%d",count,count_error)||count<=0||(size_t)count>SIZE_MAX/sizeof(struct statfs)-16)goto done;
    size_t capacity=(size_t)count+16,bytes=capacity*sizeof(struct statfs);
    uint64_t*storage=calloc(1,bytes+16);if(!report("MOUNT_STORAGE bytes=%llu allocated=%d",(unsigned long long)(bytes+16),storage!=NULL)||!storage){free(storage);goto done;}
    storage[0]=fence;uint64_t*end=(uint64_t*)((unsigned char*)storage+8+bytes);*end=fence;
    struct statfs*rows=(struct statfs*)(storage+1);errno=0;int n=getfsstat(rows,bytes,MNT_NOWAIT),error=errno;
    int valid=n>=0&&(size_t)n<capacity&&storage[0]==fence&&*end==fence,pfs=0,ordinary=0;
    if(!report("GETFSSTAT count=%d expected=%d capacity=%u errno=%d canaries=%d",n,count,(unsigned)capacity,error,storage[0]==fence&&*end==fence))valid=0;
    for(int i=0;valid&&i<n;++i){
        if(!valid_fs(rows+i)){valid=0;break;}
        int interesting=strcmp(rows[i].f_fstypename,"nullfs")&&strcmp(rows[i].f_fstypename,"devfs")&&strcmp(rows[i].f_fstypename,"tmpfs");
        if(!strncmp(rows[i].f_fstypename,"pfs",3)||!strcmp(rows[i].f_fstypename,"npfs"))++pfs;else ++ordinary;
        if(interesting&&!show("mounted",i,0,0,rows+i,1))valid=0;
    }
    errno=0;int after=getfsstat(NULL,0,MNT_NOWAIT),after_error=errno;
    if(!report("MOUNT_SUMMARY copied=%d after=%d errno=%d pfs_named=%d other=%d complete=%d",n,after,after_error,pfs,ordinary,valid&&n==after))valid=0;
    valid=valid&&n==after;free(storage);if(!valid)goto done;
    if(!boot(2)||!idle(2))goto done;ok=1;
done:
    if(!report("END nonce=%s success=%d APR_calls=0 GPU_calls=0 title_launches=0 filesystem_writes=0",RECOVERY_NONCE,ok))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

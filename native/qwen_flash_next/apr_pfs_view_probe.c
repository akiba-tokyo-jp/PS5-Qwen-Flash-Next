/* SPDX-License-Identifier: GPL-3.0-or-later
 * Project one owned PFS root into one authenticated, waiting native probe.
 * Never replace the registered title mount. Ordinary unmount only.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <dirent.h>
#include <sys/mount.h>
#include <sys/uio.h>
#include <sys/stat.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#include "pfs_fixture_context.h"
#include "pfs_view_context.h"
#define PARENT "/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime"
static int owners(unsigned expected){
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PROC,0};size_t n=sizeof(inventory.data);
    if(sysctl(mib,4,inventory.data,&n,NULL,0)||!n||n>sizeof(inventory.data)||n%sizeof(struct kinfo_proc))return 0;
    unsigned found=0;for(size_t i=0;i<n;i+=sizeof(struct kinfo_proc)){
        struct kinfo_proc k;memcpy(&k,inventory.data+i,sizeof(k));
        if(k.ki_structsize!=sizeof(k)||!memchr(k.ki_comm,0,sizeof(k.ki_comm)))return 0;
        if(!strcmp(k.ki_comm,"eboot.bin")){if(k.ki_uid!=1||k.ki_tracer)return 0;++found;}
    }
    return report("OWNED_NATIVE expected=%u found=%u",expected,found)&&found==expected;
}
int main(int argc,char**argv){
    int cleanup=argc==2&&!strcmp(argv[1],"--cleanup");if(!cleanup&&argc!=0&&argc!=1)return 2;
    journal=open(cleanup?RECOVERY_LOG "-cleanup":RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    int ok=0,mounts=0,unmounts=0,parent_changed=0,auth_changed=0;uint64_t original_auth=0;char target[512]={0},underlying[384];struct stat st;struct statfs fs;
    if(!report("BEGIN nonce=%s pid=%d scope=owned_PFS_native_view cleanup=%d GPU_calls=0",RECOVERY_NONCE,getpid(),cleanup)||getuid()!=1||geteuid()!=0||!boot(1)||!owners(cleanup?0:1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    if(statfs(PFS_MOUNT,&fs)||strncmp(fs.f_fstypename,"pfs",3)||strcmp(fs.f_mntonname,PFS_MOUNT))goto done;
    original_auth=kernel_get_ucred_authid(getpid());if(!original_auth||kernel_set_ucred_authid(getpid(),UINT64_C(0x4800000000000010)))goto done;auth_changed=1;
    if(kernel_get_ucred_authid(getpid())!=UINT64_C(0x4800000000000010)||!report("OWN_VIEW_AUTH filesystem_role=1 own_process_only=1"))goto done;
    if(snprintf(underlying,sizeof(underlying),"%s/%s",PARENT,PFS_VIEW_NAME)>=(int)sizeof(underlying))goto done;
    DIR*directory=opendir("/mnt/sandbox");if(!directory)goto done;unsigned count=0,matched=0;struct dirent*entry;
    while((entry=readdir(directory))){
        if(++count>512||!memchr(entry->d_name,0,sizeof(entry->d_name))){matched=99;break;}
        if(strncmp(entry->d_name,"PPSA99190_",10))continue;
        char program[512],candidate[512];
        if(snprintf(program,sizeof(program),"/mnt/sandbox/%s/app0/eboot.bin",entry->d_name)>=(int)sizeof(program)||
           snprintf(candidate,sizeof(candidate),"/mnt/sandbox/%s/app0/qwen-runtime/%s",entry->d_name,PFS_VIEW_NAME)>=(int)sizeof(candidate)){matched=99;break;}
        if(!qwen_launch_digest_matches(program,files[0].bytes,files[0].hash))continue;
        if(lstat(candidate,&st)){if(errno==ENOENT)continue;matched=99;break;}
        if(strlen(candidate)>=sizeof(fs.f_mntonname)){matched=99;break;}
        strcpy(target,candidate);++matched;
    }
    if(closedir(directory)||matched>1)goto done;
    if(cleanup){
        if(matched){
            if(statfs(target,&fs))goto done;
            if(!strcmp(fs.f_mntonname,target)){
                if(strcmp(fs.f_fstypename,"nullfs")||strcmp(fs.f_mntfromname,PFS_MOUNT)||!report("BEFORE_VIEW_UNMOUNT target=%s flags=0",target))goto done;
                errno=0;++unmounts;int rc=unmount(target,0),error=errno;
                if(!report("PFS_VIEW_UNMOUNT rc=%d errno=%d",rc,error)||rc)goto done;
            }
        }else if(!report("PFS_VIEW_RETIRED native_sandbox_absent=1"))goto done;
        if(lstat(underlying,&st)||!S_ISDIR(st.st_mode)||!report("BEFORE_OWN_VIEW_DIRECTORY_REMOVE"))goto done;
        if(chown(PARENT,0,0))goto done;parent_changed=1;
        if(rmdir(underlying))goto done;
        if(chown(PARENT,1,0))goto done;parent_changed=0;ok=1;goto done;
    }
    if(matched!=1||!S_ISDIR(st.st_mode)||st.st_uid!=1||(st.st_mode&07777)!=0755)goto done;
    directory=opendir(target);if(!directory)goto done;int empty=1;
    while((entry=readdir(directory)))if(strcmp(entry->d_name,".")&&strcmp(entry->d_name,"..")){empty=0;break;}
    if(closedir(directory)||!empty)goto done;
    if(chown(target,0,0)||!report("OWN_VIEW_TARGET root_owned=1 empty_directory=1"))goto done;
    struct iovec iov[]={{"fstype",7},{"nullfs",7},{"from",5},{PFS_MOUNT,sizeof(PFS_MOUNT)},{"fspath",7},{target,strlen(target)+1}};
    if(!report("BEFORE_VIEW_MOUNT target=%s readonly=1 registered_title_mount_unchanged=1",target))goto done;
    errno=0;++mounts;int rc=nmount(iov,sizeof(iov)/sizeof(iov[0]),MNT_RDONLY),error=errno;
    if(!report("PFS_VIEW_MOUNT rc=%d errno=%d",rc,error)||rc||statfs(target,&fs)||strcmp(fs.f_fstypename,"nullfs")||strcmp(fs.f_mntonname,target)||strcmp(fs.f_mntfromname,PFS_MOUNT))goto done;
    ok=1;
done:
    if(parent_changed){if(chown(PARENT,1,0))ok=0;else parent_changed=0;}
    if(auth_changed){if(kernel_set_ucred_authid(getpid(),original_auth)||kernel_get_ucred_authid(getpid())!=original_auth)ok=0;else auth_changed=0;}
    if(!report("END nonce=%s success=%d cleanup=%d mounts=%d unmounts=%d parent_restored=%d auth_restored=%d GPU_calls=0",RECOVERY_NONCE,ok,cleanup,mounts,unmounts,!parent_changed,!auth_changed))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

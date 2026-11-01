/* SPDX-License-Identifier: GPL-3.0-or-later
 * Own a direct PFS mount until native file access has closed, then detach.
 * Filesystem layouts derive from ps5-sd-tool ef5df270 / garlic-worker e0cbe2d3.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <dlfcn.h>
#include <dirent.h>
#include <stdlib.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <time.h>
#include <limits.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#include "apr_direct_control.h"
#include "direct_supervisor_context.h"
#define PARENT "/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime"
typedef int(*init_fn)(void*);
typedef int(*format_fn)(void*,const char*,uint64_t,uint64_t,unsigned char*);
typedef int(*ppr_format_fn)(void*,const char*,uint64_t,uint64_t);
typedef int(*mount_fn)(void*,const char*,const char*,unsigned char*);
typedef int(*unmount_fn)(void*,const char*,int,int);
typedef int(*allocate_fn)(int,uint64_t,uint64_t,int);
static struct{uint64_t a;unsigned char bytes[256];uint64_t b;}opt;
static int initialize(init_fn fn){memset(&opt,0,sizeof(opt));opt.a=opt.b=GUARD;return fn&&!fn(opt.bytes)&&opt.a==GUARD&&opt.b==GUARD;}
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return(uint64_t)t.tv_sec*1000000+(uint64_t)t.tv_nsec/1000;}
static int context(unsigned phase){if(!boot(phase))return 0;for(size_t i=0;i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i)if(!service(expected_processes+i,phase))return 0;return boot(phase);}
static int one_native(pid_t pid){
    size_t n=sizeof(inventory.data);int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PROC,0};if(sysctl(mib,4,inventory.data,&n,NULL,0)||!n||n>sizeof(inventory.data)||n%sizeof(struct kinfo_proc))return 0;
    unsigned found=0,matched=0;for(size_t at=0;at<n;at+=sizeof(struct kinfo_proc)){struct kinfo_proc p;memcpy(&p,inventory.data+at,sizeof(p));if(p.ki_structsize!=sizeof(p)||!memchr(p.ki_comm,0,sizeof(p.ki_comm)))return 0;
        if(!strcmp(p.ki_comm,"eboot.bin")){++found;matched=p.ki_pid==pid&&p.ki_uid==1&&!p.ki_tracer&&!(p.ki_flag&P_TRACED)&&p.ki_start.tv_sec>=BOOT_SEC;}}
    return found==1&&matched;
}
static int control_access(int fd,struct apr_direct_control*c,unsigned expected,unsigned replacement,unsigned error){
    if(flock(fd,LOCK_EX))return 0;
    int ok=pread(fd,c,sizeof(*c),0)==sizeof(*c)&&c->magic==APR_DIRECT_MAGIC&&!memcmp(c->nonce,DIRECT_NONCE,32)&&!c->reserved;
    if(ok&&replacement){if(c->stage!=expected)ok=0;else{c->stage=replacement;c->error=error;ok=pwrite(fd,c,sizeof(*c),0)==sizeof(*c)&&!fsync(fd);}}
    if(flock(fd,LOCK_UN))ok=0;return ok;
}
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;
    int ok=0,status=-1,fd=-1,claimed=0,mounted=0,owned_image=0,owned_dir=0,parent_changed=0,auth_changed=0,detached=0;
    uint64_t original_auth=0;unsigned char key[32]={0};char target[384]={0},underlying[384]={0};struct stat st;struct statfs before,after;struct apr_direct_control control;
    init_fn unmount_init=NULL;unmount_fn unmount_api=NULL;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s pid=%d scope=direct_PFS_supervisor format=%s GPU_calls=0 APR_read_submits=0",RECOVERY_NONCE,getpid(),DIRECT_PPR?"PPR":"classic")||getuid()!=1||geteuid()!=0||!context(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    status=open(DIRECT_STATUS,O_RDWR|O_NOFOLLOW);if(status<0||fstat(status,&st)||!S_ISREG(st.st_mode)||st.st_uid!=1||st.st_size!=64||(st.st_mode&0777)!=0666||!control_access(status,&control,0,0,0)||control.stage!=APR_DIRECT_READY||!control.pid||control.pid>INT_MAX||!one_native((pid_t)control.pid))goto done;
    DIR*d=opendir("/mnt/sandbox");if(!d)goto done;struct dirent*e;unsigned count=0,matched=0;
    while((e=readdir(d))){
        if(++count>512||!memchr(e->d_name,0,sizeof(e->d_name))){matched=99;break;}if(strncmp(e->d_name,"PPSA99190_",10))continue;
        char program[384],candidate[384];if(snprintf(program,sizeof(program),"/mnt/sandbox/%s/app0/eboot.bin",e->d_name)>=(int)sizeof(program)||snprintf(candidate,sizeof(candidate),"/mnt/sandbox/%s/app0/qwen-runtime/%s",e->d_name,DIRECT_DIR_NAME)>=(int)sizeof(candidate)){matched=99;break;}
        if(!qwen_launch_digest_matches(program,files[0].bytes,files[0].hash))continue;
        if(lstat(candidate,&st)||!S_ISDIR(st.st_mode)||st.st_uid!=1||strlen(candidate)>=sizeof(before.f_mntonname)){matched=99;break;}strcpy(target,candidate);++matched;
    }
    if(closedir(d)||matched!=1||statfs(target,&before)||snprintf(underlying,sizeof(underlying),"%s/%s",PARENT,DIRECT_DIR_NAME)>=(int)sizeof(underlying))goto done;
    struct stat lower,upper,parent;
    if(lstat(PARENT,&parent)||!S_ISDIR(parent.st_mode)||parent.st_uid!=1||parent.st_gid||(parent.st_mode&07777)!=0755||
       lstat(underlying,&lower)||lstat(target,&upper)||!S_ISDIR(lower.st_mode)||lower.st_uid!=1||lower.st_ino!=upper.st_ino)goto done;
    intptr_t credential=kernel_get_proc_ucred(getpid());if(!credential||credential==kernel_get_proc_ucred(getppid()))goto done;
    for(size_t i=0;i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i)if(credential==kernel_get_proc_ucred(expected_processes[i].pid))goto done;
    void*module=dlopen("libSceFsInternalForVsh.sprx",RTLD_LAZY);if(!module)goto done;
    init_fn create_init=(init_fn)dlsym(module,DIRECT_PPR?"sceFsInitCreatePprPfsSaveDataOpt":"sceFsInitCreatePfsSaveDataOpt"),mount_init=(init_fn)dlsym(module,"sceFsInitMountSaveDataOpt");
    void*create=dlsym(module,DIRECT_PPR?"sceFsCreatePprPfsSaveDataImage":"sceFsCreatePfsSaveDataImage");mount_fn mount_api=(mount_fn)dlsym(module,"sceFsMountSaveData");
    unmount_init=(init_fn)dlsym(module,"sceFsInitUmountSaveDataOpt");unmount_api=(unmount_fn)dlsym(module,"sceFsUmountSaveData");allocate_fn allocate=(allocate_fn)dlsym(module,"sceFsUfsAllocateSaveData");
    if(!create_init||!mount_init||!create||!mount_api||!unmount_init||!unmount_api||!allocate||!control_access(status,&control,APR_DIRECT_READY,APR_DIRECT_BUSY,0))goto done;claimed=1;owned_dir=1;
    original_auth=kernel_get_ucred_authid(getpid());if(!original_auth||kernel_set_ucred_authid(getpid(),UINT64_C(0x4800000000000010)))goto done;auth_changed=1;
    if(kernel_get_ucred_authid(getpid())!=UINT64_C(0x4800000000000010)||kernel_get_proc_ucred(getpid())!=credential)goto done;
    struct{uint64_t a;unsigned char encrypted[96],plain[32];uint32_t result,pad;uint64_t b;}generated;memset(&generated,0,sizeof(generated));generated.a=generated.b=GUARD;
    fd=open("/dev/pfsmgr",O_RDWR);if(fd<0)goto done;
    if(ioctl(fd,UINT32_C(0x40845303),generated.encrypted)<0||ioctl(fd,UINT32_C(0xc0845302),generated.encrypted)<0||generated.a!=GUARD||generated.b!=GUARD||generated.pad)goto done;
    memcpy(key,generated.plain,sizeof(key));memset(&generated,0,sizeof(generated));if(close(fd))goto done;fd=-1;
    fd=open(DIRECT_IMAGE,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)goto done;owned_image=1;
    if(allocate(fd,UINT64_C(64)<<20,0,0)<0||fsync(fd))goto done;if(close(fd))goto done;fd=-1;
    if(!initialize(create_init)||!report("BEFORE_DIRECT_FORMAT capacity=67108864"))goto done;
    int rc=DIRECT_PPR?((ppr_format_fn)create)(opt.bytes,DIRECT_IMAGE,0,UINT64_C(64)<<20):((format_fn)create)(opt.bytes,DIRECT_IMAGE,0,UINT64_C(64)<<20,key);
    if(!report("DIRECT_FORMAT rc=%d canaries=%d",rc,opt.a==GUARD&&opt.b==GUARD)||rc<0||opt.a!=GUARD||opt.b!=GUARD||!control_access(status,&control,0,0,0)||control.stage!=APR_DIRECT_BUSY||!one_native((pid_t)control.pid))goto done;
    if(chown(target,0,0)||!initialize(mount_init))goto done;const char*budget="system";memcpy(opt.bytes+8,&budget,sizeof(budget));
    if(!report("BEFORE_DIRECT_MOUNT target=%s",target))goto done;rc=mount_api(opt.bytes,DIRECT_IMAGE,target,key);
    int sr=statfs(target,&after);mounted=!sr&&memcmp(&before.f_fsid,&after.f_fsid,sizeof(before.f_fsid));
    if(!report("DIRECT_MOUNT rc=%d observed=%d",rc,mounted)||rc<0||!mounted||opt.a!=GUARD||opt.b!=GUARD)goto done;
    char pending[512],file[512];if(snprintf(pending,sizeof(pending),"%s/control.pending",target)>=(int)sizeof(pending)||snprintf(file,sizeof(file),"%s/control.bin",target)>=(int)sizeof(file))goto done;
    unsigned char data[16384];for(unsigned i=0;i<sizeof(data);++i)data[i]=(unsigned char)(((i*17+29)^(i>>8))&255);
    fd=open(pending,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(fd<0||write(fd,data,sizeof(data))!=sizeof(data)||fsync(fd))goto done;if(close(fd))goto done;fd=-1;if(rename(pending,file))goto done;
    if(!control_access(status,&control,APR_DIRECT_BUSY,APR_DIRECT_MOUNTED,0)||!report("DIRECT_INPUT_READY bytes=16384"))goto done;
    uint64_t started=now(),deadline=started+30000000;int closed=0;
    for(unsigned poll=0;started&&poll<1500&&now()<deadline;++poll){if(!control_access(status,&control,0,0,0))break;if(control.stage==APR_DIRECT_NATIVE_CLOSED||control.stage==APR_DIRECT_ABORT){closed=1;break;}usleep(20000);}
    if(!report("DIRECT_NATIVE_CLOSED observed=%d",closed)||!closed)goto done;ok=1;
done:
    if(fd>=0){if(close(fd))ok=0;fd=-1;}
    if(mounted&&unmount_api&&unmount_init&&initialize(unmount_init)){
        int rc=unmount_api(opt.bytes,target,0,0);int sr=statfs(target,&after);
        int clear=rc>=0&&!sr&&!memcmp(&before.f_fsid,&after.f_fsid,sizeof(before.f_fsid));
        report("DIRECT_UNMOUNT rc=%d parent_restored=%d",rc,clear);if(clear)mounted=0;else ok=0;
    }
    if(claimed&&!mounted){
        if(owned_image){if(unlink(DIRECT_IMAGE))ok=0;else owned_image=0;}
        if(owned_dir){if(!chown(PARENT,0,0)){parent_changed=1;if(rmdir(underlying))ok=0;else owned_dir=0;}else ok=0;}
    }
    if(parent_changed){if(chown(PARENT,1,0))ok=0;else parent_changed=0;}
    if(auth_changed){if(kernel_set_ucred_authid(getpid(),original_auth)||kernel_get_ucred_authid(getpid())!=original_auth)ok=0;else auth_changed=0;}
    memset(key,0,sizeof(key));
    if(claimed&&!mounted&&!owned_image&&!owned_dir&&!auth_changed&&!parent_changed&&control_access(status,&control,0,0,0))detached=control_access(status,&control,control.stage,APR_DIRECT_DETACHED,ok?0:1);
    if(claimed&&!detached)ok=0;
    if(status>=0&&close(status))ok=0;
    if(!report("END nonce=%s success=%d mounted=%d owned_image=%d owned_dir=%d detached=%d auth_restored=%d parent_restored=%d GPU_calls=0 APR_read_submits=0",RECOVERY_NONCE,ok,mounted,owned_image,owned_dir,detached,!auth_changed,!parent_changed))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

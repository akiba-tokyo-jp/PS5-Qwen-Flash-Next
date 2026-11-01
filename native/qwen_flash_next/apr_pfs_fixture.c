/* SPDX-License-Identifier: GPL-3.0-or-later
 * An exclusive owned PFS fixture through original OS APIs. No game save data.
 * Public API layouts: c0w-ar/ps5-sd-tool ef5df270 and garlic-worker e0cbe2d3.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <dlfcn.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#include "pfs_fixture_context.h"
#define PARENT "/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime"
#define IMAGE_BYTES (UINT64_C(64)<<20)
static const uint64_t mark=UINT64_C(0xe45d80317ac5952a);
typedef int(*init_fn)(void*);
/* Classic API: offset, capacity, generated key. The PPR creator uses a
 * different four-argument image format with offset/capacity and no key.
 */
typedef int(*format_fn)(void*,const char*,uint64_t,uint64_t,unsigned char*);
typedef int(*mount_fn)(void*,const char*,const char*,unsigned char*);
typedef int(*unmount_fn)(void*,const char*,int,int);
typedef int(*allocate_fn)(int,uint64_t,uint64_t,int);
static struct{uint64_t a;unsigned char bytes[256];uint64_t b;} opt;
static int initialize(init_fn fn){memset(&opt,0,sizeof(opt));opt.a=opt.b=mark;return fn&&!fn(opt.bytes)&&opt.a==mark&&opt.b==mark;}
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;
    int ok=0,mounted=0,parent_changed=0,owned_dir=0,owned_image=0,fd=-1,auth_changed=0;
    uint64_t original_auth=0;struct stat st,old_parent;struct statfs parent_fs,active_fs;unsigned char key[32]={0};
    unmount_fn unmount_api=NULL;init_fn unmount_init=NULL;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s pid=%d ppid=%d scope=PFS_fixture action=%d GPU_calls=0 title_launches=0",RECOVERY_NONCE,getpid(),getppid(),PFS_ACTION)||getuid()!=1||geteuid()!=0||!boot(1)||!idle(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    if(lstat(PARENT,&old_parent)||!S_ISDIR(old_parent.st_mode)||old_parent.st_uid!=1||old_parent.st_gid||(old_parent.st_mode&07777)!=0755||statfs(PARENT,&parent_fs))goto done;
    if(!report("PFS_PATHS mount_bytes=%u mount_field_bytes=%u",(unsigned)strlen(PFS_MOUNT),(unsigned)sizeof(parent_fs.f_mntonname))||strlen(PFS_MOUNT)>=sizeof(parent_fs.f_mntonname))goto done;
    void*module=dlopen("libSceFsInternalForVsh.sprx",RTLD_LAZY);if(!report("FS_MODULE available=%d",module!=NULL)||!module)goto done;
    init_fn create_init=(init_fn)dlsym(module,"sceFsInitCreatePfsSaveDataOpt"),mount_init=(init_fn)dlsym(module,"sceFsInitMountSaveDataOpt");
    unmount_init=(init_fn)dlsym(module,"sceFsInitUmountSaveDataOpt");
    format_fn create=(format_fn)dlsym(module,"sceFsCreatePfsSaveDataImage");mount_fn mount_api=(mount_fn)dlsym(module,"sceFsMountSaveData");
    unmount_api=(unmount_fn)dlsym(module,"sceFsUmountSaveData");
    allocate_fn allocate=(allocate_fn)dlsym(module,"sceFsUfsAllocateSaveData");
    if(!create_init||!mount_init||!unmount_init||!create||!mount_api||!unmount_api||!allocate)goto done;
    original_auth=kernel_get_ucred_authid(getpid());if(!original_auth||!report("BEFORE_OWN_AUTH target=filesystem_API owner_pid=%d",getpid()))goto done;
    if(kernel_set_ucred_authid(getpid(),UINT64_C(0x4800000000000010)))goto done;auth_changed=1;
    if(kernel_get_ucred_authid(getpid())!=UINT64_C(0x4800000000000010))goto done;
    if(PFS_ACTION==2){
        if(statfs(PFS_MOUNT,&active_fs)||!strcmp(active_fs.f_fstypename,"nullfs")||strcmp(active_fs.f_mntonname,PFS_MOUNT)||
           !memcmp(&active_fs.f_fsid,&parent_fs.f_fsid,sizeof(active_fs.f_fsid)))goto done;
        mounted=1;owned_image=1;owned_dir=1;
        if(!initialize(unmount_init)||!report("BEFORE_OWN_UNMOUNT"))goto done;
        int rc=unmount_api(opt.bytes,PFS_MOUNT,0,0);if(!report("OWN_UNMOUNT rc=%d",rc)||rc<0)goto done;mounted=0;
        if(statfs(PFS_MOUNT,&active_fs)||memcmp(&active_fs.f_fsid,&parent_fs.f_fsid,sizeof(active_fs.f_fsid)))goto done;
        if(unlink(PFS_IMAGE))goto done;owned_image=0;
        if(chown(PARENT,0,0))goto done;parent_changed=1;
        if(rmdir(PFS_MOUNT))goto done;owned_dir=0;ok=1;goto done;
    }
    errno=0;if(!lstat(PFS_IMAGE,&st)||errno!=ENOENT)goto done;errno=0;if(!lstat(PFS_MOUNT,&st)||errno!=ENOENT)goto done;
    struct{uint64_t a;unsigned char encrypted[96],plain[32];uint32_t result,pad;uint64_t b;} generated;
    memset(&generated,0,sizeof(generated));generated.a=generated.b=mark;
    fd=open("/dev/pfsmgr",O_RDWR);if(fd<0)goto done;
    if(!report("BEFORE_OWN_KEY_GENERATE bytes=132"))goto done;
    int key_rc=ioctl(fd,UINT32_C(0x40845303),generated.encrypted),key_error=errno;
    if(!report("OWN_KEY_GENERATE rc=%d errno=%d result=%u canaries=%d",key_rc,key_error,generated.result,generated.a==mark&&generated.b==mark&&!generated.pad)||key_rc<0||generated.a!=mark||generated.b!=mark||generated.pad)goto done;
    errno=0;key_rc=ioctl(fd,UINT32_C(0xc0845302),generated.encrypted);key_error=errno;
    if(!report("OWN_KEY_RESOLVE rc=%d errno=%d result=%u canaries=%d",key_rc,key_error,generated.result,generated.a==mark&&generated.b==mark&&!generated.pad)||key_rc<0||generated.a!=mark||generated.b!=mark||generated.pad)goto done;
    memcpy(key,generated.plain,sizeof(key));memset(&generated,0,sizeof(generated));if(close(fd))goto done;fd=-1;
    if(chown(PARENT,0,0))goto done;parent_changed=1;
    if(mkdir(PFS_MOUNT,0755))goto done;owned_dir=1;
    if(chown(PARENT,1,0))goto done;parent_changed=0;
    fd=open(PFS_IMAGE,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)goto done;owned_image=1;
    if(!report("BEFORE_OWN_PFS_ALLOCATE bytes=%llu",(unsigned long long)IMAGE_BYTES))goto done;
    int allocate_rc=allocate(fd,IMAGE_BYTES,0,0),allocate_error=errno;
    if(!report("OWN_PFS_ALLOCATE rc=%d errno=%d",allocate_rc,allocate_error)||allocate_rc<0||fsync(fd))goto done;
    if(close(fd))goto done;fd=-1;
    if(!initialize(create_init))goto done;
    if(!report("BEFORE_OWN_PFS_FORMAT bytes=%llu",(unsigned long long)IMAGE_BYTES))goto done;
    int rc=create(opt.bytes,PFS_IMAGE,0,IMAGE_BYTES,key);
    if(!report("OWN_PFS_FORMAT rc=%d canaries=%d",rc,opt.a==mark&&opt.b==mark)||rc<0||opt.a!=mark||opt.b!=mark)goto done;
    errno=0;int image_rc=lstat(PFS_IMAGE,&st),image_error=errno;
    if(!report("OWN_PFS_IMAGE rc=%d errno=%d bytes=%llu regular=%d requested_bytes=%llu",image_rc,image_error,
        (unsigned long long)(image_rc?0:st.st_size),!image_rc&&S_ISREG(st.st_mode),(unsigned long long)IMAGE_BYTES)||
        image_rc||!S_ISREG(st.st_mode)||st.st_size<=0)goto done;
    if(!initialize(mount_init))goto done;
    const char*budget="system";memcpy(opt.bytes+8,&budget,sizeof(budget));
    if(!report("BEFORE_OWN_PFS_MOUNT"))goto done;rc=mount_api(opt.bytes,PFS_IMAGE,PFS_MOUNT,key);
    int fs_rc=statfs(PFS_MOUNT,&active_fs);mounted=!fs_rc&&memcmp(&active_fs.f_fsid,&parent_fs.f_fsid,sizeof(active_fs.f_fsid));
    if(!report("OWN_PFS_MOUNT rc=%d observed=%d canaries=%d",rc,mounted,opt.a==mark&&opt.b==mark)||rc<0||!mounted||opt.a!=mark||opt.b!=mark)goto done;
    if(!report("OWN_PFS_FILESYSTEM name=%s type=%u target=%s",active_fs.f_fstypename,active_fs.f_type,active_fs.f_mntonname))goto done;
    char file[384];if(snprintf(file,sizeof(file),"%s/control.bin",PFS_MOUNT)>=(int)sizeof(file))goto done;
    unsigned char data[16384],readback[16384];for(unsigned i=0;i<sizeof(data);++i)data[i]=(unsigned char)(((i*17+29)^(i>>8))&255);
    fd=open(file,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(fd<0)goto done;
    if(write(fd,data,sizeof(data))!=sizeof(data)||fsync(fd)||pread(fd,readback,sizeof(readback),0)!=sizeof(readback)||memcmp(data,readback,sizeof(data)))goto done;
    if(close(fd))goto done;fd=-1;
    if(!report("OWN_PFS_CONTROL bytes=16384 exact=1"))goto done;
    ok=1;
done:
    if(fd>=0){if(close(fd))ok=0;fd=-1;}
    if(PFS_ACTION==1&&!ok&&mounted&&unmount_api&&unmount_init&&initialize(unmount_init)){
        int rc=unmount_api(opt.bytes,PFS_MOUNT,0,0);report("ERROR_OWN_UNMOUNT rc=%d",rc);
        if(rc>=0&&!statfs(PFS_MOUNT,&active_fs)&&!memcmp(&active_fs.f_fsid,&parent_fs.f_fsid,sizeof(active_fs.f_fsid)))mounted=0;
    }
    if(PFS_ACTION==1&&!ok&&!mounted){
        if(owned_image&&!unlink(PFS_IMAGE))owned_image=0;
        if(owned_dir){if(!parent_changed&&!chown(PARENT,0,0))parent_changed=1;if(parent_changed&&!rmdir(PFS_MOUNT))owned_dir=0;}
    }
    if(parent_changed){if(chown(PARENT,1,0))ok=0;else parent_changed=0;}
    if(auth_changed){if(kernel_set_ucred_authid(getpid(),original_auth)||kernel_get_ucred_authid(getpid())!=original_auth)ok=0;else auth_changed=0;}
    memset(key,0,sizeof(key));
    if(lstat(PARENT,&st)||st.st_uid!=1||st.st_gid||(st.st_mode&07777)!=0755||auth_changed||parent_changed)ok=0;
    if(!report("END nonce=%s success=%d action=%d mounted=%d owned_image=%d owned_dir=%d auth_restored=%d parent_restored=%d GPU_calls=0 title_launches=0",RECOVERY_NONCE,ok,PFS_ACTION,mounted,owned_image,owned_dir,!auth_changed,!parent_changed))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

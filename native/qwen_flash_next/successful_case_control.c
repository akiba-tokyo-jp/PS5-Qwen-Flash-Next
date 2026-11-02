/* SPDX-License-Identifier: GPL-3.0-or-later
 * Ordinary case publication/launch/CPU-only close, using the previously
 * successful registered-title ABI. A build permits exactly one operation.
 * No initialization, mount change, Unix signal, injection or GPU command.
 */
#include "controller.c"
#include "case_context.h"

static int acquire_directory(const char *path,unsigned expected_mode,unsigned *owner,int *held){
    struct stat s;
    if(lstat(path,&s)||!S_ISDIR(s.st_mode)||s.st_uid>1||s.st_gid||(s.st_mode&07777)!=expected_mode)return 0;
    *owner=s.st_uid;
    if(*owner&&chown(path,0,0))return 0;
    *held=1;
    return !lstat(path,&s)&&s.st_uid==0&&s.st_gid==0&&(s.st_mode&07777)==expected_mode;
}
static int release_directory(const char *path,unsigned expected_mode,unsigned owner){
    if(owner&&chown(path,owner,0))return 0;
    struct stat s;return !lstat(path,&s)&&S_ISDIR(s.st_mode)&&s.st_uid==owner&&!s.st_gid&&(s.st_mode&07777)==expected_mode;
}
static int own_title_mount(void){
    struct statfs s;return !statfs(MOUNT,&s)&&!strcmp(s.f_fstypename,"nullfs")&&
        !strcmp(s.f_mntonname,MOUNT)&&!strcmp(s.f_mntfromname,NEW_STAGE)&&s.f_bsize>0&&s.f_bavail>0&&
        report("OWNED_TITLE_CAPACITY block_bytes=%llu available_blocks=%llu",
            (unsigned long long)s.f_bsize,(unsigned long long)s.f_bavail);
}
#if CASE_OPERATION == 8
int split_report_line(const char*line){return report("%s",line);}
int split_open_journal(void){return journal>=0&&healthy;}
int split_close_journal(void){return healthy;}
int split_context(unsigned phase){(void)phase;return live_context()&&idle();}
int split_headroom(void){return qwen_launch_headroom(NULL);}
uint64_t split_now_ns(void){return qwen_launch_now(NULL);}
#endif

int main(int argc,char **argv){
    if(argc!=2||strcmp(argv[1],CASE_ARGUMENT))return 2;
    journal=open(CASE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(journal<0)return 3;
    int success=0,calls=0,app_id=-1;
    if(!report("BEGIN pid=%d code=ps5-qwen-successful-case-v1 operation=%s GPU_calls=0 initializer_requests=0 mount_calls=0",getpid(),CASE_ARGUMENT)||
       constructors!=1||getuid()!=1||geteuid()!=0||!live_context()||!own_title_mount())goto done;
#if CASE_OPERATION == 1
    if(!idle()||registration_state()!=1||!registered_metadata_valid()||!old_files_valid()||!pending_valid()||!claim("publish"))goto done;
    unsigned title_owner=0,runtime_owner=0;int title_acquired=0,runtime_acquired=0;
    int title_ready=acquire_directory(NEW_STAGE,0777,&title_owner,&title_acquired);
    int runtime_ready=title_ready&&acquire_directory(NEW_STAGE "/qwen-runtime",0755,&runtime_owner,&runtime_acquired);
    if(title_ready&&runtime_ready){
        success=1;
        for(unsigned i=0;i<CASE_PUBLICATION_COUNT;++i){
            int fd=open(case_pending[i],O_RDONLY|O_NOFOLLOW);
            if(fd<0){success=0;break;}
            const unsigned expected_mode=!strcmp(case_targets[i],NEW_STAGE "/eboot.bin")?0755:0644;
            int mode=fchmod(fd,expected_mode),closed=close(fd);
            if(mode||closed||!report("BEFORE owned_atomic_publication index=%u",i)){success=0;break;}
            ++calls;int rc=rename(case_pending[i],case_targets[i]);
            if(!report("RETURN owned_atomic_publication index=%u rc=%d errno=%d",i,rc,errno)||rc){success=0;break;}
        }
    }
    if(runtime_acquired&&!release_directory(NEW_STAGE "/qwen-runtime",0755,runtime_owner))success=0;
    if(title_acquired&&!release_directory(NEW_STAGE,0777,title_owner))success=0;
    if(!success||!new_files_valid()||!new_mounted_valid()||!live_context()||!idle())success=0;
    if(success){
        struct stat s;if(lstat(NEW_STAGE "/eboot.bin",&s)||!S_ISREG(s.st_mode)||(s.st_mode&07777)!=0755)success=0;
        else if(!report("CURRENT_SELF_ID inode=%llu bytes=%llu mode=%u uid=%u gid=%u mtime_sec=%lld mtime_nsec=%lld ctime_sec=%lld ctime_nsec=%lld",
            (unsigned long long)s.st_ino,(unsigned long long)s.st_size,(unsigned)s.st_mode,(unsigned)s.st_uid,(unsigned)s.st_gid,
            (long long)s.st_mtim.tv_sec,(long long)s.st_mtim.tv_nsec,(long long)s.st_ctim.tv_sec,(long long)s.st_ctim.tv_nsec))success=0;
    }
#elif CASE_OPERATION == 2
    if(!idle()||registration_state()!=1||!registered_metadata_valid()||!new_files_valid()||!new_mounted_valid()||!claim("launch"))goto done;
    int rc=sceUserServiceInitialize(NULL);
    if(!report("RETURN UserServiceInitialize rc=%d",rc)||rc)goto done;
    struct {uint64_t pre[2];launch_context value;uint64_t post[2];} l=
        {{UINT64_C(0xa9ac2e87a9ac2e87),UINT64_C(0xa9ac2e87a9ac2e87)},{0},
         {UINT64_C(0xa9ac2e87a9ac2e87),UINT64_C(0xa9ac2e87a9ac2e87)}};
    l.value.size=sizeof(l.value);rc=sceUserServiceGetForegroundUser(&l.value.user_id);
    int intact=l.pre[0]==UINT64_C(0xa9ac2e87a9ac2e87)&&l.pre[1]==l.pre[0]&&l.post[0]==l.pre[0]&&l.post[1]==l.pre[0];
    if(!report("RETURN ForegroundUser rc=%d canaries=%d",rc,intact)||rc||!intact||!live_context()||!idle()){
        sceUserServiceTerminate();goto done;
    }
    if(!report("BEFORE LaunchApp normal_registered_API=1 maximum_calls=1")){sceUserServiceTerminate();goto done;}
    char *child_args[]={NULL};calls=1;rc=sceSystemServiceLaunchApp(TITLE,child_args,&l.value);
    intact=l.pre[0]==UINT64_C(0xa9ac2e87a9ac2e87)&&l.pre[1]==l.pre[0]&&l.post[0]==l.pre[0]&&l.post[1]==l.pre[0];
    success=report("RETURN LaunchApp rc=%d canaries=%d",rc,intact)&&rc>=0&&intact;
    sceUserServiceTerminate();
    if(success){
        for(unsigned i=0;i<20;++i){app_id=sceSystemServiceGetAppIdOfRunningBigApp();if(app_id>0)break;usleep(250000);}
        success=app_id>0;
    }
#elif CASE_OPERATION == 3
    /* The host binds positive CPU-only completion or complete retirement of
     * every model/source/device owner, two reports, and the exact native PID. */
    if(!case_CPU_close_proof()||!claim("close"))goto done;
    app_id=sceSystemServiceGetAppIdOfRunningBigApp();
    if(app_id!=CASE_CLOSE_APP_ID||!report("BEFORE ordinary_OS_close app_id=%d maximum_calls=1 positive_owner_completion_bound=1",app_id))goto done;
    calls=1;int rc=sceSystemServiceKillApp(app_id,-1,0,0);
    success=report("RETURN ordinary_OS_close rc=%d",rc)&&rc==0;
#elif CASE_OPERATION == 4
    if(!idle()||!new_files_valid()||!new_mounted_valid())goto done;
    const char*directories[]={NEW_STAGE,NEW_STAGE "/qwen-runtime"};success=1;
    for(unsigned i=0;i<2;++i){
        struct stat s;if(lstat(directories[i],&s)||!S_ISDIR(s.st_mode)){success=0;break;}
        if(!report("DIRECTORY index=%u uid=%u gid=%u mode=%u",i,(unsigned)s.st_uid,(unsigned)s.st_gid,(unsigned)(s.st_mode&07777)))success=0;
    }
    struct stat image;if(lstat(NEW_STAGE "/eboot.bin",&image)||!report("SELF_MODE mode=%u uid=%u gid=%u",
        (unsigned)(image.st_mode&07777),(unsigned)image.st_uid,(unsigned)image.st_gid))success=0;
#elif CASE_OPERATION == 5
    success=idle()&&new_files_valid()&&new_mounted_valid()&&case_model_readmission();
#elif CASE_OPERATION == 6
    struct timespec now;if(!idle()||clock_gettime(CLOCK_REALTIME,&now)||now.tv_sec<=0||now.tv_nsec<0||now.tv_nsec>=1000000000)goto done;
    success=report("CURRENT_CLOCK seconds=%lld nanoseconds=%lld",(long long)now.tv_sec,(long long)now.tv_nsec);
    const char*vm_names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","vm.stats.vm0.v_free_target"};
    for(unsigned i=0;i<4;++i){uint32_t value=0;size_t n=sizeof(value);if(sysctlbyname(vm_names[i],&value,&n,NULL,0)||n!=sizeof(value)||!report("CURRENT_VM index=%u pages=%u",i,value))success=0;}
#elif CASE_OPERATION == 7
    if(!idle())goto done;success=1;
    for(unsigned i=0;i<CASE_DEPENDENCY_COUNT;++i){
        struct stat s={0};errno=0;int rc=lstat(case_dependencies[i],&s),saved=errno;
        if(!report("DEPENDENCY index=%u lstat_rc=%d errno=%d device=%llu inode=%llu mode=%u uid=%u gid=%u bytes=%llu mtime_sec=%lld mtime_nsec=%lld ctime_sec=%lld ctime_nsec=%lld",
            i,rc,saved,(unsigned long long)s.st_dev,(unsigned long long)s.st_ino,(unsigned)s.st_mode,(unsigned)s.st_uid,(unsigned)s.st_gid,
            (unsigned long long)s.st_size,(long long)s.st_mtim.tv_sec,(long long)s.st_mtim.tv_nsec,(long long)s.st_ctim.tv_sec,(long long)s.st_ctim.tv_nsec))success=0;
    }
#elif CASE_OPERATION == 8
    if(!idle()||!new_files_valid()||!new_mounted_valid()||!claim("restore-bundle"))goto done;
    calls=1;success=qwen_bundle_payload_main(1,argv)==0;
    if(!new_files_valid()||!new_mounted_valid()||!live_context()||!idle())success=0;
#elif CASE_OPERATION == 9
    if(!idle()||!new_files_valid()||!new_mounted_valid()||!claim("finalize-bundle"))goto done;
    success=case_finalize_bundle(&calls)&&new_files_valid()&&new_mounted_valid()&&live_context()&&idle();
#elif CASE_OPERATION == 10
    if(!idle()||!new_files_valid()||!new_mounted_valid()||!claim("seal-shared-Q4"))goto done;
    success=case_seal_shared_Q4(&calls)&&new_files_valid()&&new_mounted_valid()&&live_context()&&idle();
#elif CASE_OPERATION == 11
    if(!idle()||!new_files_valid()||!new_mounted_valid()||!claim("export-activation"))goto done;
    success=case_export_activation(&calls)&&new_files_valid()&&new_mounted_valid()&&live_context()&&idle();
#elif CASE_OPERATION == 12
    if(!idle()||!new_files_valid()||!new_mounted_valid()||!claim("retire-activation"))goto done;
    success=case_retire_activation(&calls)&&new_files_valid()&&new_mounted_valid()&&live_context()&&idle();
#elif CASE_OPERATION == 13
    if(!idle()||!new_files_valid()||!new_mounted_valid()||!claim("publish-component"))goto done;
    success=case_publish_component(&calls)&&new_files_valid()&&new_mounted_valid()&&live_context()&&idle();
#else
#error A single scoped operation must be selected
#endif
done:
    report("END success=%d operation_calls=%d app_id=%d log_healthy=%d GPU_calls=0 initializer_requests=0 mount_calls=0",success,calls,app_id,healthy);
    int status=success&&healthy?0:1;if(close(journal))status=1;return status;
}

/* SPDX-License-Identifier: GPL-3.0-or-later
 * Once-only ordinary launch of a verified GPU-free title diagnostic.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <stddef.h>
#include <sys/stat.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
typedef struct {uint32_t size,user_id,options;uint64_t crash_report;uint32_t flags;} launch_context;
_Static_assert(sizeof(launch_context)==32&&offsetof(launch_context,crash_report)==16,"Qualified launch ABI");
int sceUserServiceInitialize(void*);
int sceUserServiceGetForegroundUser(uint32_t*);
void sceUserServiceTerminate(void);
int sceSystemServiceLaunchApp(const char*,char**,launch_context*);
static int context(unsigned phase){if(!boot(phase)||!idle(phase))return 0;for(size_t i=0;i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i)if(!service(expected_processes+i,phase))return 0;return boot(phase);}
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;int ok=0,calls=0,started=0;
    if(!report("BEGIN nonce=%s pid=%d GPU_calls=0 ordinary_launch_only=1",RECOVERY_NONCE,getpid())||getuid()!=1||geteuid()!=0||!context(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    int rc=sceUserServiceInitialize(NULL);if(!report("USER_SERVICE init_rc=%d",rc)||rc)goto done;started=1;
    struct{uint64_t a;launch_context value;uint64_t b;} launch={GUARD,{0},GUARD};launch.value.size=sizeof(launch.value);
    rc=sceUserServiceGetForegroundUser(&launch.value.user_id);
    if(!report("FOREGROUND rc=%d canaries=%d",rc,launch.a==GUARD&&launch.b==GUARD)||rc||launch.a!=GUARD||launch.b!=GUARD||!context(2))goto done;
    if(!report("BEFORE_LAUNCH title=PPSA99190 attempt=1 GPU_calls=0"))goto done;
    char*arguments[]={NULL};calls=1;rc=sceSystemServiceLaunchApp("PPSA99190",arguments,&launch.value);
    ok=rc>=0&&launch.a==GUARD&&launch.b==GUARD;
    if(!report("LAUNCH_RETURN rc=%d canaries=%d",rc,launch.a==GUARD&&launch.b==GUARD))ok=0;
done:
    if(started)sceUserServiceTerminate();
    if(!report("END nonce=%s success=%d launch_calls=%d GPU_calls=0 no_retry=1",RECOVERY_NONCE,ok,calls))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

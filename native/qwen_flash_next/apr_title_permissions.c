/* SPDX-License-Identifier: GPL-3.0-or-later
 * Temporarily hand this application's one data directory to the transfer owner.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <sys/stat.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#define DATA_DIRECTORY "/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime"
static int context(void){if(!boot(1)||!idle(1))return 0;for(size_t i=0;i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i)if(!service(expected_processes+i,1))return 0;return boot(1);}
int main(int argc,char**argv){
    if(argc!=2||(strcmp(argv[1],"prepare")&&strcmp(argv[1],"finalize")&&strcmp(argv[1],"prepare-cleanup")&&strcmp(argv[1],"finalize-cleanup")))return 2;
    char path[320];snprintf(path,sizeof(path),"%s-%s",RECOVERY_LOG,argv[1]);journal=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    int ok=0,prepare=!strncmp(argv[1],"prepare",7);
    if(!report("BEGIN nonce=%s pid=%d mode=%s GPU_calls=0 title_launches=0",RECOVERY_NONCE,getpid(),argv[1])||getuid()!=1||geteuid()!=0||!context())goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    struct stat st;if(lstat(DATA_DIRECTORY,&st)||!S_ISDIR(st.st_mode)||st.st_uid!=(prepare?1u:0u)||st.st_gid||(st.st_mode&07777)!=0755)goto done;
    if(!report("BEFORE_DIRECTORY_OWNER old=%u new=%u mode=0755",st.st_uid,prepare?0u:1u))goto done;
    if(chown(DATA_DIRECTORY,prepare?0:1,0)||lstat(DATA_DIRECTORY,&st)||st.st_uid!=(prepare?0u:1u)||st.st_gid||(st.st_mode&07777)!=0755)goto done;
    ok=1;
done:
    if(!report("END nonce=%s success=%d mode=%s GPU_calls=0 title_launches=0",RECOVERY_NONCE,ok,argv[1]))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

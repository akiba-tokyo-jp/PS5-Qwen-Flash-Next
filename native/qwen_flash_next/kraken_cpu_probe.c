/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded actual-source CPU Kraken comparison, without GPU/model work.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <sys/stat.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#include "kraken_probe_inputs.h"
int qwen_kraken_log(const char*line){return report("%s",line);}
int qwen_run_kraken_benchmark(void);
int main(int argc,char**argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;int ok=0;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s pid=%d ppid=%d scope=CPU_Kraken_actual_Experts GPU_calls=0 title_launches=0",RECOVERY_NONCE,getpid(),getppid())||getuid()!=1||geteuid()!=0||!boot(1)||!idle(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    if(!qwen_launch_digest_matches(KRAKEN_SOURCE,KRAKEN_SOURCE_BYTES,KRAKEN_SOURCE_SHA256)||!qwen_run_kraken_benchmark()||!boot(2)||!idle(2))goto done;ok=1;
done:
    if(!report("END nonce=%s success=%d GPU_calls=0 title_launches=0 APR_calls=0 hardware_decoder=0",RECOVERY_NONCE,ok))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

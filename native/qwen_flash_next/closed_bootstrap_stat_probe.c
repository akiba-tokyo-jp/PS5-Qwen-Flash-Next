/* SPDX-License-Identifier: GPL-3.0-or-later
 * Observe one positively closed, fully captured startup journal. No mutation.
 */
#define MOSS_RUNTIME_PREP 1
#include "direct-controller.c"
#include "preservation_context.h"
#include "bootstrap_stat_context.h"
int main(int argc,char **argv) {
    (void)argv;int ok=0;struct stat value;
    if(argc!=0&&argc!=1)return 2;
    journal=open(LAUNCH_LOG_PREFIX "-CPU.log",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s CPU_only=1 title_launches=0 GPU_calls=0",PRESERVATION_NONCE)||
       constructors!=1||getuid()!=1||geteuid()!=0||!live_context()||!idle()||!no_native_owner())goto done;
    if(sizeof(preservation_sources)/sizeof(preservation_sources[0])!=1)goto done;
    const struct preservation_source *source=preservation_sources;
    if(!qwen_launch_digest_matches(source->path,(size_t)source->bytes,source->sha256))goto done;
    const int fd=open(source->path,O_RDONLY|O_NOFOLLOW|O_DIRECT);if(fd<0)goto done;
    const int observed=!fstat(fd,&value)&&S_ISREG(value.st_mode)&&value.st_size==(off_t)source->bytes;
    const int closed=close(fd)==0;if(!observed||!closed)goto done;
    if(!report("CLOSED_BOOTSTRAP_STAT mtime_sec=%lld mtime_nsec=%ld ctime_sec=%lld bytes=%lld current_boot_sec=%lld current_launch_sec=%lld predates_current_boot=%d predates_current_launch=%d",
        (long long)value.st_mtim.tv_sec,value.st_mtim.tv_nsec,(long long)value.st_ctim.tv_sec,(long long)value.st_size,
        (long long)BOOTSTRAP_CURRENT_BOOT_SECONDS,(long long)BOOTSTRAP_CURRENT_LAUNCH_SECONDS,
        value.st_mtim.tv_sec<BOOTSTRAP_CURRENT_BOOT_SECONDS,value.st_mtim.tv_sec<BOOTSTRAP_CURRENT_LAUNCH_SECONDS))goto done;
    if(!live_context()||!idle()||!no_native_owner())goto done;ok=1;
done:
    if(!report("END success=%d nonce=%s readonly_metadata_and_whole_integrity=1 title_launches=0 GPU_calls=0 automatic_retry=0",ok,PRESERVATION_NONCE))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

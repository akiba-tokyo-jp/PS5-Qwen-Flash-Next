/* SPDX-License-Identifier: MIT
 * Required integrity for already captured, positively closed owned artifacts.
 * The included qualified controller retains all boot/service/title guards.
 */
#define MOSS_RUNTIME_PREP 1
#include "direct-controller.c"
#include "preservation_context.h"

int main(int argc,char **argv) {
    (void)argv;int ok=0;unsigned complete=0;
    if(argc!=0&&argc!=1)return 2;
    journal=open(LAUNCH_LOG_PREFIX "-CPU.log",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(journal<0)return 3;
    if(!report("BEGIN nonce=%s CPU_only=1 title_launches=0 GPU_calls=0",PRESERVATION_NONCE)||
       constructors!=1||getuid()!=1||geteuid()!=0||!live_context()||!idle()||!no_native_owner())goto done;
    const uint64_t begun=qwen_launch_now(NULL);
    if(!begun)goto done;
    for(unsigned i=0;i<sizeof(preservation_sources)/sizeof(preservation_sources[0]);++i) {
        const struct preservation_source *source=&preservation_sources[i];
        uint32_t before=0,after=0;size_t count=4;
        const uint64_t now=qwen_launch_now(NULL);
        if(!now||now<begun||now-begun>UINT64_C(20000000000)||
           sysctlbyname("vm.stats.vm0.v_free_count",&before,&count,NULL,0)||count!=4)goto done;
        if(!report("FILE_BEFORE index=%u",i)||
           !qwen_launch_digest_matches(source->path,(size_t)source->bytes,source->sha256))goto done;
        count=4;
        if(sysctlbyname("vm.stats.vm0.v_free_count",&after,&count,NULL,0)||count!=4||
           !report("FILE_COMPLETE index=%u free_before=%u free_after=%u whole_SHA256_identity_EOF=1",i,before,after))goto done;
        ++complete;
    }
    if(!live_context()||!idle()||!no_native_owner())goto done;
    ok=1;
done:
    if(!report("END success=%d nonce=%s files_completed=%u title_launches=0 GPU_calls=0 no_retry=1",ok,PRESERVATION_NONCE,complete))ok=0;
    if(close(journal))ok=0;
    return ok?0:1;
}

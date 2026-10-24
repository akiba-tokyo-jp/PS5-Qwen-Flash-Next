/* SPDX-License-Identifier: MIT
 * Bounded CPU hash timing on synthetic in-memory bytes. No model, file payload,
 * mapping, GPU, title or process-credential operation. The unchanged SHA256
 * provider is compiled separately from the pinned engine's public-domain source.
 */
#ifdef QWEN_HASH_PROBE_HOST_STUBS
#include "model_hash_probe_stubs.h"
#else
#include <sys/types.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#endif
#include "hash/sha256/sha256.h"
#include "model_hash_probe_context.h"

#define PROBE_BYTES (1u<<20)
#define PROBE_MAX_PASSES 512u
#define PROBE_TARGET_NS UINT64_C(10000000000)
#define PROBE_DEADLINE_NS UINT64_C(15000000000)
#define PROBE_CANARY UINT64_C(0x7631e8691c4f2319)
static unsigned char probe_input[PROBE_BYTES];
typedef struct { uint64_t bytes,elapsed_ns;unsigned passes; } HashProbeResult;
typedef struct { uint64_t before;struct timespec value;uint64_t after; } HashProbeClock;

static int observe_time(uint64_t *result) {
    HashProbeClock clock;memset(&clock,0,sizeof(clock));clock.before=clock.after=PROBE_CANARY;
    if(clock_gettime(CLOCK_MONOTONIC,&clock.value)||clock.before!=PROBE_CANARY||clock.after!=PROBE_CANARY||
       clock.value.tv_sec<0||clock.value.tv_nsec<0||clock.value.tv_nsec>=1000000000||
       (uint64_t)clock.value.tv_sec>(UINT64_MAX-UINT64_C(999999999))/UINT64_C(1000000000))return 0;
    *result=(uint64_t)clock.value.tv_sec*UINT64_C(1000000000)+(uint64_t)clock.value.tv_nsec;
    return 1;
}

static int hash_probe(HashProbeResult *result,const char *expected) {
    memset(result,0,sizeof(*result));
    if(!expected||strlen(expected)!=64||strspn(expected,"0123456789abcdef")!=64)return 0;
    for(unsigned i=0;i<PROBE_BYTES;++i)probe_input[i]=(unsigned char)i;
    uint64_t started=0,previous=0,now=0;
    if(!observe_time(&started))return 0;
    previous=started;
    for(unsigned i=0;i<PROBE_MAX_PASSES;++i){
        if(!observe_time(&now)||now<previous||now<started)return 0;
        if(now-started>PROBE_DEADLINE_NS)return 0;
        if(i&&now-started>=PROBE_TARGET_NS)break;
        previous=now;
        sha256_t hash;unsigned char digest[32];char actual[65];
        sha256_init(&hash);sha256_update(&hash,probe_input,sizeof(probe_input));sha256_final(&hash,digest);
        for(unsigned j=0;j<32;++j){actual[j*2]="0123456789abcdef"[digest[j]>>4];actual[j*2+1]="0123456789abcdef"[digest[j]&15];}
        actual[64]=0;
        if(strcmp(actual,expected)||!observe_time(&now)||now<previous||now<started)return 0;
        ++result->passes;result->bytes+=sizeof(probe_input);result->elapsed_ns=now-started;previous=now;
        if(result->elapsed_ns>PROBE_DEADLINE_NS)return 0;
    }
    return result->passes>=4&&result->elapsed_ns>0&&result->elapsed_ns<=PROBE_DEADLINE_NS;
}

static int persist(FILE *log) { return fflush(log)==0&&fsync(fileno(log))==0; }
int main(int argc,char **argv) {
    if(argc!=2||strcmp(argv[1],"--cpu-hash"))return 2;
    int fd=open(PROBE_LOG_PATH,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(fd<0)return 3;
    FILE *log=fdopen(fd,"w");if(!log){close(fd);return 3;}
    fprintf(log,"BEGIN nonce=%s uid=%u euid=%u buffer_bytes=%u GPU_calls=0 title_launches=0 model_loaded=0\n",
        PROBE_NONCE,getuid(),geteuid(),PROBE_BYTES);
    HashProbeResult result;memset(&result,0,sizeof(result));
    int ok=persist(log)&&getuid()==1&&geteuid()==0&&hash_probe(&result,PROBE_SHA256);
    if(ok)fprintf(log,"CPU_HASH verified_bytes=%llu elapsed_ns=%llu passes=%u buffer_bytes=%u digest_matches=1 disk_IO_measured=0\n",
        (unsigned long long)result.bytes,(unsigned long long)result.elapsed_ns,result.passes,PROBE_BYTES);
    fprintf(log,"END success=%d nonce=%s GPU_calls=0 title_launches=0 model_loaded=0\n",ok,PROBE_NONCE);
    if(!persist(log)||fclose(log))ok=0;
    return ok?0:1;
}

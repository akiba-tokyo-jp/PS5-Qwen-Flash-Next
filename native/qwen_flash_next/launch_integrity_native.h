/* SPDX-License-Identifier: MIT
 * Included after the qualified controller's report/unchanged/SHA256 helpers.
 * It replaces only integrity input; all boot, service, title and owner guards
 * remain the controller's responsibility and are not substituted here.
 */
#ifndef QWEN_LAUNCH_INTEGRITY_NATIVE_H
#define QWEN_LAUNCH_INTEGRITY_NATIVE_H
#include "launch_integrity.h"
static _Alignas(QWEN_LAUNCH_ALIGNMENT) unsigned char qwen_launch_window[QWEN_LAUNCH_WINDOW];
static int qwen_launch_digest_failed;
struct qwen_launch_digest_context {int fd;struct ai_sha256 hash;};
static uint64_t qwen_launch_now(void *unused) {
    (void)unused;struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000||
       (uint64_t)t.tv_sec>(UINT64_MAX-999999999ull)/1000000000ull)return 0;
    return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec;
}
static int qwen_launch_headroom_sample(void *unused) {
    (void)unused;uint32_t v[7]={0};
    const char *names[]={"vm.stats.vm0.v_free_count","hw.pagesize","vm.stats.vm0.v_page_count",
        "vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_target","vm.stats.vm0.v_free_reserved","vm.stats.vm0.v_free_count"};
    for(unsigned i=0;i<7;++i){size_t n=4;if(sysctlbyname(names[i],v+i,&n,NULL,0)||n!=4)return 0;}
#ifdef QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES
    /* CPU-only application policy; this does not write either OS threshold.
     * The independent-threshold experiment is limited to tiny control metadata.
     * The default and the data-copy payload retain the additive policy. */
#ifdef QWEN_LAUNCH_CPU_INDEPENDENT_THRESHOLDS
    const uint64_t required=(uint64_t)(v[3]>v[5]?v[3]:v[5])+QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES;
#else
    const uint64_t reserve=(uint64_t)v[5]+QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES;
    const uint64_t required=(uint64_t)v[3]+reserve;
#endif
#else
    const uint64_t reserve=v[5]>256?v[5]:256;
    const uint64_t required=(uint64_t)v[3]+reserve;
#endif
    int qualified=v[1]==16384&&v[2]&&v[5]&&v[5]<=v[3]&&v[3]<v[4]&&v[4]<=v[2]&&
        v[0]<=v[2]&&v[6]<=v[2]&&(uint64_t)v[0]>=required&&(uint64_t)v[6]>=required;
#ifdef QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES
    static int pressure_reported;
    if(!qualified&&!pressure_reported++)
        (void)report("CPU_METADATA_PRESSURE free_before=%u free_after=%u OS_minimum=%u OS_reserved=%u selected_margin=%u required=%llu",
            v[0],v[6],v[3],v[5],QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES,(unsigned long long)required);
#endif
    return qualified;
}
static int qwen_launch_headroom(void *unused) {
#ifdef QWEN_LAUNCH_CPU_HEADROOM_WAIT
    static uint64_t total_wait_ns=0;
    if(qwen_launch_headroom_sample(unused))return 1;
    const uint64_t begun=qwen_launch_now(NULL);if(!begun)return 0;
    for(;;){
        uint64_t now=qwen_launch_now(NULL);
        if(now<begun||now-begun>UINT64_C(20000000000)||total_wait_ns>UINT64_C(60000000000)-(now-begun))return 0;
        if(qwen_launch_headroom_sample(unused)){
            total_wait_ns+=now-begun;
            return report("CPU_COPY_HEADROOM_WAIT waited_ms=%llu total_ms=%llu IO_retries=0 OS_predicate_unchanged=1",
                (unsigned long long)((now-begun)/1000000),(unsigned long long)(total_wait_ns/1000000));
        }
        usleep(250000);
    }
#else
    return qwen_launch_headroom_sample(unused);
#endif
}
static int qwen_launch_marker(void *unused,int before) {
    (void)unused;return report(before?"LAUNCH_INTEGRITY_READ_BEFORE":"LAUNCH_INTEGRITY_READ_RETURNED");
}
static int64_t qwen_launch_read(void *context,void *window,size_t bytes,uint64_t offset) {
    struct qwen_launch_digest_context*c=context;
    _Static_assert(sizeof(off_t)==8,"Direct integrity requires native 64-bit offsets");
    return pread(c->fd,window,bytes,(off_t)offset);
}
static int qwen_launch_consume(void *context,const unsigned char *data,size_t bytes) {
    struct qwen_launch_digest_context*c=context;ai_sha256_update(&c->hash,data,bytes);return 1;
}
static int qwen_launch_digest_matches(const char *path,size_t expected_size,const char *expected) {
    if(qwen_launch_digest_failed)return 0;
    struct stat before,opened,after;unsigned char hash[32];char hex[65];
    if(lstat(path,&before)||!S_ISREG(before.st_mode)||before.st_size!=(off_t)expected_size)goto refuse;
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_DIRECT);if(fd<0)goto refuse;
    const int flags=fcntl(fd,F_GETFL);
    int ok=flags>=0&&(flags&O_DIRECT)&&!fstat(fd,&opened)&&unchanged(&before,&opened);
    if(ok)ok=report("LAUNCH_INTEGRITY_OPEN direct_flag_set=1 bytes=%zu window=%u",expected_size,QWEN_LAUNCH_WINDOW);
    struct qwen_launch_digest_context context={.fd=fd};ai_sha256_init(&context.hash);
    struct qwen_launch_integrity s={0};s.context=&context;s.now_ns=qwen_launch_now;s.headroom=qwen_launch_headroom;
    s.marker=qwen_launch_marker;s.read_at=qwen_launch_read;s.consume=qwen_launch_consume;
    if(ok)ok=qwen_launch_integrity_stream(&s,qwen_launch_window,expected_size,60);
    if(ok)ok=!fstat(fd,&after)&&unchanged(&opened,&after)&&!lstat(path,&after)&&unchanged(&opened,&after);
    if(close(fd))ok=0;
    if(!ok)goto refuse;
    ai_sha256_final(&context.hash,hash);
    for(unsigned i=0;i<32;++i)snprintf(hex+2*i,3,"%02x",hash[i]);
    if(strcmp(hex,expected)||!report("LAUNCH_INTEGRITY_COMPLETE mode=direct bytes=%zu calls=%llu returned=%llu exact=1",
        expected_size,(unsigned long long)s.calls,(unsigned long long)s.returned))goto refuse;
    return 1;
refuse:
    qwen_launch_digest_failed=1;return 0;
}
#endif

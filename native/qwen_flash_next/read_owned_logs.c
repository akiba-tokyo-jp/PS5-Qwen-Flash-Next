/* SPDX-License-Identifier: GPL-3.0-or-later
 * Read two fixed native-owner log tails after exact boot/service/owner guards.
 * The build supplies the unchanged guards from the pinned normal-close helper;
 * its main and every close/mutation operation are excluded before compilation.
 */
#include "qualified_owner_guard.c"
#include <sys/stat.h>
#include <fcntl.h>
#include "owned_log_paths.h"
static int scalar(const char *name,uint32_t *value) {
    size_t bytes=sizeof(*value);*value=0;
    return !sysctlbyname(name,value,&bytes,NULL,0)&&bytes==sizeof(*value);
}
static int headroom(void) {
    uint32_t page=0,free_first=0,free_last=0,minimum=0,reserved=0;
    int ok=scalar("hw.pagesize",&page)&&scalar("vm.stats.vm0.v_free_count",&free_first)&&
        scalar("vm.stats.vm0.v_free_min",&minimum)&&scalar("vm.stats.vm0.v_free_reserved",&reserved)&&
        scalar("vm.stats.vm0.v_free_count",&free_last)&&page==16384;
    uint32_t extra=reserved>256?reserved:256;
    ok=ok&&minimum&&minimum<=UINT32_MAX-extra&&free_first>minimum+extra&&free_last>minimum+extra;
    return report("CPU_headroom admitted=%d page=%u free_first=%u free_last=%u minimum=%u reserved=%u extra=%u inactive_counted=0",ok,page,free_first,free_last,minimum,reserved,extra)&&ok;
}
static int same_file(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&
        a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&
        a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int read_tail(const char *label,const char *path) {
    // This helper's real UID is already the native owner's UID. PS5 does not
    // grant this root-effective helper a DAC override for owner-only logs.
    // Change only this helper's effective UID; never chmod/chown the target.
    if(geteuid()!=0||getuid()!=1||seteuid(1)||geteuid()!=1)return report("owned_log_UID_drop_failed label=%s",label)&&0;
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);
    if(fd<0){int saved=errno;int restored=!seteuid(0)&&geteuid()==0;return report("owned_log_open_failed label=%s errno=%d helper_UID_restored=%d",label,saved,restored)&&0;}
    struct stat before,after;int ok=!fstat(fd,&before)&&S_ISREG(before.st_mode)&&before.st_uid==1&&
        (before.st_mode&07777)==0600&&before.st_nlink==1&&before.st_size>0&&before.st_size<=(8u<<20);
    off_t at=ok&&before.st_size>(512u<<10)?before.st_size-(512u<<10):0;
    if(!ok||!report("BEGIN_OWNED_LOG label=%s total_bytes=%lld offset=%lld",label,(long long)before.st_size,(long long)at)){close(fd);(void)seteuid(0);return 0;}
    char buffer[4096];
    while(ok&&at<before.st_size) {
        size_t wanted=(size_t)(before.st_size-at);if(wanted>sizeof(buffer))wanted=sizeof(buffer);
        ssize_t got=pread(fd,buffer,wanted,at);if(got<=0||(size_t)got>wanted){ok=0;break;}
        for(ssize_t done=0;done<got;) {
            ssize_t n=write(output_fd,buffer+done,(size_t)(got-done));if(n<=0){ok=0;break;}done+=n;
        }
        at+=got;
    }
    ok=ok&&!fstat(fd,&after)&&same_file(&before,&after)&&at==before.st_size;
    if(close(fd))ok=0;
    const int restored=!seteuid(0)&&geteuid()==0;
    return report("END_OWNED_LOG label=%s stable=%d helper_UID_restored=%d",label,ok,restored)&&ok&&restored;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0;
    if(!report("ENTRY code=owned-native-log-reader nonce=%s argc=%d constructors=%u GPU_calls=0 mutations=0 title_close_calls=0",CLOSE_NONCE,argc,constructors))return 1;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!owner(1)||!headroom()||
        !context(2)||!owner(2)||!healthy)goto done;
    ok=read_tail("diagnostic",OWNED_DIAGNOSTIC_PATH)&&headroom()&&read_tail("driver",OWNED_DRIVER_PATH)&&
        context(3)&&owner(3)&&headroom();
done:
    if(!report("END success=%d nonce=%s GPU_calls=0 mutations=0 title_close_calls=0 model_payload_reads=0 automatic_retry=0",ok,CLOSE_NONCE))ok=0;
    return ok?0:1;
}

/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded tail of one positively closed native diagnostic; source is read only.
 */
#define MOSS_RUNTIME_PREP 1
#include "direct-controller.c"
#include "closed_diagnostic_context.h"
int main(int argc,char **argv) {
    (void)argv;int ok=0,fd=-1;struct stat before,after;unsigned char data[4096],extra;
    if(argc!=0&&argc!=1)return 2;
    journal=open(CD_JOURNAL,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(journal<0)return 3;
    if(!report("BEGIN nonce=%s CPU_only=1 title_launches=0 GPU_calls=0 source_writes=0",CD_NONCE)||
       constructors!=1||getuid()!=1||geteuid()!=0||!live_context()||!idle()||!no_native_owner())goto done;
    fd=open(CD_SOURCE,O_RDONLY|O_NOFOLLOW);
    if(!report("DIAGNOSTIC_OPEN returned=%d errno=%d",fd>=0,errno)||fd<0)goto done;
    if(fstat(fd,&before)||!S_ISREG(before.st_mode)||before.st_uid!=1||before.st_size<=0||before.st_size>(8<<20))goto done;
    const size_t count=before.st_size>4096?4096:(size_t)before.st_size;
    const off_t offset=before.st_size-(off_t)count;
    if(!report("DIAGNOSTIC_TAIL bytes=%lld offset=%lld captured=%zu whole_file=%d",(long long)before.st_size,
        (long long)offset,count,offset==0))goto done;
    if(pread(fd,data,count,offset)!=(ssize_t)count||pread(fd,&extra,1,before.st_size)!=0||
       fstat(fd,&after)||!unchanged(&before,&after))goto done;
    for(size_t at=0;at<count;at+=64){char hex[129];size_t bytes=count-at;if(bytes>64)bytes=64;
        for(size_t i=0;i<bytes;++i){hex[2*i]="0123456789abcdef"[data[at+i]>>4];hex[2*i+1]="0123456789abcdef"[data[at+i]&15];}
        hex[2*bytes]=0;if(!report("DIAGNOSTIC_HEX offset=%zu bytes=%zu data=%s",at,bytes,hex))goto done;}
    if(close(fd))goto done;fd=-1;
    if(!live_context()||!idle()||!no_native_owner())goto done;ok=1;
done:
    if(fd>=0&&close(fd))ok=0;
    if(!report("END success=%d nonce=%s source_writes=0 GPU_calls=0 title_launches=0 automatic_retry=0",ok,CD_NONCE))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

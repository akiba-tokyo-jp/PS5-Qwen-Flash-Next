/* SPDX-License-Identifier: GPL-3.0-or-later
 * Qualify the declared vector-I/O ABI using invalid descriptors only.
 */
#include "qualified_context_guard.c"
#include "vector_io_context.h"
#include <ps5platform/kernel.h>
#include <sys/uio.h>
#include <fcntl.h>
#include <errno.h>
#include <stddef.h>
_Static_assert(sizeof(struct iovec)==16,"Native vector descriptor width");
_Static_assert(offsetof(struct iovec,iov_base)==0,"Native vector address offset");
_Static_assert(offsetof(struct iovec,iov_len)==8,"Native vector size offset");
_Static_assert(sizeof(off_t)==8,"Native file offset width");
int main(int argc,char **argv) {
    (void)argv;int ok=0;char byte=0;struct iovec vector={&byte,1};
    output_fd=open(VECTOR_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s invalid_descriptors_only=1 allocations=0 payload_reads=0 title_launches=0 GPU_calls=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
        sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("PREADV_BEFORE fd_invalid=1 vectors=1 offset=0"))goto done;
    errno=0;const ssize_t positioned=preadv(-1,&vector,1,0);const int positioned_error=errno;
    if(!report("PREADV_RETURNED result=%lld errno=%d",(long long)positioned,positioned_error)||
        positioned!=-1||positioned_error!=EBADF||byte)goto done;
    if(!report("READV_BEFORE fd_invalid=1 vectors=1"))goto done;
    errno=0;const ssize_t sequential=readv(-1,&vector,1);const int sequential_error=errno;
    if(!report("READV_RETURNED result=%lld errno=%d",(long long)sequential,sequential_error)||
        sequential!=-1||sequential_error!=EBADF||byte)goto done;
    if(!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=1;
done:
    if(!report("END success=%d nonce=%s vector_calls=2 invalid_descriptors_only=1 allocations=0 payload_reads=0 title_launches=0 GPU_calls=0 no_retry=1",ok,CLOSE_NONCE))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
    return ok?0:1;
}

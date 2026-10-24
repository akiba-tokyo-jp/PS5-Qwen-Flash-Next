/* SPDX-License-Identifier: MIT
 * Seal only the plan-bound model files. No payload reads, ownership changes,
 * deletion, title operations, model loading, mappings or GPU operations.
 */
#ifdef QWEN_SEAL_HOST_STUBS
#include "model_file_seal_stubs.h"
#else
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#endif
struct expected_model_file { const char *path; uint64_t bytes; };
#include "model_file_seal_context.h"
#define SEAL_GUARD UINT64_C(0x6352679174ab8192)
_Static_assert(sizeof(struct stat)<=256,"Bounded native stat ABI");
static struct stat initial[sizeof(expected_files)/sizeof(expected_files[0])];
static int same_identity(const struct stat *a,const struct stat *b,int mode) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&
        a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&(!mode||a->st_mode==b->st_mode)&&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec;
}
static int observed(int fd,struct stat *out) {
    struct {uint64_t pre[2];unsigned char data[256];uint64_t post[2];} g;
    memset(&g,0,sizeof(g));g.pre[0]=g.pre[1]=g.post[0]=g.post[1]=SEAL_GUARD;
    if(fstat(fd,(struct stat *)(void *)g.data)||g.pre[0]!=SEAL_GUARD||g.pre[1]!=SEAL_GUARD||
       g.post[0]!=SEAL_GUARD||g.post[1]!=SEAL_GUARD)return 0;
    memcpy(out,g.data,sizeof(*out));return 1;
}
static int directory(void) {
    int fd=open(SEAL_ROOT,O_RDONLY|O_NONBLOCK|O_DIRECTORY|O_NOFOLLOW);if(fd<0)return 0;
    struct stat info;int ok=observed(fd,&info)&&S_ISDIR(info.st_mode)&&info.st_ino&&
        info.st_uid==0&&info.st_gid==0&&(info.st_mode&07777)==0755;
    if(close(fd))ok=0;return ok;
}
static int valid_file(const struct stat *info,unsigned index) {
    unsigned mode=info->st_mode&07777;
    return S_ISREG(info->st_mode)&&info->st_ino&&info->st_uid==0&&info->st_gid==0&&info->st_size>0&&
        (uint64_t)info->st_size==expected_files[index].bytes&&(mode==0777||mode==0644);
}
static int preflight(void) {
    if(!directory())return 0;
    for(unsigned i=0;i<sizeof(expected_files)/sizeof(expected_files[0]);++i){
        int fd=open(expected_files[i].path,O_RDONLY|O_NONBLOCK|O_NOFOLLOW);if(fd<0)return 0;
        int ok=observed(fd,&initial[i])&&valid_file(&initial[i],i);if(close(fd))ok=0;if(!ok)return 0;
    }
    return directory();
}
static int seal_files(FILE *log) {
    if(!preflight())return 0;
    for(unsigned i=0;i<sizeof(expected_files)/sizeof(expected_files[0]);++i){
        int fd=open(expected_files[i].path,O_RDONLY|O_NONBLOCK|O_NOFOLLOW);if(fd<0)return 0;
        struct stat before,after;int ok=observed(fd,&before)&&valid_file(&before,i)&&same_identity(&before,&initial[i],1);
        if(ok&&(before.st_mode&07777)!=0644)ok=fchmod(fd,0644)==0;
        if(ok)ok=observed(fd,&after)&&valid_file(&after,i)&&(after.st_mode&07777)==0644&&same_identity(&before,&after,0);
        if(close(fd))ok=0;
        if(fprintf(log,"FILE_SEALED index=%u expected_bytes=%llu previous_mode=%04o mode=0644 identity_stable=%d contents_read=0 success=%d\n",
            i+1,(unsigned long long)expected_files[i].bytes,(unsigned)initial[i].st_mode&07777,ok,ok)<0||fflush(log))return 0;
        if(!ok)return 0;
    }
    if(!directory())return 0;
    for(unsigned i=0;i<sizeof(expected_files)/sizeof(expected_files[0]);++i){
        int fd=open(expected_files[i].path,O_RDONLY|O_NONBLOCK|O_NOFOLLOW);if(fd<0)return 0;
        struct stat after;int ok=observed(fd,&after)&&valid_file(&after,i)&&(after.st_mode&07777)==0644&&same_identity(&initial[i],&after,0);
        if(close(fd))ok=0;if(!ok)return 0;
    }
    return directory();
}
int main(int argc,char **argv) {
    if(argc!=2||strcmp(argv[1],"--seal-model-files"))return 2;
    int fd=open(SEAL_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)return 3;
    FILE *log=fdopen(fd,"w");if(!log){close(fd);return 3;}
    fprintf(log,"BEGIN nonce=%s uid=%u euid=%u files=%zu payload_reads=0 GPU_calls=0 title_launches=0\n",
        SEAL_NONCE,getuid(),geteuid(),sizeof(expected_files)/sizeof(expected_files[0]));
    int ok=getuid()==1&&geteuid()==0&&seal_files(log);
    fprintf(log,"END success=%d nonce=%s files=%zu mode=0644 owner=0 payload_reads=0 GPU_calls=0 title_launches=0\n",
        ok,SEAL_NONCE,sizeof(expected_files)/sizeof(expected_files[0]));
    if(fflush(log)||fsync(fileno(log))||fclose(log))ok=0;
    return ok?0:1;
}

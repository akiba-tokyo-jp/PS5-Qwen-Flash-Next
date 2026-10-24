/* SPDX-License-Identifier: MIT
 * Read only sealed model identities and bounded prior evidence. Never maps a
 * file, reads model payloads, changes permissions, launches a title or uses GPU.
 */
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "hash/sha256/sha256.h"
struct expected_model_file {const char *path;uint64_t bytes;};
#include "model_identity_snapshot_context.h"
#define ID_GUARD UINT64_C(0x749ab32871185349)
_Static_assert(sizeof(struct stat)<=256,"Measured stat ABI bound");
static struct stat identities[77];
static int observed(int fd,struct stat *out){
    struct {uint64_t pre[2];unsigned char data[256];uint64_t post[2];} g;
    memset(&g,0,sizeof(g));g.pre[0]=g.pre[1]=g.post[0]=g.post[1]=ID_GUARD;
    if(fstat(fd,(struct stat *)(void *)g.data)||g.pre[0]!=ID_GUARD||g.pre[1]!=ID_GUARD||g.post[0]!=ID_GUARD||g.post[1]!=ID_GUARD)return 0;
    memcpy(out,g.data,sizeof(*out));return 1;
}
static int same(const struct stat *a,const struct stat *b){
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int no_later(int64_t a,long an,int64_t b,long bn){return a<b||(a==b&&an<=bn);}
static int evidence(const char *path,uint64_t bytes,const char *expected,unsigned uid,struct stat *out){
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);if(fd<0)return 0;
    struct stat after;int ok=observed(fd,out)&&S_ISREG(out->st_mode)&&out->st_ino&&out->st_uid==uid&&out->st_size>0&&(uint64_t)out->st_size==bytes&&bytes<=65536;
    sha256_t hash;sha256_init(&hash);unsigned char buffer[4096],digest[32];uint64_t count=0;
    while(ok&&count<bytes){size_t wanted=(size_t)(bytes-count);if(wanted>sizeof(buffer))wanted=sizeof(buffer);
        ssize_t got=read(fd,buffer,wanted);if(got<=0||(size_t)got>wanted){ok=0;break;}sha256_update(&hash,buffer,(size_t)got);count+=(uint64_t)got;}
    if(ok)ok=observed(fd,&after)&&same(out,&after)&&count==bytes;
    if(close(fd))ok=0;
    sha256_final(&hash,digest);char hex[65];for(unsigned i=0;i<32;++i){hex[i*2]="0123456789abcdef"[digest[i]>>4];hex[i*2+1]="0123456789abcdef"[digest[i]&15];}hex[64]=0;
    return ok&&!strcmp(hex,expected);
}
static int directory(struct stat *out){
    int fd=open(SNAPSHOT_ROOT,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK);if(fd<0)return 0;
    int ok=observed(fd,out)&&S_ISDIR(out->st_mode)&&out->st_ino&&out->st_uid==0&&out->st_gid==0&&(out->st_mode&07777)==0755;
    if(close(fd))ok=0;return ok;
}
static int row(unsigned i,struct stat *out){
    int fd=open(expected_files[i].path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);if(fd<0)return 0;
    int ok=observed(fd,out)&&S_ISREG(out->st_mode)&&out->st_ino&&out->st_uid==0&&out->st_gid==0&&(out->st_mode&07777)==0644&&out->st_size>0&&(uint64_t)out->st_size==expected_files[i].bytes;
    if(close(fd))ok=0;return ok;
}
static void identity(FILE *log,const char *label,unsigned index,const struct stat *s){
    fprintf(log,"%s index=%u dev=%llu ino=%llu mode=%u uid=%u gid=%u bytes=%llu mtime_sec=%lld mtime_nsec=%ld ctime_sec=%lld ctime_nsec=%ld\n",
        label,index,(unsigned long long)s->st_dev,(unsigned long long)s->st_ino,(unsigned)s->st_mode,(unsigned)s->st_uid,(unsigned)s->st_gid,
        (unsigned long long)s->st_size,(long long)s->st_mtim.tv_sec,s->st_mtim.tv_nsec,(long long)s->st_ctim.tv_sec,s->st_ctim.tv_nsec);
}
int main(int argc,char **argv){
    if(argc!=2||strcmp(argv[1],"--snapshot-sealed-model"))return 2;
    int fd=open(SNAPSHOT_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)return 3;
    FILE *log=fdopen(fd,"w");if(!log){close(fd);return 3;}
    fprintf(log,"BEGIN nonce=%s uid=%u euid=%u model_payload_reads=0 mappings=0 GPU_calls=0 title_launches=0\n",SNAPSHOT_NONCE,getuid(),geteuid());
    struct stat seal,integrity,before,after;int ok=getuid()==1&&geteuid()==0&&sizeof(expected_files)/sizeof(expected_files[0])==77;
    ok=ok&&evidence(SEAL_EVIDENCE,SEAL_BYTES,SEAL_SHA256,0,&seal)&&evidence(INTEGRITY_EVIDENCE,INTEGRITY_BYTES,INTEGRITY_SHA256,1,&integrity);
    if(ok)ok=no_later(seal.st_mtim.tv_sec,seal.st_mtim.tv_nsec,integrity.st_mtim.tv_sec,integrity.st_mtim.tv_nsec)&&directory(&before);
    if(ok)ok=no_later(before.st_mtim.tv_sec,before.st_mtim.tv_nsec,seal.st_mtim.tv_sec,seal.st_mtim.tv_nsec)&&no_later(before.st_ctim.tv_sec,before.st_ctim.tv_nsec,seal.st_mtim.tv_sec,seal.st_mtim.tv_nsec);
    if(ok){identity(log,"SEAL_EVIDENCE",0,&seal);identity(log,"INTEGRITY_EVIDENCE",0,&integrity);identity(log,"MODEL_DIRECTORY",0,&before);}
    for(unsigned i=0;ok&&i<77;++i){
        ok=row(i,&identities[i])&&no_later(identities[i].st_ctim.tv_sec,identities[i].st_ctim.tv_nsec,seal.st_mtim.tv_sec,seal.st_mtim.tv_nsec)&&
            no_later(identities[i].st_mtim.tv_sec,identities[i].st_mtim.tv_nsec,identities[i].st_ctim.tv_sec,identities[i].st_ctim.tv_nsec);
        if(ok)identity(log,"MODEL_IDENTITY",i+1,&identities[i]);
    }
    for(unsigned i=0;ok&&i<77;++i){struct stat check;ok=row(i,&check)&&same(&check,&identities[i]);}
    if(ok)ok=directory(&after)&&same(&before,&after);
    fprintf(log,"END success=%d nonce=%s files=77 all_ctimes_no_later_than_sealing=1 directory_unchanged_since_sealing=1 model_payload_reads=0 mappings=0 GPU_calls=0 title_launches=0\n",ok,SNAPSHOT_NONCE);
    if(fflush(log)||fsync(fileno(log))||fclose(log))ok=0;
    return ok?0:1;
}

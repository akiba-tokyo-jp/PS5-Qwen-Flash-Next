/* SPDX-License-Identifier: MIT
 * Exercise the real receiver with a fragmented stream and returned failures.
 * The transport and file calls below never access an operating-system object.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sha256.h"

typedef long long ssize_t;
#define off_t test_off_t
typedef long long off_t;
typedef unsigned socklen_t;
struct timeval { long tv_sec,tv_usec; };
struct sockaddr { unsigned char sin_len,sin_family; };
struct sockaddr_in { unsigned char sin_len,sin_family;unsigned short sin_port;struct {uint32_t s_addr;} sin_addr; };
struct stat { unsigned st_mode,st_nlink,st_uid,st_gid;off_t st_size; };
#define AF_INET 2
#define SOCK_STREAM 1
#define SOL_SOCKET 1
#define SO_RCVBUF 1
#define SO_RCVTIMEO 2
#define SO_SNDTIMEO 3
#define O_WRONLY 1
#define O_CREAT 2
#define O_EXCL 4
#define O_NOFOLLOW 8
#define O_DIRECT 16
#define F_GETFL 1
#define ENOENT 2
#define S_ISREG(mode) ((mode)==0100000)
#define DIRECT_STAGE_PATH "/new-test-copy"
#define DIRECT_STAGE_PORT 43210
#define DIRECT_STAGE_CONSOLE_IP 1
#define DIRECT_STAGE_PEER_IP 2
#define DIRECT_STAGE_BYTES 17003u
#define DIRECT_STAGE_NONCE "0123456789abcdef0123456789abcdef"
#define DIRECT_STAGE_SHA256 expected_sha

static unsigned char payload[DIRECT_STAGE_BYTES],wire[128+DIRECT_STAGE_BYTES],stored[32768];
static char expected_sha[65];
static size_t cursor,wire_size,stored_size;
static unsigned live_objects,opens,acks,write_calls;
#undef errno
static int fault,errno;
static uint64_t now_ns;
enum { GOOD,EXISTS,PEER,NONCE,SIZE,RESERVED,SHORT_STREAM,CORRUPT_PAYLOAD,SHORT_WRITE,SYNC,READBACK,CLOSE,SEND,EXPIRED,FAULT_COUNT };
#define CHECK(value) do {if(!(value)){fprintf(stderr,"check failed line %d fault %d\n",__LINE__,fault);exit(1);}} while(0)
static void sha_text(const unsigned char *data,size_t bytes,char text[65]){
    struct ai_sha256 h;unsigned char digest[32];ai_sha256_init(&h);ai_sha256_update(&h,data,bytes);ai_sha256_final(&h,digest);
    for(unsigned i=0;i<32;++i){text[2*i]="0123456789abcdef"[digest[i]>>4];text[2*i+1]="0123456789abcdef"[digest[i]&15];}text[64]=0;
}
static uint64_t qwen_launch_now(void *unused){(void)unused;now_ns+=fault==EXPIRED?180000000001ull:1;return now_ns;}
static int qwen_launch_headroom(void *unused){(void)unused;return 1;}
static int report(const char *format,...){(void)format;return 1;}
static int lstat(const char *path,struct stat *s){CHECK(!strcmp(path,DIRECT_STAGE_PATH));(void)s;errno=ENOENT;return fault==EXISTS?0:-1;}
static int socket(int domain,int type,int protocol){CHECK(domain==AF_INET&&type==SOCK_STREAM&&!protocol);++live_objects;return 10;}
static int setsockopt(int fd,int level,int name,const void *value,socklen_t bytes){CHECK((fd==10||fd==11)&&level==SOL_SOCKET&&name&&value&&bytes);return 0;}
static unsigned short htons(unsigned short n){return (unsigned short)((n<<8)|(n>>8));}
static int bind(int fd,const struct sockaddr *address,socklen_t bytes){CHECK(fd==10&&address&&bytes==sizeof(struct sockaddr_in));return 0;}
static int listen(int fd,int backlog){CHECK(fd==10&&backlog==1);return 0;}
static int accept(int fd,struct sockaddr *address,socklen_t *bytes){
    CHECK(fd==10&&*bytes==sizeof(struct sockaddr_in));struct sockaddr_in *peer=(struct sockaddr_in*)address;
    peer->sin_family=AF_INET;peer->sin_addr.s_addr=fault==PEER?99:DIRECT_STAGE_PEER_IP;++live_objects;return 11;
}
static ssize_t recv(int fd,void *data,size_t bytes,int flags){
    CHECK(fd==11&&!flags);if(cursor==wire_size)return 0;
    /* Deliberately split every header and payload across many receives. */
    size_t n=bytes<997?bytes:997;if(n>wire_size-cursor)n=wire_size-cursor;
    memcpy(data,wire+cursor,n);cursor+=n;return (ssize_t)n;
}
static int open(const char *path,int flags,int mode){
    CHECK(!strcmp(path,DIRECT_STAGE_PATH)&&flags==(O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT)&&mode==0644);
    ++opens;++live_objects;return 12;
}
static int fcntl(int fd,int command){CHECK(fd==12&&command==F_GETFL);return O_DIRECT;}
static int fstat(int fd,struct stat *s){CHECK(fd==12);memset(s,0,sizeof(*s));s->st_mode=0100000;s->st_nlink=1;return 0;}
static ssize_t pwrite(int fd,const void *data,size_t bytes,off_t offset){
    CHECK(fd==12&&bytes==16384&&offset>=0&&(offset%16384)==0&&((uintptr_t)data%16384)==0&&offset+bytes<=sizeof(stored));
    ++write_calls;if(fault==SHORT_WRITE)return (ssize_t)bytes-1;
    memcpy(stored+(size_t)offset,data,bytes);stored_size=(size_t)offset+bytes;return (ssize_t)bytes;
}
static int ftruncate(int fd,off_t bytes){CHECK(fd==12&&bytes==DIRECT_STAGE_BYTES&&stored_size==32768);
    for(size_t i=DIRECT_STAGE_BYTES;i<stored_size;++i)CHECK(!stored[i]);stored_size=(size_t)bytes;return 0;}
static int fsync(int fd){CHECK(fd==12);return fault==SYNC?-1:0;}
static int close(int fd){CHECK(fd>=10&&fd<=12&&live_objects);--live_objects;return fault==CLOSE&&fd==12?-1:0;}
static int qwen_launch_digest_matches(const char *path,uint64_t bytes,const char *sha){
    CHECK(!strcmp(path,DIRECT_STAGE_PATH)&&bytes==DIRECT_STAGE_BYTES&&stored_size==bytes);
    char actual[65];sha_text(stored,stored_size,actual);return fault!=READBACK&&!strcmp(actual,sha);
}
static ssize_t send(int fd,const void *data,size_t bytes,int flags){
    CHECK(fd==11&&bytes==8&&!flags&&!memcmp(data,"QWENDONE",8));if(fault==SEND)return 4;++acks;return 8;
}
#include "direct_stage_under_test.h"

int main(void){
    /* PE/COFF caps static alignment at 8192; supply the same aligned window. */
    unsigned char *backing=malloc(32768);CHECK(backing!=NULL);
    direct_stage_window=(unsigned char*)(((uintptr_t)backing+16383)&~(uintptr_t)16383);
    for(size_t i=0;i<sizeof(payload);++i)payload[i]=(unsigned char)(i*73+19);
    sha_text(payload,sizeof(payload),expected_sha);
    for(fault=GOOD;fault<FAULT_COUNT;++fault){
        memset(wire,0,sizeof(wire));memcpy(wire,"QWENDIR1",8);memcpy(wire+8,DIRECT_STAGE_NONCE,32);
        const uint64_t bytes=DIRECT_STAGE_BYTES;memcpy(wire+40,&bytes,8);memcpy(wire+48,expected_sha,64);memcpy(wire+128,payload,sizeof(payload));
        memset(stored,0xff,sizeof(stored));cursor=stored_size=0;wire_size=sizeof(wire);live_objects=opens=acks=write_calls=0;now_ns=0;
        if(fault==NONCE)wire[8]^=1;if(fault==SIZE)wire[40]^=1;if(fault==RESERVED)wire[127]=1;
        if(fault==SHORT_STREAM)wire_size-=17;if(fault==CORRUPT_PAYLOAD)wire[129]^=1;
        int operations=0;const int result=case_receive_direct_stage(&operations);
        CHECK(result==(fault==GOOD)&&live_objects==0&&opens<=1&&operations==(int)opens&&acks==(fault==GOOD));
        if(fault==GOOD)CHECK(write_calls==2&&stored_size==sizeof(payload)&&!memcmp(stored,payload,sizeof(payload)));
        if(fault==EXISTS||fault==PEER||fault==NONCE||fault==SIZE||fault==RESERVED||fault==EXPIRED)CHECK(!opens);
    }
    free(backing);
    printf("{\"completed\":true,\"returned_transport_and_file_cases\":%d,\"fragmented_stream_and_aligned_tail_exact\":true,\"OS_objects\":0,\"PS5_operations\":0}\n",FAULT_COUNT);
    return 0;
}

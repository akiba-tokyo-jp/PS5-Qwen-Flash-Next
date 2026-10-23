/* SPDX-License-Identifier: MIT
 * In-memory API fault injection. No host or console ownership changes occur.
 */
#define QWEN_MODEL_DIRECTORY_HOST_STUBS 1
#define main model_directory_control_entry
#include "../native/qwen_flash_next/model_directory_control.c"
#undef main
#include <stdlib.h>

typedef struct { const char *path,*text; struct stat value; } Node;
static Node nodes[10];
static int fd_node[128],fd_live[128],fd_pos[128],next_fd;
static int owner_calls,mode_calls,close_calls,read_after_close,clobber,fail_close;
static unsigned checks;
static int find(const char *name) {
    for(int i=0;i<10;i++)if(!strcmp(nodes[i].path,name))return i;
    return -1;
}
static void reset(void) {
    const char *paths[]={APP,APP "/web",APP "/validation-owner",APP "/app.json",APP "/development.json",
        APP "/web/index.html",APP "/web/app.js",APP "/web/style.css",MODEL,MODEL "/.qwen-transfer-owner.json"};
    memset(nodes,0,sizeof(nodes));memset(fd_live,0,sizeof(fd_live));memset(fd_pos,0,sizeof(fd_pos));
    memset(fd_node,-1,sizeof(fd_node));next_fd=3;owner_calls=mode_calls=close_calls=read_after_close=clobber=fail_close=0;
    for(int i=0;i<10;i++){
        nodes[i].path=paths[i];nodes[i].value.st_mode=S_IFREG|0644;nodes[i].value.st_nlink=1;
    }
    nodes[0].value.st_mode=nodes[1].value.st_mode=S_IFDIR|0755;
    nodes[0].value.st_uid=nodes[1].value.st_uid=1;
    nodes[2].text=OWNER_NONCE;nodes[2].value.st_size=(long long)strlen(OWNER_NONCE);
    nodes[8].value.st_mode=S_IFDIR|0700;
    nodes[9].text=MODEL_MARKER;nodes[9].value.st_size=(long long)strlen(MODEL_MARKER);nodes[9].value.st_mode=S_IFREG|0600;
}
static void check(int value) {++checks;if(!value){fprintf(stderr,"Directory API check %u failed\n",checks);exit(1);}}
static int valid_fd(int fd) {return fd>=3&&fd<128&&fd_live[fd];}
int md_open(const char *path,int flags,...) {
    int index=find(path);
    if(index<0||!(flags&O_NOFOLLOW)||(nodes[index].value.st_mode&S_IFMT)==S_IFLNK||
       ((flags&O_DIRECTORY)&&!S_ISDIR(nodes[index].value.st_mode))||next_fd>=128)return -1;
    int fd=next_fd++;fd_node[fd]=index;fd_live[fd]=1;return fd;
}
md_ssize md_read(int fd,void *out,size_t size) {
    if(!valid_fd(fd)){++read_after_close;return -1;}
    Node *node=&nodes[fd_node[fd]];if(!node->text)return -1;
    size_t remaining=strlen(node->text)-(size_t)fd_pos[fd];if(size>remaining)size=remaining;
    memcpy(out,node->text+fd_pos[fd],size);fd_pos[fd]+=(int)size;return (md_ssize)size;
}
int md_close(int fd) {
    ++close_calls;if(!valid_fd(fd))return -1;
    if(fail_close){fail_close=0;return -1;}
    fd_live[fd]=0;return 0;
}
static void result_stat(struct stat *out,int index) {
    *out=nodes[index].value;
    if(clobber){GuardedStat *guard=(GuardedStat*)((char*)out - offsetof(GuardedStat,value));guard->post=0;}
}
int md_lstat(const char *path,struct stat *out) {int i=find(path);if(i<0)return -1;result_stat(out,i);return 0;}
int md_fstat(int fd,struct stat *out) {if(!valid_fd(fd))return -1;result_stat(out,fd_node[fd]);return 0;}
int md_chown(const char *path,unsigned uid,unsigned gid) {
    int i=find(path);if(i<0)return -1;++owner_calls;nodes[i].value.st_uid=uid;nodes[i].value.st_gid=gid;return 0;
}
int md_chmod(const char *path,unsigned mode) {
    int i=find(path);if(i<0)return -1;++mode_calls;nodes[i].value.st_mode=(nodes[i].value.st_mode&S_IFMT)|mode;return 0;
}
int md_fchmod(int fd,unsigned mode) {return valid_fd(fd)?md_chmod(nodes[fd_node[fd]].path,mode):-1;}
unsigned md_getuid(void){return 1;}
unsigned md_geteuid(void){return 0;}
int md_fsync(int fd){(void)fd;return 0;}
FILE *md_fdopen(int fd,const char *mode){(void)fd;(void)mode;return NULL;}
int md_fileno(FILE *file){(void)file;return 0;}

int main(void) {
    unsigned char left[4096]={0},right[4096]={0};
    check(bytes_equal(left,right,sizeof(left)));
    right[4095]=0x80;check(!bytes_equal(left,right,sizeof(left)));
    check(bytes_equal(left,right,sizeof(left)-1));
    left[4095]=0x80;check(bytes_equal(left,right,sizeof(left)));
    reset();check(prepare());check(owner_calls==2&&nodes[0].value.st_uid==0&&nodes[1].value.st_uid==0);
    reset();nodes[0].value.st_uid=7;check(!prepare());check(owner_calls==0&&mode_calls==0);
    reset();nodes[0].value.st_mode=S_IFLNK|0755;check(!prepare());check(owner_calls==0);
    reset();nodes[2].text="incorrect-owner";check(!prepare());check(owner_calls==0);
    reset();check(prepare());owner_calls=0;check(model_directory(1,NULL));check(finalize_parent());
    check(model_directory(0,NULL));check(nodes[0].value.st_uid==1&&nodes[1].value.st_uid==1);
    check((nodes[8].value.st_mode&07777)==0755&&(nodes[9].value.st_mode&07777)==0644);
    reset();nodes[8].value.st_uid=7;check(!model_directory(1,NULL));check(mode_calls==0&&owner_calls==0);
    reset();nodes[9].text="wrong-new-marker";check(!model_directory(1,NULL));check(mode_calls==0);
    reset();nodes[8].value.st_mode=S_IFLNK|0755;check(!model_directory(1,NULL));check(mode_calls==0&&close_calls==0);
    reset();nodes[9].value.st_nlink=2;check(!model_directory(1,NULL));check(mode_calls==0);
    reset();clobber=1;check(!model_directory(1,NULL));check(mode_calls==0&&close_calls==1);
    reset();fail_close=1;check(!prepare());check(owner_calls==0&&close_calls==1&&read_after_close==0);
    reset();check(prepare());nodes[3].value.st_uid=7;owner_calls=0;check(!finalize_parent());
    check(owner_calls==0&&nodes[0].value.st_uid==0&&nodes[1].value.st_uid==0);
    reset();check(!model_directory(0,NULL));check(mode_calls==0);
    reset();nodes[8].value.st_mode=S_IFDIR|0755;nodes[9].value.st_mode=S_IFREG|0644;
    check(model_directory(0,NULL));check(mode_calls==0&&owner_calls==0&&read_after_close==0);
    printf("Model directory ownership, marker, symlink, canary and close guards: %u checks passed\n",checks);
    return 0;
}

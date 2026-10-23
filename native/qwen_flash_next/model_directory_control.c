/* SPDX-License-Identifier: MIT
 * CPU-only model-directory preparation. Ownership helpers retain the project's
 * qualified source-permissions.c contract. No title/GPU action or process
 * credential change. Only the task's known local-owner markers are read.
 * Private nonces and exact marker bytes are generated on the data disk.
 */
#ifdef QWEN_MODEL_DIRECTORY_HOST_STUBS
#include "model_directory_stubs.h"
#else
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#endif
#include "model_directory_context.h"
#define APP "/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime"
#define MODEL APP "/model"
#define CANARY 0x761237612376123ULL
typedef struct { unsigned long long pre; struct stat value; unsigned long long post; } GuardedStat;

static void initialize(GuardedStat * value) {
    memset(value,0,sizeof(*value)); value->pre=value->post=CANARY;
}
static int intact(const GuardedStat * value) { return value->pre==CANARY&&value->post==CANARY; }
static int persist(FILE *log) { return fflush(log)==0&&fsync(fileno(log))==0; }
static int bytes_equal(const void *left,const void *right,size_t bytes) {
    /* Keep exact marker comparison local for every generated marker length.
     * Volatile reads prevent a synthesized libc import outside the qualified set.
     */
    const volatile unsigned char *a=left,*b=right;
    for(size_t i=0;i<bytes;++i)if(a[i]!=b[i])return 0;
    return 1;
}
static int marker_matches(void) {
    char text[80]={0}; int fd=open(APP "/validation-owner",O_RDONLY|O_NOFOLLOW);
    if(fd<0)return 0;
    ssize_t got=read(fd,text,sizeof(text)); int closed=close(fd);
    return !closed&&got==(ssize_t)strlen(OWNER_NONCE)&&bytes_equal(text,OWNER_NONCE,(size_t)got);
}
static int directory(const char *path,unsigned owner) {
    GuardedStat g; initialize(&g);
    return !lstat(path,&g.value)&&intact(&g)&&S_ISDIR(g.value.st_mode)&&g.value.st_uid==owner&&
           g.value.st_gid==0&&(g.value.st_mode&07777)==0755;
}
static int prepare(void) {
    return marker_matches()&&directory(APP,1)&&directory(APP "/web",1)&&
           !chown(APP,0,0)&&!chown(APP "/web",0,0)&&directory(APP,0)&&directory(APP "/web",0);
}
static int regular_mode(const char *name) {
    char path[512]; int n=snprintf(path,sizeof(path),APP "/%s",name);
    if(n<0||(size_t)n>=sizeof(path))return 0;
    int fd=open(path,O_RDONLY|O_NOFOLLOW); if(fd<0)return 0;
    GuardedStat g; initialize(&g);
    int ok=!fstat(fd,&g.value)&&intact(&g)&&S_ISREG(g.value.st_mode)&&g.value.st_uid==0&&
           g.value.st_gid==0&&g.value.st_nlink==1&&!(g.value.st_mode&07000)&&!fchmod(fd,0644);
    if(close(fd))ok=0;
    return ok;
}
static int finalize_parent(void) {
    GuardedStat root,web; initialize(&root); initialize(&web);
    if(!marker_matches()||lstat(APP,&root.value)||lstat(APP "/web",&web.value)||!intact(&root)||!intact(&web))return 0;
    if(!S_ISDIR(root.value.st_mode)||!S_ISDIR(web.value.st_mode)||root.value.st_uid||web.value.st_uid||
       root.value.st_gid||web.value.st_gid||(root.value.st_mode&07000)||(web.value.st_mode&07000))return 0;
    const char *files[]={"app.json","development.json","validation-owner","web/index.html","web/app.js","web/style.css"};
    for(unsigned i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!regular_mode(files[i]))return 0;
    if(chmod(APP "/web",0755)||chmod(APP,0755)||chown(APP "/web",1,0)||chown(APP,1,0))return 0;
    return directory(APP,1)&&directory(APP "/web",1);
}
static int model_directory(int normalize,FILE *log) {
    int directory_fd=open(MODEL,O_RDONLY|O_DIRECTORY|O_NOFOLLOW);
    if(directory_fd<0)return 0;
    GuardedStat dir; initialize(&dir);
    int ok=!fstat(directory_fd,&dir.value)&&intact(&dir)&&S_ISDIR(dir.value.st_mode)&&
           dir.value.st_uid==0&&dir.value.st_gid==0&&!(dir.value.st_mode&07000);
    int marker_fd=-1;
    if(ok)marker_fd=open(MODEL "/.qwen-transfer-owner.json",O_RDONLY|O_NOFOLLOW);
    if(marker_fd<0)ok=0;
    GuardedStat marker; initialize(&marker);
    static const char expected[]=MODEL_MARKER;
    char text[4097];
    if(sizeof(expected)>sizeof(text))ok=0;
    if(ok)ok=!fstat(marker_fd,&marker.value)&&intact(&marker)&&S_ISREG(marker.value.st_mode)&&
        marker.value.st_uid==0&&marker.value.st_gid==0&&marker.value.st_nlink==1&&
        !(marker.value.st_mode&07000)&&marker.value.st_size==(off_t)(sizeof(expected)-1);
    if(ok){
        size_t used=0;
        while(used<sizeof(expected)-1){
            ssize_t got=read(marker_fd,text+used,sizeof(expected)-1-used);
            if(got<=0){ok=0;break;}
            used+=(size_t)got;
        }
        if(ok)ok=read(marker_fd,text+used,1)==0&&bytes_equal(text,expected,sizeof(expected)-1);
    }
    if(ok&&normalize)ok=!fchmod(marker_fd,0644)&&!fchmod(directory_fd,0755);
    if(ok){
        initialize(&dir); initialize(&marker);
        ok=!fstat(directory_fd,&dir.value)&&!fstat(marker_fd,&marker.value)&&intact(&dir)&&intact(&marker)&&
           S_ISDIR(dir.value.st_mode)&&dir.value.st_uid==0&&dir.value.st_gid==0&&(dir.value.st_mode&07777)==0755&&
           S_ISREG(marker.value.st_mode)&&marker.value.st_uid==0&&marker.value.st_gid==0&&
           marker.value.st_nlink==1&&(marker.value.st_mode&07777)==0644;
    }
    if(marker_fd>=0&&close(marker_fd))ok=0;
    if(close(directory_fd))ok=0;
    if(ok&&log)fprintf(log,"MODEL_DIRECTORY uid=%u gid=%u mode=%04o marker_bytes=%llu no_symlinks=1 marker_verified=1\n",
        (unsigned)dir.value.st_uid,(unsigned)dir.value.st_gid,(unsigned)(dir.value.st_mode&07777),
        (unsigned long long)marker.value.st_size);
    return ok;
}
int main(int argc,char **argv) {
    if(argc!=2||(strcmp(argv[1],"prepare")&&strcmp(argv[1],"finalize")&&strcmp(argv[1],"verify")))return 2;
    char path[256]; int length=snprintf(path,sizeof(path),LOG_PREFIX "-%s.log",argv[1]);
    if(length<0||(size_t)length>=sizeof(path))return 2;
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644); if(fd<0)return 3;
    FILE *log=fdopen(fd,"w"); if(!log){close(fd);return 3;}
    fprintf(log,"BEGIN mode=%s uid=%u euid=%u GPU_calls=0 title_launches=0\n",argv[1],getuid(),geteuid());
    int ok=persist(log)&&getuid()==1&&geteuid()==0;
    if(ok){
        if(!strcmp(argv[1],"prepare"))ok=prepare();
        else if(!strcmp(argv[1],"finalize"))ok=marker_matches()&&directory(APP,0)&&directory(APP "/web",0)&&
            model_directory(1,log)&&finalize_parent()&&model_directory(0,log);
        else ok=marker_matches()&&directory(APP,1)&&directory(APP "/web",1)&&model_directory(0,log);
    }
    fprintf(log,"END success=%d mode=%s parent_ownership_restored=%d GPU_calls=0 title_launches=0\n",
            ok,argv[1],ok&&strcmp(argv[1],"prepare")!=0);
    if(!persist(log)||fclose(log))ok=0;
    return ok?0:1;
}

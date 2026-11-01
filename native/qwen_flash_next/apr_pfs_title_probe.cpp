// SPDX-License-Identifier: GPL-3.0-or-later
// Native visibility and APR identity for the newly created PFS control only.
#include <cstdarg>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include "apr_title_context.h"
extern "C" int sceKernelAprResolveFilepathsToIds(const char*const*,uint32_t,uint32_t*,uint32_t*);
extern "C" int sceKernelAprGetFileSize(uint32_t,uint64_t*);
namespace {
int journal=-1;bool healthy=true;unsigned logged=0;
bool report(const char*format,...){
    if(journal<0)journal=open(APR_TITLE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0||!healthy)return false;
    char line[1024];va_list ap;va_start(ap,format);int n=vsnprintf(line,sizeof(line)-1,format,ap);va_end(ap);
    if(n<0||n>=int(sizeof(line)-1)||logged>65536u-unsigned(n)-1u){healthy=false;return false;}
    line[n++]='\n';if(write(journal,line,n)!=n||fsync(journal)){healthy=false;return false;}logged+=unsigned(n);return true;
}
constexpr uint64_t guard=UINT64_C(0xa712953a45b820e6);
unsigned char reference[16384];
}
extern "C" void qwen_native_stage(const char*stage){report("STAGE text=%s",stage);}
extern "C" void qwen_native_trace_initializer(size_t index,uintptr_t,bool returned){report("INITIALIZER index=%zu returned=%d",index,returned);}
extern "C" void catchReturnFromMain(int result){report("RETURN result=%d ordinary_exit=1",result);if(journal>=0){close(journal);journal=-1;}}
int main(int,char**){
    int ok=0,visible=0,resolved=0;
    if(!report("BEGIN nonce=%s pid=%d ppid=%d uid=%u euid=%u scope=new_PFS_control GPU_calls=0 APR_read_submits=0",APR_TITLE_NONCE,getpid(),getppid(),getuid(),geteuid()))return 2;
    do{
        const char*path=APR_PFS_FILE;
#ifdef APR_PFS_VIEW_DIR
        if(mkdir(APR_PFS_VIEW_DIR,0755)||!report("PFS_VIEW_WAIT ready=1 maximum_ms=30000"))break;
        // The host attaches only the owned PFS root to this existing sandbox.
        // The wait has a deadline and never submits I/O to APR or the GPU.
        for(unsigned attempt=0;attempt<300;++attempt){
            int probe=open(path,O_RDONLY|O_NOFOLLOW);if(probe>=0){close(probe);break;}usleep(100000);
        }
#endif
        errno=0;int fd=open(path,O_RDONLY|O_NOFOLLOW),open_error=errno;ssize_t got=-1;int closed=-1;
        if(fd>=0){got=read(fd,reference,sizeof(reference));closed=close(fd);}
        visible=got==sizeof(reference)&&closed==0;
        if(visible)for(unsigned i=0;i<sizeof(reference);++i)visible&=reference[i]==static_cast<unsigned char>(((i*17+29)^(i>>8))&255);
        if(!report("PFS_NATIVE_ACCESS path=%s opened=%d errno=%d bytes=%lld close_rc=%d exact=%d",path,fd>=0,open_error,(long long)got,closed,visible)||!visible)break;
        struct{uint64_t a;uint32_t value,pad;uint64_t b;} id{guard,UINT32_MAX,0,guard},failed{guard,UINT32_MAX,0,guard};
        if(!report("BEFORE_PFS_RESOLVE"))break;
        errno=0;int rc=sceKernelAprResolveFilepathsToIds(&path,1,&id.value,&failed.value),error=errno;
        bool intact=id.a==guard&&id.b==guard&&!id.pad&&failed.a==guard&&failed.b==guard&&!failed.pad;
        if(!report("PFS_NATIVE_RESOLVE rc=%d errno=%d id=%u error_index=%u canaries=%d",rc,error,id.value,failed.value,intact)||!intact)break;
        if(!rc){
            struct{uint64_t a,value,b;} size{guard,0,guard};errno=0;int sr=sceKernelAprGetFileSize(id.value,&size.value),se=errno;
            bool exact=size.a==guard&&size.b==guard;
            if(!report("PFS_NATIVE_SIZE rc=%d errno=%d bytes=%llu canaries=%d",sr,se,(unsigned long long)size.value,exact)||sr||!exact||size.value!=sizeof(reference))break;
            resolved=1;
        }
        ok=1;
    }while(false);
    if(!report("END nonce=%s success=%d visible=%d resolved=%d APR_read_submits=0 GPU_calls=0",APR_TITLE_NONCE,ok,visible,resolved))ok=0;
#ifdef APR_PFS_VIEW_DIR
    usleep(500000);
#endif
    return ok?0:1;
}

// SPDX-License-Identifier: GPL-3.0-or-later
// A direct PFS control probe; the supervisor detaches before native return.
#include <cstdarg>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <time.h>
#include "apr_title_context.h"
#include "apr_direct_control.h"
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
uint64_t now(){timespec t{};return clock_gettime(CLOCK_MONOTONIC,&t)?0:uint64_t(t.tv_sec)*1000000u+uint64_t(t.tv_nsec)/1000u;}
bool access_control(int fd,apr_direct_control&c,int stage=0){
    if(flock(fd,LOCK_EX))return false;
    bool ok=pread(fd,&c,sizeof(c),0)==sizeof(c)&&c.magic==APR_DIRECT_MAGIC&&!memcmp(c.nonce,APR_TITLE_NONCE,32)&&c.pid==uint64_t(getpid())&&!c.reserved;
    if(ok&&stage){c.stage=uint32_t(stage);ok=pwrite(fd,&c,sizeof(c),0)==sizeof(c)&&!fsync(fd);}
    if(flock(fd,LOCK_UN))ok=false;return ok;
}
constexpr uint64_t guard=UINT64_C(0xa712953a45b820e6);
}
extern "C" void qwen_native_stage(const char*s){report("STAGE text=%s",s);}
extern "C" void qwen_native_trace_initializer(size_t i,uintptr_t,bool returned){report("INITIALIZER index=%zu returned=%d",i,returned);}
extern "C" void catchReturnFromMain(int rc){report("RETURN result=%d ordinary_exit=1",rc);if(journal>=0){close(journal);journal=-1;}}
int main(int,char**){
    int ok=0,visible=0,resolved=0,status=-1;bool claimed=false,detached=false,owned_dir=false;apr_direct_control control{};
    if(!report("BEGIN nonce=%s pid=%d ppid=%d uid=%u euid=%u scope=direct_PFS_control GPU_calls=0 APR_read_submits=0",APR_TITLE_NONCE,getpid(),getppid(),getuid(),geteuid()))return 2;
    do{
        if(mkdir(APR_DIRECT_DIR,0755))break;owned_dir=true;
        status=open(APR_DIRECT_STATUS,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0666);if(status<0||fchmod(status,0666))break;
        control.magic=APR_DIRECT_MAGIC;memcpy(control.nonce,APR_TITLE_NONCE,32);control.pid=uint64_t(getpid());control.stage=APR_DIRECT_READY;
        if(write(status,&control,sizeof(control))!=sizeof(control)||fsync(status)||!report("DIRECT_PFS_WAIT ready=1 maximum_prepare_us=30000000"))break;
        uint64_t started=now(),deadline=started+30000000,abort_deadline=0;if(!started)break;
        for(unsigned poll=0;poll<3000;++poll){
            if(!access_control(status,control))break;
            claimed|=control.stage!=APR_DIRECT_READY;
            if(control.stage==APR_DIRECT_MOUNTED||control.stage==APR_DIRECT_DETACHED)break;
            if(now()>=deadline){
                // Claim and cancellation use the same lock, so an unclaimed
                // timeout cannot race a late mount after this process returns.
                if(flock(status,LOCK_EX))break;
                bool valid=pread(status,&control,sizeof(control),0)==sizeof(control);
                if(valid&&control.stage==APR_DIRECT_READY){control.stage=APR_DIRECT_ABORT;valid=pwrite(status,&control,sizeof(control),0)==sizeof(control)&&!fsync(status);claimed=false;flock(status,LOCK_UN);break;}
                if(valid){control.stage=APR_DIRECT_ABORT;pwrite(status,&control,sizeof(control),0);fsync(status);claimed=true;}
                flock(status,LOCK_UN);report("DIRECT_PFS_ABORT waiting_for_owned_detach=1");deadline=UINT64_MAX;abort_deadline=now()+30000000;
            }
            if(abort_deadline&&now()>=abort_deadline){report("DIRECT_PFS_TIMEOUT phase=prepare supervisor_cleanup_required=1");break;}
            usleep(20000);
        }
        if(control.stage!=APR_DIRECT_MOUNTED)break;
        struct statfs fs{};unsigned char data[16384];const char*path=APR_PFS_FILE;errno=0;int fd=open(path,O_RDONLY|O_NOFOLLOW),error=errno;ssize_t got=-1;int close_rc=-1;
        if(fd>=0){got=read(fd,data,sizeof(data));close_rc=close(fd);}
        visible=got==sizeof(data)&&close_rc==0;
        for(unsigned i=0;visible&&i<sizeof(data);++i)visible=data[i]==static_cast<unsigned char>(((i*17+29)^(i>>8))&255);
        if(!report("DIRECT_PFS_ACCESS opened=%d errno=%d bytes=%lld close_rc=%d exact=%d",fd>=0,error,(long long)got,close_rc,visible)||!visible||statfs(APR_DIRECT_DIR,&fs))break;
        if(!report("DIRECT_PFS_FILESYSTEM name=%s type=%u target=%s",fs.f_fstypename,fs.f_type,fs.f_mntonname)||strncmp(fs.f_fstypename,"pfs",3))break;
        struct{uint64_t a;uint32_t value,pad;uint64_t b;} id{guard,UINT32_MAX,0,guard},failed{guard,UINT32_MAX,0,guard};
        if(!report("BEFORE_DIRECT_PFS_RESOLVE"))break;errno=0;int rc=sceKernelAprResolveFilepathsToIds(&path,1,&id.value,&failed.value),saved=errno;
        bool intact=id.a==guard&&id.b==guard&&!id.pad&&failed.a==guard&&failed.b==guard&&!failed.pad;
        if(!report("DIRECT_PFS_RESOLVE rc=%d errno=%d id=%u error_index=%u canaries=%d",rc,saved,id.value,failed.value,intact)||!intact)break;
        if(!rc){struct{uint64_t a,value,b;} size{guard,0,guard};errno=0;int sr=sceKernelAprGetFileSize(id.value,&size.value),se=errno;
            if(!report("DIRECT_PFS_SIZE rc=%d errno=%d bytes=%llu canaries=%d",sr,se,(unsigned long long)size.value,size.a==guard&&size.b==guard)||sr||size.value!=sizeof(data)||size.a!=guard||size.b!=guard)break;resolved=1;}
        ok=1;
    }while(false);
    if(status>=0&&claimed){
        if(control.stage!=APR_DIRECT_DETACHED&&access_control(status,control,APR_DIRECT_NATIVE_CLOSED))report("DIRECT_PFS_HANDOFF descriptors_closed=1");
        uint64_t deadline=now()+30000000;bool valid=true;
        for(unsigned poll=0;poll<1500;++poll){valid=access_control(status,control);if(!valid||control.stage==APR_DIRECT_DETACHED||now()>=deadline)break;usleep(20000);}
        detached=valid&&control.stage==APR_DIRECT_DETACHED;
        if(!report("DIRECT_PFS_DETACHED acknowledged=%d supervisor_error=%u",detached,control.error)||!detached||control.error)ok=0;
    }
    if(status>=0){if(close(status))ok=0;if((!claimed||detached)&&unlink(APR_DIRECT_STATUS))ok=0;}
    if(!claimed&&owned_dir){if(rmdir(APR_DIRECT_DIR))ok=0;}
    if(!report("END nonce=%s success=%d visible=%d resolved=%d detached=%d APR_read_submits=0 GPU_calls=0",APR_TITLE_NONCE,ok,visible,resolved,detached))ok=0;
    return ok?0:1;
}

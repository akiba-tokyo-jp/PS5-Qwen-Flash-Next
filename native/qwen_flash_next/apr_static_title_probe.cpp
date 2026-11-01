// SPDX-License-Identifier: GPL-3.0-or-later
// Native static APR imports and public-source command construction; no GPU.
#include <cstdarg>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <fcntl.h>
#include <unistd.h>
#include "apr_title_context.h"
#include "apr_command_encoder.h"
extern "C" int sceKernelAprResolveFilepathsToIds(const char*const*,uint32_t,uint32_t*,uint32_t*);
extern "C" int sceKernelAprGetFileSize(uint32_t,uint64_t*);
namespace {
int journal=-1;bool healthy=true;unsigned logged=0;
bool report(const char*format,...){
    if(journal<0)journal=open(APR_TITLE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(journal<0||!healthy)return false;
    char line[1024];va_list ap;va_start(ap,format);int n=vsnprintf(line,sizeof(line)-1,format,ap);va_end(ap);
    if(n<0||n>=int(sizeof(line)-1)||logged>65536u-unsigned(n)-1u){healthy=false;return false;}
    line[n++]='\n';if(write(journal,line,n)!=n||fsync(journal)){healthy=false;return false;}logged+=unsigned(n);return true;
}
constexpr uint64_t guard=UINT64_C(0x8d45115aab3e6117);
alignas(16384) unsigned char command[4096],target[16384];
}
extern "C" void qwen_native_stage(const char*stage){report("STAGE text=%s",stage);}
extern "C" void qwen_native_trace_initializer(size_t index,uintptr_t,bool returned){report("INITIALIZER index=%zu returned=%d",index,returned);}
extern "C" void catchReturnFromMain(int result){report("RETURN result=%d ordinary_exit=1",result);if(journal>=0){close(journal);journal=-1;}}
int main(int,char**){
    int ok=0;unsigned valid=0;uint32_t control_id=UINT32_MAX;bool packed=false;
    if(!report("BEGIN nonce=%s pid=%d ppid=%d uid=%u euid=%u GPU_calls=0 model_loaded=0 APR_read_submits=0",APR_TITLE_NONCE,getpid(),getppid(),getuid(),geteuid()))return 2;
    do{
        if(!report("ENV log_in_app0=1 boot_checked_in_launcher=1 registered_title_via_OS_launch=1")||
           !report("APR_NATIVE_BINDING mode=loader_static_import resolver=%p size=%p",reinterpret_cast<void*>(sceKernelAprResolveFilepathsToIds),reinterpret_cast<void*>(sceKernelAprGetFileSize)))break;
        const char*paths[]={"/app0/eboot.bin",APR_CONTROL_FILE,APR_EXPERT_FILE};
        if(!report("BEFORE_NATIVE_ERRNO"))break;
        int*native_errno=__error();
        if(!report("NATIVE_ERRNO available=%d",native_errno!=nullptr))break;
        for(unsigned i=0;i<3;++i){
            if(!report("BEFORE_POSIX_ACCESS index=%u",i))break;
            if(native_errno)*native_errno=0;int fd=open(paths[i],O_RDONLY|O_NOFOLLOW);int open_error=native_errno?*native_errno:-1;
            unsigned char first[16];ssize_t got=-1;int read_error=0,closed=0;
            if(fd>=0){if(native_errno)*native_errno=0;got=read(fd,first,sizeof(first));read_error=native_errno?*native_errno:-1;closed=close(fd);}
            bool bytes_exact=true;if(i==1&&got==16)for(unsigned j=0;j<16;++j)bytes_exact&=first[j]==static_cast<unsigned char>(j*17+29);
            if(!report("POSIX_ACCESS index=%u opened=%d open_errno=%d read_bytes=%lld read_errno=%d close_rc=%d control_bytes_exact=%d",i,fd>=0,open_error,(long long)got,read_error,closed,bytes_exact))break;
            struct{uint64_t a;uint32_t value,pad;uint64_t b;} id{guard,UINT32_MAX,0,guard},failed{guard,UINT32_MAX,0,guard};
            if(!report("BEFORE_RESOLVE index=%u path=%s",i,paths[i]))break;
            if(native_errno)*native_errno=0;int rc=sceKernelAprResolveFilepathsToIds(paths+i,1,&id.value,&failed.value),error=native_errno?*native_errno:-1;
            bool intact=id.a==guard&&id.b==guard&&!id.pad&&failed.a==guard&&failed.b==guard&&!failed.pad;
            if(!report("RESOLVE index=%u rc=%d errno=%d id=%u error_index=%u canaries=%d errno_measured=%d",i,rc,error,id.value,failed.value,intact,native_errno!=nullptr)||!intact)return 3;
            if(!rc){struct{uint64_t a,value,b;} size{guard,0,guard};
                int sr=sceKernelAprGetFileSize(id.value,&size.value);
                bool exact=size.a==guard&&size.b==guard;
                if(!report("FILE_SIZE index=%u rc=%d bytes=%llu canaries=%d",i,sr,(unsigned long long)size.value,exact)||sr||!exact)return 4;
                if(i==1){if(size.value!=16384)return 5;control_id=id.value;}++valid;}
        }
        struct{uint64_t a;qwen_app::AprCommandBuffer cb;uint64_t b;} cb{guard,{},guard};volatile uint64_t completion=0;
        uint32_t id=control_id!=UINT32_MAX?control_id:0x12345678u;
        packed=qwen_app::apr_bind(cb.cb,command,sizeof(command))&&qwen_app::apr_read(cb.cb,id,target,sizeof(target),0)&&
            cb.cb.offset==20&&cb.cb.commands==1&&qwen_app::apr_completion(cb.cb,&completion,0x1357)&&cb.cb.commands==2&&
            cb.cb.offset==32&&cb.a==guard&&cb.b==guard&&completion==0;
        if(!report("WRITER backend=public_source exact=%d commands=%d bytes=%u synthetic_ID=%d APR_read_submits=0",packed,cb.cb.commands,cb.cb.offset,control_id==UINT32_MAX))break;
        ok=packed;
    }while(false);
    if(!report("END nonce=%s success=%d resolved_files=%u writer_exact=%d APR_read_submits=0 GPU_calls=0 model_loaded=0 system_module_loads=0",APR_TITLE_NONCE,ok,valid,packed))ok=0;
    return ok?0:1;
}

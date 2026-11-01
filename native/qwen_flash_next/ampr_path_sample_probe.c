/* SPDX-License-Identifier: GPL-3.0-or-later
 * Resolve fixed existing APR paths; capture bounded original Expert samples.
 */
#define main qualified_recovery_original_main
#include "qualified_recovery_guard.c"
#undef main
#include <dlfcn.h>
#include <sys/stat.h>
#include "sha256.h"
static int unchanged(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
#include "launch_integrity_native.h"
#include "current_files.h"
#include "sample_sources.h"
static unsigned char window[65536] __attribute__((aligned(16384)));
static int context(unsigned phase){if(!boot(phase)||!idle(phase))return 0;for(size_t i=0;i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i)if(!service(expected_processes+i,phase))return 0;return boot(phase);}
static int identity(const struct stat*s,const uint64_t expected[10]){
    const uint64_t key[]={s->st_dev,s->st_ino,s->st_mode,s->st_uid,s->st_gid,(uint64_t)s->st_size,s->st_mtim.tv_sec,s->st_mtim.tv_nsec,s->st_ctim.tv_sec,s->st_ctim.tv_nsec};
    return S_ISREG(s->st_mode)&&!memcmp(key,expected,sizeof(key));
}
static int copy_sample(int output,unsigned index){
    const struct sample_source *s=samples+index;struct stat before,after;
    int fd=open(s->path,O_RDONLY|O_NOFOLLOW|O_DIRECT);if(fd<0)return 0;
    int ok=(fcntl(fd,F_GETFL)&O_DIRECT)&&!fstat(fd,&before)&&identity(&before,s->key);
    struct ai_sha256 hash;ai_sha256_init(&hash);
    for(size_t at=0;ok&&at<1540096;){size_t n=1540096-at;if(n>sizeof(window))n=sizeof(window);
        ssize_t got=pread(fd,window,n,(off_t)(s->offset+at));if(got!=(ssize_t)n){ok=0;break;}
        ai_sha256_update(&hash,window,n);if(write(output,window,n)!=(ssize_t)n){ok=0;break;}at+=n;
    }
    ok=ok&&!fstat(fd,&after)&&unchanged(&before,&after);if(close(fd))ok=0;if(fsync(output))ok=0;
    unsigned char digest[32];char hex[65];ai_sha256_final(&hash,digest);for(unsigned i=0;i<32;++i){hex[i*2]="0123456789abcdef"[digest[i]>>4];hex[i*2+1]="0123456789abcdef"[digest[i]&15];}hex[64]=0;
    return report("SAMPLE index=%u ordinal=%u bytes=1540096 exact=%d sha256=%s",index,s->ordinal,ok,hex)&&ok;
}
int main(int argc,char **argv){
    (void)argv;if(argc!=0&&argc!=1)return 2;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(journal<0)return 3;
    int ok=0,out=-1;unsigned captured=0;
    if(!report("BEGIN nonce=%s pid=%d CPU_only=1 GPU_calls=0 title_launches=0 IO_submits=0 module_loads=0",RECOVERY_NONCE,getpid())||getuid()!=1||geteuid()!=0||!context(1))goto done;
    for(size_t i=0;i<sizeof(files)/sizeof(files[0]);++i)if(!qwen_launch_digest_matches(files[i].path,files[i].bytes,files[i].hash))goto done;
    typedef int(*resolve_fn)(const char*const*,uint32_t,uint32_t*,uint32_t*);
    typedef int(*size_fn)(uint32_t,uint64_t*);
    resolve_fn resolve=(resolve_fn)dlsym(RTLD_DEFAULT,"sceKernelAprResolveFilepathsToIds");
    size_fn get_size=(size_fn)dlsym(RTLD_DEFAULT,"sceKernelAprGetFileSize");
    if(!resolve||!get_size)goto done;
    const char*paths[]={files[0].path,"/system_ex/app/PPSA99190/eboot.bin",samples[0].path};
    for(unsigned i=0;i<3;++i){
        struct{uint64_t a;uint32_t value,pad;uint64_t b;} id={GUARD,0xffffffffu,0,GUARD},error={GUARD,0xffffffffu,0,GUARD};
        if(!report("BEFORE_APR_RESOLVE index=%u attempts=1",i))goto done;
        errno=0;int rc=resolve(paths+i,1,&id.value,&error.value),saved=errno;
        int intact=id.a==GUARD&&id.b==GUARD&&!id.pad&&error.a==GUARD&&error.b==GUARD&&!error.pad;
        if(!report("APR_RESOLVE index=%u rc=%d hex_rc=0x%08x errno=%d file_id=%u error_index=%u canaries=%d",i,rc,(unsigned)rc,saved,id.value,error.value,intact)||!intact)goto done;
        if(!rc){struct{uint64_t a,value,b;} size={GUARD,0,GUARD};errno=0;int sr=get_size(id.value,&size.value),se=errno;
            intact=size.a==GUARD&&size.b==GUARD;
            if(!report("APR_SIZE index=%u rc=%d errno=%d bytes=%llu canaries=%d",i,sr,se,(unsigned long long)size.value,intact)||!intact)goto done;}
    }
    out=open(SAMPLE_OUTPUT,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0644);if(out<0)goto done;
    if(!(fcntl(out,F_GETFL)&O_DIRECT))goto done;
    for(unsigned i=0;i<sizeof(samples)/sizeof(samples[0]);++i){if(!copy_sample(out,i))goto done;++captured;}
    if(close(out)){out=-1;goto done;}out=-1;
    if(!context(2))goto done;ok=1;
done:
    if(out>=0&&close(out))ok=0;
    if(!report("END nonce=%s success=%d samples=%u IO_submits=0 GPU_calls=0 title_launches=0 module_loads=0 no_retry=1",RECOVERY_NONCE,ok,captured))ok=0;
    if(close(journal))ok=0;return ok?0:1;
}

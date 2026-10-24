/* SPDX-License-Identifier: MIT
 * Read-only VM metadata for one positively identified CPU-idle title.
 * No process memory reads, mapping changes, model payload, GPU or close calls.
 */
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <sys/sysctl.h>
#include <sys/user.h>
#include <unistd.h>
#include "vmmap_metadata.h"
#include "vmmap_probe_context.h"
typedef struct {uint32_t app_id;uint64_t reserved;char title_id[14];char tail[0x3c];} app_info;
_Static_assert(sizeof(struct kinfo_proc)==1096,"Qualified PS5 process ABI requires the priority overlay");
_Static_assert(sizeof(app_info)==96&&offsetof(app_info,title_id)==16,"Qualified AppInfo ABI");
_Static_assert(offsetof(struct kinfo_vmentry,kve_path)==sizeof(struct qwen_vmmap_prefix),"Public SDK packed map prefix");
_Static_assert(offsetof(struct kinfo_vmentry,kve_resident)==offsetof(struct qwen_vmmap_prefix,resident),"Public SDK resident field");
int sceKernelGetAppInfo(int,app_info*);
int sceSystemServiceGetAppId(const char*);
int sceSystemServiceGetAppIdOfRunningBigApp(void);
static FILE *output;
static struct {unsigned char before[64],data[QWEN_VMMAP_CAPACITY],after[64];} buffer;
static int vmmap_pending=0,vmmap_calls=0,vmmap_supported=0,vmmap_parsed=0;
static unsigned vmmap_records=0;
static int report(const char*format,...) {
    va_list args;va_start(args,format);int ok=vfprintf(output,format,args)>=0;va_end(args);
    return ok&&fputc('\n',output)!=EOF&&!fflush(output)&&!fsync(fileno(output));
}
static int guards(void){for(unsigned i=0;i<64;++i)if(buffer.before[i]!=0xa5||buffer.after[i]!=0xa5)return 0;return 1;}
static int64_t number(const char*text){char*end=NULL;errno=0;int64_t n=strtoll(text,&end,10);return errno||!*text||*end||n<0?-1:n;}
static int owner(int pid,int64_t seconds,int64_t usec,int64_t app_id) {
    struct {uint64_t before[2];unsigned char data[4096];uint64_t after[2];} p={0};
    p.before[0]=p.before[1]=p.after[0]=p.after[1]=UINT64_C(0x6a7b83c44d29e510);
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PID,pid};size_t size=sizeof(p.data);
    errno=0;int rc=sysctl(mib,4,p.data,&size,NULL,0),error=errno;
    int intact=p.before[0]==p.before[1]&&p.before[0]==p.after[0]&&p.before[0]==p.after[1]&&p.before[0]==UINT64_C(0x6a7b83c44d29e510);
    if(!report("OWNER_PROC_RETURNED rc=%d errno=%d bytes=%zu expected_bytes=%zu canaries=%d",rc,error,size,sizeof(struct kinfo_proc),intact)||rc||size!=sizeof(struct kinfo_proc)||!intact)return 0;
    struct kinfo_proc k;memcpy(&k,p.data,sizeof(k));
    if(k.ki_structsize!=sizeof(k)||k.ki_pid!=pid||k.ki_uid!=1||k.ki_start.tv_sec!=seconds||k.ki_start.tv_usec!=usec||
       !memchr(k.ki_comm,0,sizeof(k.ki_comm))||strcmp(k.ki_comm,"eboot.bin"))return report("OWNER_PROC_IDENTITY exact=0")&&0;
    struct {uint64_t before;app_info app;uint64_t after;} a={0};a.before=a.after=UINT64_C(0x5af1932e74168c02);
    rc=sceKernelGetAppInfo(pid,&a.app);
    int app_exact=!rc&&a.before==a.after&&a.before==UINT64_C(0x5af1932e74168c02)&&
        memchr(a.app.title_id,0,sizeof(a.app.title_id))&&!strcmp(a.app.title_id,"PPSA99190")&&a.app.app_id==app_id&&
        sceSystemServiceGetAppId(a.app.title_id)==app_id&&sceSystemServiceGetAppIdOfRunningBigApp()==app_id;
    return report("OWNER_APP_RETURNED rc=%d exact=%d",rc,app_exact)&&app_exact;
}
static int boot_and_headroom(void) {
    struct {uint64_t before;struct timeval boot;uint64_t after;} b={0};b.before=b.after=UINT64_C(0x725b725b725b725b);size_t size=sizeof(b.boot);
    errno=0;int rc=sysctlbyname("kern.boottime",&b.boot,&size,NULL,0),error=errno;
    int boot_exact=!rc&&size==sizeof(b.boot)&&b.before==b.after&&b.before==UINT64_C(0x725b725b725b725b)&&b.boot.tv_sec==VMMAP_BOOT_SEC&&b.boot.tv_usec==VMMAP_BOOT_USEC;
    if(!report("BOOT_RETURNED rc=%d errno=%d bytes=%zu exact=%d",rc,error,size,boot_exact)||!boot_exact)return 0;
    uint32_t values[4]={0};const char *names[]={"hw.pagesize","vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved"};
    for(unsigned i=0;i<4;++i){size=4;errno=0;rc=sysctlbyname(names[i],values+i,&size,NULL,0);error=errno;
        if(!report("HEADROOM_RETURNED index=%u rc=%d errno=%d bytes=%zu value=%u",i,rc,error,size,values[i])||rc||size!=4)return 0;}
    uint64_t reserve=values[3]>256?values[3]:256;
    int admitted=values[0]==16384&&(uint64_t)values[1]>=(uint64_t)values[2]+reserve;
    return report("HEADROOM_ADMISSION free=%u required=%llu exact=%d",values[1],(unsigned long long)((uint64_t)values[2]+reserve),admitted)&&admitted;
}
static int region(void*unused,unsigned n,const struct qwen_vmmap_prefix*p,const unsigned char*path,size_t size) {
    (void)unused;(void)path;
    return report("VMMAP_REGION index=%u type=%d start=0x%llx end=0x%llx offset=0x%llx bytes=%llu resident_pages=%d private_pages=%d protection=%d flags=%d path_bytes=%zu",
        n,p->type,(unsigned long long)p->start,(unsigned long long)p->end,(unsigned long long)p->offset,(unsigned long long)(p->end-p->start),
        p->resident,p->private_resident,p->protection,p->flags,size);
}
static int vmmap_once(int pid) {
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_VMMAP,pid};size_t needed=0;
    if(!report("VMMAP_SIZE_BEFORE"))return 0;
    vmmap_pending=1;errno=0;int rc=sysctl(mib,4,NULL,&needed,NULL,0),error=errno;vmmap_pending=0;++vmmap_calls;
    if(!report("VMMAP_SIZE_RETURNED rc=%d errno=%d bytes=%zu bound=%u",rc,error,needed,QWEN_VMMAP_CAPACITY))return 0;
    if(!rc&&needed&&needed<=QWEN_VMMAP_CAPACITY) {
        vmmap_supported=1;memset(buffer.before,0xa5,64);memset(buffer.after,0xa5,64);size_t bytes=QWEN_VMMAP_CAPACITY;
        if(!report("VMMAP_DATA_BEFORE"))return 0;
        vmmap_pending=1;errno=0;rc=sysctl(mib,4,buffer.data,&bytes,NULL,0);error=errno;vmmap_pending=0;++vmmap_calls;
        if(!report("VMMAP_DATA_RETURNED rc=%d errno=%d bytes=%zu canaries=%d",rc,error,bytes,guards())||!guards())return 0;
        if(!rc&&bytes&&bytes<=QWEN_VMMAP_CAPACITY)vmmap_parsed=qwen_vmmap_parse(buffer.data,bytes,region,NULL,&vmmap_records);
    }
    return 1;
}
int main(int argc,char**argv) {
    if(argc!=5)return 2;int64_t pid=number(argv[1]),seconds=number(argv[2]),usec=number(argv[3]),app=number(argv[4]);
    if(pid<=0||pid>INT32_MAX||seconds<0||usec<0||usec>=1000000||app<=0||app>INT32_MAX)return 2;
    int fd=open(VMMAP_LOG_PATH,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)return 3;
    output=fdopen(fd,"w");if(!output){close(fd);return 3;}
    int ok=0;
    if(!report("BEGIN nonce=%s metadata_only=1 GPU_calls=0 launch_calls=0 close_calls=0",VMMAP_NONCE))goto done;
    unsigned uid=getuid(),euid=geteuid();
    if(!report("CREDENTIALS uid=%u euid=%u exact=%d",uid,euid,uid==1&&euid==0)||uid!=1||euid!=0||!boot_and_headroom()||!owner((int)pid,seconds,usec,app))goto done;
    if(!vmmap_once((int)pid))goto done;
    if(!owner((int)pid,seconds,usec,app))goto done;
    ok=1;
done:
    if(!report("END success=%d nonce=%s query_supported=%d parsed=%d records=%u VM_query_calls=%d all_VM_calls_returned=%d owner_unchanged=%d GPU_calls=0 launch_calls=0 close_calls=0 retries=0",ok,VMMAP_NONCE,vmmap_supported,vmmap_parsed,vmmap_records,vmmap_calls,!vmmap_pending,ok))ok=0;
    if(fclose(output))ok=0;return ok?0:1;
}

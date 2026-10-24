/* SPDX-License-Identifier: GPL-3.0-or-later
 * Recovery-only boot/service/idle guard, derived from the qualified metadata
 * observer and normal-close guards. Never grants title or GPU execution.
 * Does not require or load the optional native compatibility runtime.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/proc.h>
#include <sys/sysctl.h>
#include <sys/time.h>
#include <sys/user.h>
#include <unistd.h>
#include <ps5/kernel.h>
#include "recovery_context.h"

#define GUARD UINT64_C(0x71ac34862ec971ab)
#define MAX_PROCS 512u
_Static_assert(sizeof(struct kinfo_proc)==1096,"Measured PS5 process metadata ABI");
_Static_assert(sizeof(struct timeval)==16,"Measured PS5 boot metadata ABI");
int sceSystemServiceGetAppIdOfRunningBigApp(void);
static int journal=-1,healthy=1;
static size_t written;
static int report(const char *format,...) {
    char line[1024];va_list ap;va_start(ap,format);
    int n=vsnprintf(line,sizeof(line)-1,format,ap);va_end(ap);
    if(!healthy||n<0||(size_t)n>=sizeof(line)-1||written>65536u-(size_t)n-1){healthy=0;return 0;}
    line[n++]='\n';size_t done=0;
    while(done<(size_t)n){ssize_t count=write(journal,line+done,(size_t)n-done);
        if(count<0&&errno==EINTR)continue;
        if(count<=0||(size_t)count>(size_t)n-done){healthy=0;return 0;}done+=(size_t)count;}
    written+=(size_t)n;if(fsync(journal)){healthy=0;return 0;}return 1;
}
static int boot(unsigned phase) {
    struct{uint64_t a;struct timeval value;uint64_t b;} g={GUARD,{0},GUARD};
    struct{uint64_t a;size_t value;uint64_t b;} length={GUARD,sizeof(g.value),GUARD};
    int mib[]={CTL_KERN,KERN_BOOTTIME};
    int rc=sysctl(mib,2,&g.value,&length.value,NULL,0);
    uint32_t fw=kernel_get_fw_version();
    int exact=!rc&&length.value==sizeof(g.value)&&g.a==GUARD&&g.b==GUARD&&length.a==GUARD&&length.b==GUARD&&
        g.value.tv_sec==BOOT_SEC&&g.value.tv_usec==BOOT_USEC&&fw==0x12400009u;
    return report("BOOT phase=%u exact=%d firmware=0x%08x sec=%lld usec=%lld",phase,exact,fw,
        (long long)g.value.tv_sec,(long long)g.value.tv_usec)&&exact;
}
static int service(const struct expected_process *expected,unsigned phase) {
    struct{uint64_t a[2];unsigned char data[4096];uint64_t b[2];} g;
    memset(&g,0,sizeof(g));g.a[0]=g.a[1]=g.b[0]=g.b[1]=GUARD;
    struct{uint64_t a;size_t value;uint64_t b;} length={GUARD,sizeof(g.data),GUARD};
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PID,expected->pid};
    int rc=sysctl(mib,4,g.data,&length.value,NULL,0);
    int intact=g.a[0]==GUARD&&g.a[1]==GUARD&&g.b[0]==GUARD&&g.b[1]==GUARD&&length.a==GUARD&&length.b==GUARD;
    struct kinfo_proc k;memset(&k,0,sizeof(k));
    if(!rc&&intact&&length.value==sizeof(k))memcpy(&k,g.data,sizeof(k));
    int exact=!rc&&intact&&length.value==sizeof(k)&&k.ki_structsize==sizeof(k)&&
        k.ki_pid==expected->pid&&k.ki_ppid==expected->ppid&&k.ki_uid==expected->uid&&
        k.ki_start.tv_sec==expected->sec&&k.ki_start.tv_usec==expected->usec&&
        memchr(k.ki_comm,0,sizeof(k.ki_comm))&&!strcmp(k.ki_comm,expected->name)&&
        !k.ki_tracer&&!(k.ki_flag&P_TRACED)&&(k.ki_stat==SRUN||k.ki_stat==SSLEEP);
    return report("SERVICE phase=%u name=%s exact=%d",phase,expected->name,exact)&&exact;
}
static struct{uint64_t a[2];unsigned char data[MAX_PROCS*sizeof(struct kinfo_proc)];uint64_t b[2];} inventory;
static int idle(unsigned phase) {
    inventory.a[0]=inventory.a[1]=inventory.b[0]=inventory.b[1]=GUARD;
    struct{uint64_t a;size_t value;uint64_t b;} length={GUARD,sizeof(inventory.data),GUARD};
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PROC,0};
    int rc=sysctl(mib,4,inventory.data,&length.value,NULL,0);
    int valid=!rc&&length.value&&length.value<=sizeof(inventory.data)&&length.value%sizeof(struct kinfo_proc)==0&&
        inventory.a[0]==GUARD&&inventory.a[1]==GUARD&&inventory.b[0]==GUARD&&inventory.b[1]==GUARD&&length.a==GUARD&&length.b==GUARD;
    unsigned owners=0;
    if(valid)for(size_t offset=0;offset<length.value;offset+=sizeof(struct kinfo_proc)){
        struct kinfo_proc k;memcpy(&k,inventory.data+offset,sizeof(k));
        if(k.ki_structsize!=sizeof(k)||!memchr(k.ki_comm,0,sizeof(k.ki_comm))){valid=0;break;}
        owners+=(unsigned)!strcmp(k.ki_comm,"eboot.bin");
    }
    int big=sceSystemServiceGetAppIdOfRunningBigApp();
    valid=valid&&!owners&&(big==-1||big==0);
    return report("IDLE phase=%u valid=%d native_owners=%u runningBigApp=%d",phase,valid,owners,big)&&valid;
}
int main(int argc,char **argv) {
    if(argc!=2||strcmp(argv[1],"--recovery-only"))return 2;
    journal=open(RECOVERY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(journal<0)return 3;
    int ok=getuid()==1&&geteuid()==0&&sizeof(expected_processes)/sizeof(expected_processes[0])==7;
    ok=report("BEGIN nonce=%s recovery_only=1 title_execution_permitted=0 GPU_calls=0 model_payload_reads=0",RECOVERY_NONCE)&&ok;
    for(unsigned phase=1;ok&&phase<=2;++phase){
        ok=boot(phase);
        for(size_t i=0;ok&&i<sizeof(expected_processes)/sizeof(expected_processes[0]);++i)ok=service(&expected_processes[i],phase);
        if(ok)ok=idle(phase);
        if(ok)ok=boot(phase);
    }
    if(!report("END nonce=%s success=%d log_healthy=%d services=7 phases=2 native_owners_absent_proven=%d recovery_only=1 title_execution_permitted=0 GPU_calls=0 model_payload_reads=0",RECOVERY_NONCE,ok,healthy,ok))ok=0;
    if(close(journal))ok=0;
    return ok&&healthy?0:1;
}

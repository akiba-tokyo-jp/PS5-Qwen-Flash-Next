/* SPDX-License-Identifier: MIT
 * One bounded metadata observation of the already identified idle services.
 * No process memory reads, source payload I/O, mappings, allocation pressure,
 * service changes, title operations or GPU work.
 */
#include "vmmap_metadata.h"
struct idle_vm_summary {
    uint64_t virtual_bytes,resident_pages,private_pages,file_virtual_bytes,file_resident_pages;
    unsigned entries,file_entries;
};
static int idle_vm_region(void*context,unsigned ordinal,const struct qwen_vmmap_prefix*p,const unsigned char*path,size_t n){
    (void)ordinal;(void)path;
    struct idle_vm_summary*s=context;
    if(p->resident<0||p->private_resident<0||p->end<=p->start||
       UINT64_MAX-s->virtual_bytes<p->end-p->start)return 0;
    s->virtual_bytes+=p->end-p->start;s->resident_pages+=(uint32_t)p->resident;
    s->private_pages+=(uint32_t)p->private_resident;++s->entries;
    if(n&&p->fileid){++s->file_entries;s->file_virtual_bytes+=p->end-p->start;s->file_resident_pages+=(uint32_t)p->resident;}
    return 1;
}
#ifndef QWEN_IDLE_VM_SUMMARY_ONLY
static struct {uint64_t pre[2];unsigned char data[QWEN_VMMAP_CAPACITY];uint64_t post[2];} idle_vm_buffer;
static int idle_service_identity(int pid,const char*name,struct kinfo_proc*out){
    struct {uint64_t pre[2];struct kinfo_proc value;uint64_t post[2];} v;
    memset(&v,0,sizeof(v));v.pre[0]=v.pre[1]=v.post[0]=v.post[1]=UINT64_C(0xc1b96357c1b96357);
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PID,pid};size_t n=sizeof(v.value);errno=0;
    int rc=sysctl(mib,4,&v.value,&n,NULL,0),error=errno;
    int guards=v.pre[0]==UINT64_C(0xc1b96357c1b96357)&&v.pre[1]==v.pre[0]&&v.post[0]==v.pre[0]&&v.post[1]==v.pre[0];
    if(!report("IDLE_SERVICE_PROCESS pid=%d rc=%d errno=%d bytes=%zu guards=%d",pid,rc,error,n,guards)||
       rc||n!=sizeof(v.value)||!guards||v.value.ki_structsize!=sizeof(v.value)||v.value.ki_pid!=pid||
       v.value.ki_uid||!memchr(v.value.ki_comm,0,sizeof(v.value.ki_comm))||strcmp(v.value.ki_comm,name)||
       v.value.ki_tracer||(v.value.ki_flag&P_TRACED))return 0;
    *out=v.value;
    return report("IDLE_SERVICE_RESOURCE pid=%d name=%s start_sec=%lld start_usec=%lld virtual_bytes=%llu RSS_pages=%lld RSS_not_unique_physical=1",
        pid,name,(long long)out->ki_start.tv_sec,(long long)out->ki_start.tv_usec,
        (unsigned long long)out->ki_size,(long long)out->ki_rssize);
}
static int case_retire_completed_images(int*calls){
    static const int pids[]={84,88,89,154};
    static const char*names[]={"elfldr.elf","ftpsrv.elf","websrv.elf","payload"};
    *calls=0;
    if(!report("IDLE_SERVICE_SCOPE targets=4 maximum_VM_queries=8 target_memory_reads=0 mapping_changes=0 source_payload_reads=0 service_changes=0"))return 0;
    for(unsigned i=0;i<4;++i){
        struct kinfo_proc before,after;
        if(!live_context()||!idle()||!qwen_launch_headroom(NULL)||!idle_service_identity(pids[i],names[i],&before))return 0;
        int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_VMMAP,pids[i]};size_t n=0;errno=0;
        if(!report("IDLE_SERVICE_VM_SIZE_BEFORE pid=%d",pids[i]))return 0;
        int rc=sysctl(mib,4,NULL,&n,NULL,0),error=errno;++*calls;
        if(!report("IDLE_SERVICE_VM_SIZE_RETURNED pid=%d rc=%d errno=%d bytes=%zu",pids[i],rc,error,n))return 0;
        if(!rc&&n&&n<=QWEN_VMMAP_CAPACITY){
            const uint64_t guard=UINT64_C(0x3951a7bf3951a7bf);
            idle_vm_buffer.pre[0]=idle_vm_buffer.pre[1]=idle_vm_buffer.post[0]=idle_vm_buffer.post[1]=guard;
            n=sizeof(idle_vm_buffer.data);errno=0;
            if(!report("IDLE_SERVICE_VM_DATA_BEFORE pid=%d",pids[i]))return 0;
            rc=sysctl(mib,4,idle_vm_buffer.data,&n,NULL,0);error=errno;++*calls;
            int intact=idle_vm_buffer.pre[0]==guard&&idle_vm_buffer.pre[1]==guard&&idle_vm_buffer.post[0]==guard&&idle_vm_buffer.post[1]==guard;
            if(!report("IDLE_SERVICE_VM_DATA_RETURNED pid=%d rc=%d errno=%d bytes=%zu guards=%d",pids[i],rc,error,n,intact)||!intact)return 0;
            if(!rc&&n&&n<=sizeof(idle_vm_buffer.data)){
                struct idle_vm_summary summary={0};unsigned records=0;
                int parsed=qwen_vmmap_parse(idle_vm_buffer.data,n,idle_vm_region,&summary,&records);
                if(!report("IDLE_SERVICE_VM_SUMMARY pid=%d parsed=%d entries=%u virtual_bytes=%llu resident_pages=%llu private_pages=%llu file_entries=%u file_resident_pages=%llu RSS_not_unique_physical=1",
                    pids[i],parsed,records,(unsigned long long)summary.virtual_bytes,(unsigned long long)summary.resident_pages,
                    (unsigned long long)summary.private_pages,summary.file_entries,(unsigned long long)summary.file_resident_pages))return 0;
            }
        }
        if(!idle_service_identity(pids[i],names[i],&after)||before.ki_start.tv_sec!=after.ki_start.tv_sec||
           before.ki_start.tv_usec!=after.ki_start.tv_usec)return 0;
    }
    return report("IDLE_SERVICE_COMPLETE read_only=1 all_metadata_calls_returned=1 target_memory_reads=0 mapping_changes=0 service_changes=0");
}
#endif

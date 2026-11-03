/* SPDX-License-Identifier: MIT */
#include <assert.h>
#define QWEN_IDLE_VM_SUMMARY_ONLY 1
#include "idle_service_memory.h"
int main(void){
    struct idle_vm_summary s={0};
    struct qwen_vmmap_prefix p={0};p.start=16384;p.end=49152;p.resident=2;p.private_resident=1;
    assert(idle_vm_region(&s,0,&p,(const unsigned char*)"",0));
    assert(s.entries==1&&s.virtual_bytes==32768&&s.resident_pages==2&&s.file_entries==0);
    p.start=49152;p.end=65536;p.resident=1;p.private_resident=0;p.fileid=9;
    assert(idle_vm_region(&s,1,&p,(const unsigned char*)"/owned",6));
    assert(s.entries==2&&s.resident_pages==3&&s.private_pages==1&&s.file_entries==1&&s.file_resident_pages==1);
    p.resident=-1;assert(!idle_vm_region(&s,2,&p,NULL,0));
    p.resident=1;p.private_resident=-1;assert(!idle_vm_region(&s,2,&p,NULL,0));
    p.private_resident=0;p.end=p.start;assert(!idle_vm_region(&s,2,&p,NULL,0));
    p.end=p.start+16384;s.virtual_bytes=UINT64_MAX-1;assert(!idle_vm_region(&s,2,&p,NULL,0));
    return 0;
}

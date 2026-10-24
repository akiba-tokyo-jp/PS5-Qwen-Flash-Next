/* SPDX-License-Identifier: MIT */
#ifndef QWEN_VMMAP_METADATA_H
#define QWEN_VMMAP_METADATA_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define QWEN_VMMAP_CAPACITY (1u<<20)
#define QWEN_VMMAP_RECORDS 4096u
struct qwen_vmmap_prefix {
    int32_t bytes,type;uint64_t start,end,offset,fileid;uint32_t fsid;
    int32_t flags,resident,private_resident,protection,references,shadows,vnode_type;
    uint64_t vnode_bytes;uint32_t rdev;uint16_t mode,status;int32_t spare[12];
};
_Static_assert(sizeof(struct qwen_vmmap_prefix)==136,"Packed FreeBSD11 VM map prefix");
typedef int(*qwen_vmmap_visit)(void*,unsigned,const struct qwen_vmmap_prefix*,const unsigned char*,size_t);
static int qwen_vmmap_parse(const unsigned char *data,size_t bytes,qwen_vmmap_visit visit,void *context,unsigned *count) {
    size_t at=0;uint64_t previous=0;*count=0;
    if(!data||!bytes||bytes>QWEN_VMMAP_CAPACITY||!visit)return 0;
    while(at<bytes) {
        struct qwen_vmmap_prefix p;
        if(bytes-at<sizeof(p)||*count==QWEN_VMMAP_RECORDS)return 0;
        memcpy(&p,data+at,sizeof(p));
        if(p.bytes<(int32_t)sizeof(p)+1||p.bytes>(int32_t)sizeof(p)+1024||p.bytes%8||
           (size_t)p.bytes>bytes-at||p.start>=p.end||p.start<previous)return 0;
        size_t capacity=(size_t)p.bytes-sizeof(p);
        const unsigned char *path=data+at+sizeof(p),*end=memchr(path,0,capacity);
        if(!end||!visit(context,*count,&p,path,(size_t)(end-path)))return 0;
        previous=p.end;at+=(size_t)p.bytes;++*count;
    }
    return *count>0;
}
#endif

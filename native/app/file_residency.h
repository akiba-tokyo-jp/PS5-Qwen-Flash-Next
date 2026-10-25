/* SPDX-License-Identifier: MIT */
#ifndef QWEN_FILE_RESIDENCY_H
#define QWEN_FILE_RESIDENCY_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define QWEN_RESIDENCY_PAGE 16384u
#define QWEN_RESIDENCY_WINDOW 1048576u
struct qwen_file_residency_ops {
    void *context;
    int (*admit)(void *);
    int (*mark)(void *,unsigned,unsigned);
    void *(*map_none)(void *,uint64_t,size_t);
    int (*query)(void *,const void *,size_t,char *);
    int (*unmap)(void *,void *,size_t);
};
struct qwen_file_residency {
    unsigned maps,queries,unmaps,resident,modified,referenced,pages;
    unsigned pending,live,unsupported;
};
/* Phase 1/2/3 is map/query/unmap; edge 0/1 marks before/returned.
 * Release only an owned mapping after its metadata query returned. A failed
 * release retains ownership and forbids a subsequent map. No fault/read path.
 */
static int qwen_file_residency_scan(const struct qwen_file_residency_ops *o,
                                  uint64_t bytes,unsigned maximum_windows,
                                  struct qwen_file_residency *s) {
    if(!o||!s||!o->admit||!o->mark||!o->map_none||!o->query||!o->unmap||
       !bytes||bytes>128u*1024u*1024u||!maximum_windows||maximum_windows>128||
       s->pending||s->live||s->maps||s->queries||s->unmaps)return 0;
    const uint64_t extent=(bytes+QWEN_RESIDENCY_PAGE-1)/QWEN_RESIDENCY_PAGE*QWEN_RESIDENCY_PAGE;
    if((extent+QWEN_RESIDENCY_WINDOW-1)/QWEN_RESIDENCY_WINDOW>maximum_windows)return 0;
    for(uint64_t offset=0;offset<extent;) {
        const size_t n=(size_t)(extent-offset>QWEN_RESIDENCY_WINDOW?QWEN_RESIDENCY_WINDOW:extent-offset);
        if(!o->admit(o->context)||!o->mark(o->context,1,0))return 0;
        s->pending=1;void *p=o->map_none(o->context,offset,n);s->pending=0;++s->maps;
        s->live=(unsigned)(p!=(void *)(intptr_t)-1);
        if(!o->mark(o->context,1,1))return 0;
        if(!s->live){s->unsupported=1;return 0;}
        struct {uint64_t before[2];char bytes[QWEN_RESIDENCY_WINDOW/QWEN_RESIDENCY_PAGE];uint64_t after[2];} v;
        const uint64_t guard=UINT64_C(0x391a67955c28e341);
        v.before[0]=v.before[1]=v.after[0]=v.after[1]=guard;memset(v.bytes,0,sizeof(v.bytes));
        if(!o->mark(o->context,2,0))return 0;
        s->pending=1;int rc=o->query(o->context,p,n,v.bytes);s->pending=0;++s->queries;
        int marked=o->mark(o->context,2,1);
        int valid=!rc&&marked&&v.before[0]==guard&&v.before[1]==guard&&v.after[0]==guard&&v.after[1]==guard;
        for(unsigned i=0;i<n/QWEN_RESIDENCY_PAGE&&valid;++i)if((unsigned char)v.bytes[i]&~0x3fu)valid=0;
        for(unsigned i=(unsigned)(n/QWEN_RESIDENCY_PAGE);i<sizeof(v.bytes)&&valid;++i)if(v.bytes[i])valid=0;
        if(!o->mark(o->context,3,0))return 0;
        s->pending=1;int freed=o->unmap(o->context,p,n);s->pending=0;++s->unmaps;
        if(!freed)s->live=0;
        if(!o->mark(o->context,3,1)||freed)return 0;
        if(!valid){s->unsupported=(unsigned)(rc!=0);return 0;}
        for(unsigned i=0;i<n/QWEN_RESIDENCY_PAGE;++i) {
            unsigned flags=(unsigned char)v.bytes[i];++s->pages;
            s->resident+=(flags&1)!=0;s->modified+=(flags&(4|16))!=0;s->referenced+=(flags&(2|8))!=0;
        }
        offset+=n;
    }
    return s->maps==s->queries&&s->queries==s->unmaps&&!s->pending&&!s->live;
}
#endif

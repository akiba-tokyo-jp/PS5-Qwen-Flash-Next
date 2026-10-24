/* SPDX-License-Identifier: MIT
 * Bounded integrity input for a serial CPU-only launch controller.
 * The caller owns one aligned window and the descriptor. No allocation,
 * cache reclamation, title control or retry occurs here.
 */
#ifndef QWEN_LAUNCH_INTEGRITY_H
#define QWEN_LAUNCH_INTEGRITY_H
#include <stddef.h>
#include <stdint.h>
#define QWEN_LAUNCH_ALIGNMENT 16384u
#define QWEN_LAUNCH_WINDOW (1u<<20)
struct qwen_launch_integrity {
    void *context;
    uint64_t (*now_ns)(void *);
    int (*headroom)(void *);
    int (*marker)(void *,int);
    int64_t (*read_at)(void *,void *,size_t,uint64_t);
    int (*consume)(void *,const unsigned char *,size_t);
    uint64_t calls,returned,bytes;
    int failed,pending;
};
static int qwen_launch_integrity_read(struct qwen_launch_integrity *s,void *window,
        uint64_t offset,size_t requested,size_t expected,int consume,
        uint64_t begun,uint64_t limit) {
    const uint64_t before=s->now_ns(s->context);
    if(before<begun||before-begun>limit||!s->headroom(s->context)||!s->marker(s->context,1))return 0;
    s->pending=1;++s->calls;
    const int64_t got=s->read_at(s->context,window,requested,offset);
    s->pending=0;++s->returned;
    if(!s->marker(s->context,0))return 0;
    const uint64_t after=s->now_ns(s->context);
    if(after<before||after-begun>limit||got!=(int64_t)expected)return 0;
    if(consume) {
        if(!s->consume(s->context,window,expected))return 0;
        s->bytes+=expected;
    }
    return 1;
}
static int qwen_launch_integrity_stream(struct qwen_launch_integrity *s,void *window,
        uint64_t bytes,unsigned seconds) {
    if(!s||s->failed||s->pending||!window||(uintptr_t)window%QWEN_LAUNCH_ALIGNMENT||
       !bytes||bytes>(512ull<<20)||!seconds||seconds>60||!s->now_ns||!s->headroom||
       !s->marker||!s->read_at||!s->consume||s->calls||s->returned||s->bytes)return 0;
    const uint64_t begun=s->now_ns(s->context),limit=(uint64_t)seconds*1000000000ull;
    if(!begun){s->failed=1;return 0;}
    for(uint64_t offset=0;offset<bytes;) {
        size_t logical=bytes-offset>QWEN_LAUNCH_WINDOW?QWEN_LAUNCH_WINDOW:(size_t)(bytes-offset);
        const size_t requested=(logical+QWEN_LAUNCH_ALIGNMENT-1)&~(size_t)(QWEN_LAUNCH_ALIGNMENT-1);
        if(!qwen_launch_integrity_read(s,window,offset,requested,logical,1,begun,limit)){s->failed=1;return 0;}
        offset+=logical;
    }
    /* An explicit final block verifies EOF, including an unaligned tail.
     * Tail bytes are checked again but never hashed or counted twice.
     */
    const uint64_t eof_offset=bytes&~(uint64_t)(QWEN_LAUNCH_ALIGNMENT-1);
    const size_t tail=(size_t)(bytes-eof_offset);
    if(!qwen_launch_integrity_read(s,window,eof_offset,QWEN_LAUNCH_ALIGNMENT,tail,0,begun,limit)){
        s->failed=1;return 0;
    }
    return s->bytes==bytes&&s->calls==s->returned&&!s->pending;
}
#endif

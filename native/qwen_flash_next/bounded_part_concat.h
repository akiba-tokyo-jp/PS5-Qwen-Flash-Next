// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define QWEN_CONCAT_WINDOW 262144u
struct qwen_concat_ops {
    void*context;
    int64_t(*read)(void*,unsigned,uint64_t,void*,size_t);
    int(*write)(void*,uint64_t,const void*,size_t);
    int(*digest)(void*,const void*,size_t);
    int(*end_part)(void*,unsigned);
};
struct qwen_concat_stats {uint64_t logical_bytes,physical_written;unsigned reads,writes,closed_parts;};
// Part boundaries need not be Direct-I/O aligned. Only the final output
// write is padded; the owner truncates to logical_bytes after positive I/O.
static inline int qwen_concat_copy(const uint64_t*sizes,unsigned count,void*input,void*output,
                                  const struct qwen_concat_ops*ops,struct qwen_concat_stats*stats){
    if(!sizes||!count||count>128||!input||!output||((uintptr_t)input&16383)||((uintptr_t)output&16383)||
       (uintptr_t)input>UINTPTR_MAX-QWEN_CONCAT_WINDOW||(uintptr_t)output>UINTPTR_MAX-QWEN_CONCAT_WINDOW||
       ((uintptr_t)input<(uintptr_t)output+QWEN_CONCAT_WINDOW&&(uintptr_t)output<(uintptr_t)input+QWEN_CONCAT_WINDOW)||
       !ops||!stats||!ops->read||!ops->write||!ops->digest||!ops->end_part)return 0;
    uint64_t total=0;for(unsigned i=0;i<count;++i){if(!sizes[i]||sizes[i]>(512ULL<<20)-total)return 0;total+=sizes[i];}
    memset(stats,0,sizeof(*stats));size_t filled=0;
    for(unsigned part=0;part<count;++part){
        uint64_t offset=0;int valid=1;
        while(offset<sizes[part]){
            const size_t logical=sizes[part]-offset<QWEN_CONCAT_WINDOW?(size_t)(sizes[part]-offset):QWEN_CONCAT_WINDOW;
            const size_t requested=(logical+16383u)&~(size_t)16383u;
            const int64_t got=ops->read(ops->context,part,offset,input,requested);++stats->reads;
            if(got!=(int64_t)logical||!ops->digest(ops->context,input,logical)){valid=0;break;}
            size_t consumed=0;
            while(consumed<logical){
                const size_t take=logical-consumed<QWEN_CONCAT_WINDOW-filled?logical-consumed:QWEN_CONCAT_WINDOW-filled;
                memcpy((unsigned char*)output+filled,(unsigned char*)input+consumed,take);filled+=take;consumed+=take;
                if(filled==QWEN_CONCAT_WINDOW){
                    ++stats->writes;if(!ops->write(ops->context,stats->physical_written,output,QWEN_CONCAT_WINDOW)){valid=0;break;}
                    stats->physical_written+=QWEN_CONCAT_WINDOW;filled=0;
                }
            }
            if(!valid)break;
            offset+=logical;stats->logical_bytes+=logical;
        }
        const int closed=ops->end_part(ops->context,part);if(closed)++stats->closed_parts;
        if(!valid||!closed)return 0;
    }
    if(filled){
        const size_t padded=(filled+16383u)&~(size_t)16383u;memset((unsigned char*)output+filled,0,padded-filled);
        ++stats->writes;if(!ops->write(ops->context,stats->physical_written,output,padded))return 0;
        stats->physical_written+=padded;
    }
    return stats->logical_bytes==total&&stats->closed_parts==count&&stats->physical_written==(total+16383u)/16384u*16384u;
}

/* SPDX-License-Identifier: MIT */
#ifndef QWEN_FILE_RESIDENCY_REGION_H
#define QWEN_FILE_RESIDENCY_REGION_H
#include <stddef.h>
#include <stdint.h>
#define QWEN_REGION_PAGE UINT64_C(16384)
struct qwen_residency_region {uint64_t file_bytes,offset,bytes;unsigned maximum_windows;};
static int qwen_residency_region_valid(const struct qwen_residency_region*r) {
    if(!r||!r->file_bytes||r->file_bytes>(UINT64_C(512)<<30)||!r->bytes||r->bytes>(UINT64_C(128)<<20)||
       r->offset%QWEN_REGION_PAGE||r->offset>=r->file_bytes||r->bytes>r->file_bytes-r->offset||
       !r->maximum_windows||r->maximum_windows>128)return 0;
    const uint64_t extent=(r->bytes+QWEN_REGION_PAGE-1)/QWEN_REGION_PAGE*QWEN_REGION_PAGE;
    return(extent+1048575)/1048576<=r->maximum_windows;
}
static int qwen_residency_region_offset(const struct qwen_residency_region*r,uint64_t relative,size_t bytes,uint64_t*actual) {
    if(!actual||!qwen_residency_region_valid(r)||relative%QWEN_REGION_PAGE||!bytes||bytes>1048576||bytes%QWEN_REGION_PAGE)return 0;
    const uint64_t extent=(r->bytes+QWEN_REGION_PAGE-1)/QWEN_REGION_PAGE*QWEN_REGION_PAGE;
    if(relative>=extent||bytes>extent-relative)return 0;
    *actual=r->offset+relative;
    return *actual+bytes<=(r->file_bytes+QWEN_REGION_PAGE-1)/QWEN_REGION_PAGE*QWEN_REGION_PAGE;
}
#endif

/* SPDX-License-Identifier: MIT
 * Direct payload capacity and kernel VM metadata are separate domains.
 * Opt in only with the current-boot calibration bound in the build manifest.
 * 27 completed native allocate/map/touch/unmap/release cycles: maximum 17
 * VM pages; matched idle decrease at most 2 pages. This is a sampled policy,
 * not a universal physical minimum or a guarantee against global OS changes.
 */
#ifndef QWEN_DIRECT_VM_POLICY_H
#define QWEN_DIRECT_VM_POLICY_H
#include <stdint.h>
static unsigned qwen_direct_vm_pages(uint64_t bytes,unsigned alignment) {
#ifdef QWEN_DIRECT_VM_CALIBRATION_20261028
    static int emitted;
    if(!bytes||bytes>(28u<<20)||bytes%16384u||
       (alignment!=16384u&&alignment!=65536u)||bytes%alignment)return UINT32_MAX;
    if(!emitted) {
        if(!report("DIRECT_VM_ACCOUNTING profile=20261028 overhead_pages=17 idle_margin_pages=2 total_VM_additional_pages=19 Direct_payload_bytes=%llu alignment_bytes=%u",(unsigned long long)bytes,alignment))return UINT32_MAX;
        emitted=1;
    }
    return 19u;
#else
    (void)alignment;
    if(bytes%16384u||bytes/16384u>UINT32_MAX)return UINT32_MAX;
    return (unsigned)(bytes/16384u);
#endif
}
#endif

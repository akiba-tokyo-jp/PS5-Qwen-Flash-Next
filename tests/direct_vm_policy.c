/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdarg.h>
static unsigned reports;
static int report(const char *format,...) {(void)format;++reports;return 1;}
#include "direct_vm_policy.h"
int main(void) {
#ifdef QWEN_DIRECT_VM_CALIBRATION_20261028
    assert(qwen_direct_vm_pages(98304,16384)==19);
    assert(qwen_direct_vm_pages(8u<<20,16384)==19);
    assert(qwen_direct_vm_pages(20u<<20,65536)==19);
    assert(qwen_direct_vm_pages(28u<<20,16384)==19);
    assert(reports==1);
    assert(qwen_direct_vm_pages(0,16384)==UINT32_MAX);
    assert(qwen_direct_vm_pages((28u<<20)+16384,16384)==UINT32_MAX);
    assert(qwen_direct_vm_pages(98304,65536)==UINT32_MAX);
    assert(qwen_direct_vm_pages(65536,32768)==UINT32_MAX);
    assert(qwen_direct_vm_pages(1,16384)==UINT32_MAX);
#else
    assert(qwen_direct_vm_pages(98304,16384)==6);
    assert(qwen_direct_vm_pages(28u<<20,16384)==1792);
    assert(reports==0);
#endif
    return 0;
}

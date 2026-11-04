# SPDX-License-Identifier: MIT
"""Narrow cache-local synchronization refinements after completed ID readback."""
from build_speculative_batch_probe import once
from start_success_route import need


def transform(source, mode):
    need(mode in ('group', 'readback'), 'One explicit stream synchronization refinement required')
    begin = source.index('        if(qwen_app_Q2_quad_enabled()&&!six_refill){')
    end = source.index('\n        for (size_t ip = 0;', begin)
    block = source[begin:end]
    fence = '                ggml_backend_synchronize(backend);'
    need(block.count(fence) == 1 and block.count('ggml_backend_tensor_set(') == 1 and
         'ggml_backend_tensor_set_async' not in block and 'ggml_backend_graph_compute' not in block,
         'Only blocking stream uploads may intervene in the selected scope')
    prefix = source[:begin]
    need(prefix.rfind('ggml_backend_tensor_get_async(backend, sel, ids.data(), 0, ggml_nbytes(sel));') <
         prefix.rfind('ggml_backend_synchronize(backend);') and
         'ggml_backend_tensor_set_async' not in prefix[prefix.rfind('ggml_backend_synchronize(backend);'):],
         'The selected-ID readback and all preceding async work must complete before stream ownership')
    if mode == 'group':
        changed = once(block, fence, '                if(first==0)ggml_backend_synchronize(backend);')
    else:
        changed = once(block, fence, '                // The selected-ID readback completed; intervening uploads return synchronously.')
    return source[:begin] + changed + source[end:]

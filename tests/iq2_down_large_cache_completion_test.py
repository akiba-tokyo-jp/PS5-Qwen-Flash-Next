# SPDX-License-Identifier: MIT
"""Exercise changed all-graph admission without replaying legacy controls."""
import copy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from iq2_down_ggml_completion import ORDER
from iq2_down_large_cache_scope import validate_terminal

owner = dict(held=True, device=100, instance=101, epoch=45,
    driver_used_bytes=80, driver_reserved_bytes=100, global_capacity_measured=False,
    device_destroy_calls=0, driver_retire_calls=0, post_completion_GPU_operations=0,
    ordinary_process_close_required=True)
rows = [dict(layer=l, width=w, GGML_graphs=1, positive_fence=True,
    all_case_resources_retired=True, actual_Gate_Up_prefix_bytes=11827200,
    actual_Down_view_offset=460800, carrier_plane_bytes=460800,
    selected=2 if w <= 2 else 10, output_values=w*(2 if w <= 2 else 10)*2560,
    all_outputs_passed=True, mismatches=0, canaries_exact=True) for l, w in ORDER]
terminal = dict(completed=True, GGML_carrier_ABI=True, unknown_completion=False,
    native_PS5=True, model_loads=0, all_GPU_resources_positively_retired=False,
    all_case_resources_positively_retired=True, all_source_IO_completed=True,
    IO_journal_closed=True, GGML_backend_free_calls=0, retained_GGML_backend=102,
    all_outputs_passed=True, cases=rows, retained_completed_device=owner,
    F16_storage_FP32_accumulation=True, large_cache_index_safe=True,
    completed_GGML_case_prefix=0, reused_decode_cases=0)
validate_terminal(terminal)
negative = copy.deepcopy(terminal)
negative['all_outputs_passed'] = False
negative['cases'] = negative['cases'][:1]
negative['cases'][0].update(all_outputs_passed=False, mismatches=1)
validate_terminal(negative)
changes = [
    lambda t: t.update(large_cache_index_safe=False),
    lambda t: t.update(F16_storage_FP32_accumulation=False),
    lambda t: t.update(completed_GGML_case_prefix=2),
    lambda t: t.update(completed_GGML_case_prefix=False),
    lambda t: t.update(reused_decode_cases=6),
    lambda t: t.update(reused_decode_cases=False),
    lambda t: t.update(cases=[r for r in t['cases'] if r['width'] > 2]),
    lambda t: t['cases'].pop(),
    lambda t: t['cases'].reverse(),
    lambda t: t.update(unknown_completion=True),
    lambda t: t['cases'][0].update(positive_fence=False),
    lambda t: t.update(all_source_IO_completed=False),
    lambda t: t['retained_completed_device'].update(post_completion_GPU_operations=1),
]
for change in changes:
    bad = copy.deepcopy(terminal)
    change(bad)
    try:
        validate_terminal(bad)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Incomplete or old decode qualifications must refuse')
bad = copy.deepcopy(negative)
bad['cases'].append(copy.deepcopy(rows[1]))
try:
    validate_terminal(bad)
except RuntimeError:
    pass
else:
    raise AssertionError('No graph may follow a returned numerical negative')
print('{"completed":true,"positive_controls":2,"negative_controls":14,"PS5_operations":0}')

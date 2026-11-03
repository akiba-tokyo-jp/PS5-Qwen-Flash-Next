#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Separate returned numerical results from unknown GGML GPU completion."""
from start_success_route import need

ORDER=[(layer,width) for layer in (0,23,47) for width in (1,2,30,32)]


def validate_terminal(t):
    need(t['completed'] and t['GGML_carrier_ABI'] is True and not t['unknown_completion'] and
         t['native_PS5'] and t['model_loads']==0 and not t['all_GPU_resources_positively_retired'] and
         t['all_case_resources_positively_retired'] and t['all_source_IO_completed'] and t['IO_journal_closed'] and
         t['GGML_backend_free_calls']==0 and t['retained_GGML_backend']>0,
         'Every submitted graph, case owner and source call must return before ordinary close')
    rows=t['cases'];passed=t['all_outputs_passed'];prefix=t.get('completed_GGML_case_prefix',0)
    need(type(prefix) is int and prefix in (0,2),'Only the separately bound two-case prefix may be reused')
    F16=t.get('F16_storage_FP32_accumulation') is True
    if F16:
        need(prefix==0 and t.get('reused_decode_cases')==6,'Only the six separately bound unchanged decode cases may be reused')
    order=[r for r in ORDER if r[1]>2] if F16 else ORDER[prefix:]
    need(1<=len(rows)<=len(order) and [(r['layer'],r['width']) for r in rows]==order[:len(rows)] and
         all(r['GGML_graphs']==1 and r['positive_fence'] and r['all_case_resources_retired'] and
             r['actual_Gate_Up_prefix_bytes']>0 and r['actual_Down_view_offset']==460800 and
             r['carrier_plane_bytes']==460800 and r['selected']==(2 if r['width']<=2 else 10) and
             r['output_values']==r['width']*r['selected']*2560 and
             r['all_outputs_passed']==(r['mismatches']==0 and r['canaries_exact']) for r in rows),
         'Exactly the submitted distinct GGML prefix and positive completion are required')
    need((passed and len(rows)==len(order) and all(r['all_outputs_passed'] for r in rows)) or
         (not passed and all(r['all_outputs_passed'] for r in rows[:-1]) and not rows[-1]['all_outputs_passed']),
         'A returned numerical negative ends graph submission immediately')
    owner=t['retained_completed_device']
    need(owner['held'] and owner['device']>0 and owner['instance']>0 and owner['epoch']>0 and
         owner['driver_used_bytes']<=owner['driver_reserved_bytes'] and not owner['global_capacity_measured'] and
         owner['device_destroy_calls']==owner['driver_retire_calls']==owner['post_completion_GPU_operations']==0 and
         owner['ordinary_process_close_required'],'The real GGML device, instance and backend remain alive until ordinary exit')
    return owner

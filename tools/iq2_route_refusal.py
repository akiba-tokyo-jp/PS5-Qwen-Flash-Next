#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit only the returned IQ2 route-byte guard after one completed request."""
from start_success_route import need

ENTRY_SHA = '360b7cda8d2260d9ba090a654040d8a4e407f6c58fc8a97f53827f79a9b64dfb'
SELF_SHA = '105cde6a357e13086826b95459150b201d2c2c5131394071cec18ace9d625a3c'


def audit(stages, failure):
    active, epochs = False, 0
    for line in stages.splitlines():
        if line == b'native_driver_single_producer_entered':
            need(not active, 'No overlapping producer is admitted')
            active = True
        elif line == b'native_driver_producer_completed_resources_owned':
            need(active, 'Every completed producer must have entered')
            active, epochs = False, epochs + 1
    need(not active and epochs == 30, 'All thirty producers must complete positively')
    need(stages.splitlines()[-3:] == [b'inference_request_reset_completed',
        b'first_generation_request_reset_completed', b'resident_additional_exception_work_stopped'],
        'The returned CPU guard must immediately follow the completed request reset')
    need(stages.count(b'first_generation_intent_persisted') == 1 and
         stages.count(b'first_generation_token_persisted') == 22 and
         stages.count(b'first_generation_request_reset_completed') == 1 and
         stages.count(b'inference_end_of_generation_observed') == 1 and b'fatal_operation=' not in stages,
         'Only the exact first returned generation is admitted')
    need(failure['message'] == 'Complete actual additional routes required' and
         failure['native_resources_started'] is True and failure['model_loaded'] is True and
         failure['CPU_worker_completion_unknown'] is False,
         'The exact returned CPU route guard and known worker completion are required')
    upload = failure['resident_GPU_upload']
    need(upload['completed_copy_calls'] == 1307 and upload['completed_copy_bytes'] == 3549514400 and
         upload['original_fence_wait_reset_and_cleanup'], 'All original synchronous uploads must return')
    need(failure['context_reuse_VM']['GPU_calls_added'] == 0 and
         failure['context_reuse_VM']['same_original_context'] and
         [r['phase'] for r in failure['context_reuse_VM']['samples']] ==
         ['before_engine_release', 'after_engine_release', 'before_cache_metadata_reset', 'after_cache_metadata_reset'],
         'The actual request reset must retain the known original owner without additional GPU calls')


def close_proof_valid(proof):
    return (proof.get('known_IQ2_post_request_route_accounting_refusal') is True and
        proof.get('model_loaded') is True and proof.get('completed_requests') == 1 and
        proof.get('completed_GPU_epochs') == 30 and proof.get('completed_token_records') == 22 and
        proof.get('post_reset_GPU_submissions') == 0 and proof.get('all_source_IO_completed') is True and
        proof.get('CPU_worker_completion_unknown') is False and
        proof.get('source_audit_SHA256') == ENTRY_SHA and proof.get('SELF_SHA256') == SELF_SHA)

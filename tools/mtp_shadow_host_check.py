#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the actual FirstGeneration integration test to candidate MTP sources."""
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load,need


def verify(receipt,provider_inputs):
    need(record(receipt['path'])==receipt,'The actual FirstGeneration host receipt changed')
    check=load(receipt['path'])
    need(check['completed'] and check.get('actual_FirstGeneration_context_capacity_prompt_position_and_retirement_controls_passed') is True and
         check['causal_single_reject_accept_catchup_bonus_EOG_controls_passed'] and check['target_compiled'],
         'Actual FirstGeneration context-capacity, prompt-position and retirement controls must pass')
    tested={Path(row['path']).name:row for row in check['inputs']}
    need(len(tested)==len(check['inputs']) and all(record(row['path'])==row for row in check['inputs']),
         'All tested host integration inputs must remain exact')
    expected={'persistent_mtp_cursor.h','persistent_mtp_shadow.h','persistent_mtp_shadow.cpp','session.h','first_generation.h'}
    need({Path(row['path']).name for row in provider_inputs}==expected and len(provider_inputs)==len(expected),
         'All actual candidate MTP and caller sources must be bound')
    for row in provider_inputs:
        reference=tested[Path(row['path']).name]
        need(record(row['path'])==row and all(row[key]==reference[key] for key in ('bytes','sha256')),
             'The candidate MTP/caller source differs from the tested implementation')


def require_profile(profile):
    need(profile.get('actual_FirstGeneration_host_controls_passed') is True,
         'The actual FirstGeneration host integration gate is required')
    verify(profile['actual_FirstGeneration_host_check'],profile['actual_FirstGeneration_provider_inputs'])


def require_target_capture_profile(profile):
    need(profile.get('successful_MTP_contract_verified') is True and profile.get('actual_legacy_policy_validator_passed') is True and
         profile.get('actual_FirstGeneration_target_capture_host_controls_passed') is True,
         'Successful MTP support and actual target-capture caller controls are required')
    receipt=profile['target_capture_host_check'];need(record(receipt['path'])==receipt,'Target capture host receipt changed')
    check=load(receipt['path'])
    need(check['completed'] and check['actual_FirstGeneration_accept_reject_bonus_and_hidden_retention_controls_passed'] and
         all(record(row['path'])==row for row in check['inputs']),
         'All actual target-capture host inputs must remain exact')


def require_online_profile(profile):
    need(profile.get('successful_MTP_contract_verified') is True and profile.get('actual_legacy_policy_validator_passed') is True and
         profile.get('actual_FirstGeneration_online_MTP_host_controls_passed') is True,
         'Successful support providers and actual online MTP caller controls are required')
    receipt=profile['online_MTP_host_check'];need(record(receipt['path'])==receipt,'Online MTP host receipt changed')
    check=load(receipt['path'])
    need(check['completed'] and check['actual_FirstGeneration_accept_reject_catchup_bonus_EOG_and_attempt_bound_controls_passed'] and
         all(record(row['path'])==row for row in check['inputs']),'All tested online MTP inputs must remain exact')
    capture=profile['native_target_capture_proof'];need(record(capture['path'])==capture,'Native target capture proof changed')
    native=load(capture['path'])
    need(native['completed'] and native['accepted']==native['rejected']==1 and native['queued_bonus_without_new_process'] and
         native['compact_rejection_first_hidden_retained'] and native['full_target_tokens_and_output_bytes_exact'] and
         native['native_owners']==0,'Actual target acceptance, rejection and hidden retention must precede online MTP')

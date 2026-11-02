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

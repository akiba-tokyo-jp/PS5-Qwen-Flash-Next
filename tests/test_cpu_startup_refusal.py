#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep unknown work outside source-bound CPU-only ordinary closure."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from close_successful_early_self_refusal import returned_CPU_reader_observation
from close_successful_current_model import completed_terminal_journal


class ReturnedReader(unittest.TestCase):
    def journal(self,reads=0,free=1800):
        return (b'CXX_initializers_completed\n'
                b'early_SELF_CPU_read_scope_at_main_entry_after_CXX GPU_calls=0\n'+
                (b'early_SELF_Direct_read_before_native_call GPU_calls=0\n'
                 b'early_SELF_Direct_read_returned GPU_calls=0\n')*reads+
                f'main_SELF_CPU_observation free_before={free} free_last={free} minimum_sampled={free} selected_CPU_floor=919 completed_reads={reads}\n'.encode()+
                b'fatal_operation=main_SELF_Direct_integrity_returned_refusal\n')

    def test_explicit_original_CPU_scope(self):
        for reads in (0,1,12):
            self.assertEqual(returned_CPU_reader_observation(self.journal(reads),original_CPU_only_allowed=True)[-1],reads)

    def test_no_implicit_zero_read_permission(self):
        with self.assertRaises((ValueError,RuntimeError)):
            returned_CPU_reader_observation(self.journal())

    def test_unsafe_or_changed_scope(self):
        base=self.journal(1)
        mutations=[
            base.replace(b'early_SELF_Direct_read_returned GPU_calls=0\n',b''),
            base.replace(b'completed_reads=1',b'completed_reads=2'),
            base.replace(b'selected_CPU_floor=919',b'selected_CPU_floor=918'),
            base.replace(b'CXX_initializers_completed\n',b''),
            base.replace(b'minimum_sampled=1800',b'minimum_sampled=0'),
            base.replace(b'minimum_sampled=1800',b'minimum_sampled=1801'),
            base+b'unfinished\n',
        ]
        for forbidden in (b'native_GPU_initialize',b'model_mapping_',b'configuration_read',b'early_SELF_Direct_EOF_',
                          b'main_entered GPU_not_started=1 model_loaded=0',b'inference_before_'):
            mutations.append(base.replace(b'main_SELF_CPU_observation',forbidden+b'\nmain_SELF_CPU_observation'))
        for raw in mutations:
            with self.subTest(raw=raw):
                with self.assertRaises((ValueError,RuntimeError)):
                    returned_CPU_reader_observation(raw,original_CPU_only_allowed=True)

    def test_original_scope_does_not_admit_settle_refusal(self):
        raw=self.journal().replace(b'main_SELF_CPU_observation',b'CPU_startup_passive_settle done=0 polls=0\nmain_SELF_CPU_observation')
        with self.assertRaises((ValueError,RuntimeError)):
            returned_CPU_reader_observation(raw,original_CPU_only_allowed=True)
        self.assertEqual(returned_CPU_reader_observation(raw,settle_only_allowed=True)[-1],0)

    def test_positive_CPU_completion_marker(self):
        raw=(b'early_SELF_whole_Direct_hash_completed_at_main_entry_after_CXX\n'
             b'CPU_startup_memory_completed_waiting_for_ordinary_close\n')
        self.assertTrue(completed_terminal_journal(raw,True))
        self.assertFalse(completed_terminal_journal(raw,False))
        self.assertTrue(completed_terminal_journal(b'resident_additional_completed_waiting_for_ordinary_close\n'))
        self.assertFalse(completed_terminal_journal(b'CXX_initializers_completed\n',True))

    def test_CPU_completion_requires_parked_whole_reader(self):
        raw=(b'early_SELF_whole_Direct_hash_completed_at_main_entry_after_CXX\n'
             b'CPU_startup_memory_completed_waiting_for_ordinary_close\n')
        mutations=[raw+b'pending\n',raw+raw,raw.replace(b'early_SELF_whole_Direct_hash_completed_at_main_entry_after_CXX\n',b'')]
        for forbidden in (b'model_mapping_',b'native_GPU_initialize',b'inference_before_'):
            mutations.append(forbidden+b'\n'+raw)
        for stages in mutations:
            with self.assertRaises((ValueError,RuntimeError)):completed_terminal_journal(stages,True)


if __name__=='__main__':unittest.main()

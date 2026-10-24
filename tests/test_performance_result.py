# SPDX-License-Identifier: MIT
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from performance_result import FIELDS, validate_performance, validate_backpressure, validate_first_performance


class PerformanceResultTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(schema='ps5-qwen-completed-performance-v1',
            process_includes_source_and_backend_work=True, GPU_timestamp_queries=False,
            hot_path_logs_added=False, GPU_operations_added=False,
            delta=dict.fromkeys(FIELDS, 1))
        self.record['delta'].update(process_ns=1000, synchronize_ns=0, process_calls=52)
        self.result = dict(stop_reason='end_of_generation', metrics=dict(prompt_tokens=30, generated_tokens=22))

    def test_nested_intervals_are_not_GPU_compute_time(self):
        result = validate_performance(self.record, self.result)
        self.assertEqual(result['measured_source_wall_fraction'], .004)
        self.assertFalse(result['GPU_compute_time_qualified'])

    def test_failed_missing_uncompleted_and_inconsistent_measurements(self):
        mutations = [lambda r: r['delta'].pop('source_read_ns'),
            lambda r: r['delta'].update(source_completed_windows=0),
            lambda r: r['delta'].update(source_read_ns=1001),
            lambda r: r['delta'].update(process_calls=51),
            lambda r: r['delta'].update(source_consumer_ns=-1),
            lambda r: r.update(GPU_timestamp_queries=True)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(self.record); mutation(record)
                with self.assertRaises(ValueError): validate_performance(record, self.result)
        self.result['stop_reason'] = 'failed'
        with self.assertRaises(ValueError): validate_performance(self.record, self.result)

    def test_output_limit_has_no_extra_EOG_decode(self):
        self.result['stop_reason'] = 'output_token_limit'
        self.record['delta']['process_calls'] = 51
        validate_performance(self.record, self.result)

    def test_parallel_v2_measures_wall_interval_and_requires_used_pairs(self):
        self.record.update(schema='ps5-qwen-completed-performance-v2',
            source_read_ns_is_batch_wall_time=True, maximum_parallel_source_reads=2)
        self.record['delta'].update(source_chunks=2, source_completed_windows=2, source_parallel_batches=1)
        validate_performance(self.record, self.result)
        for value in (0, 2):
            self.record['delta']['source_parallel_batches'] = value
            with self.assertRaises(ValueError): validate_performance(self.record, self.result)

    def test_pipeline_worker_intervals_overlap_and_only_one_read_is_admitted(self):
        self.record.update(schema='ps5-qwen-completed-performance-v3',
            source_read_ns_is_producer_wait_time=True, maximum_parallel_source_reads=1,
            worker_times_overlap_consumers=True)
        self.record['delta'].update(source_chunks=2, source_completed_windows=2,
            source_pipeline_batches=1, source_worker_read_ns=999, source_worker_dispatch_ns=999)
        self.assertEqual(validate_performance(self.record,self.result)['measured_source_wall_fraction'],.004)
        for key,value in [('maximum_parallel_source_reads',2),('worker_times_overlap_consumers',False)]:
            record=copy.deepcopy(self.record);record[key]=value
            with self.assertRaises(ValueError):validate_performance(record,self.result)

    def test_bounded_memory_recovery_preserves_the_original_reserve(self):
        record=dict(schema='ps5-qwen-memory-backpressure-v1',enabled=True,
            maximum_boundary_wait_ms=2000,maximum_total_wait_ms=10000,poll_interval_ms=100,
            memory_reserves_unchanged=True,IO_or_GPU_operations_retried=False,last_qualified=True,
            kernel_page_size=16384,kernel_extra_margin_bytes=4<<20,
            observations=5,pressure_events=1,recovered_admissions=1,cumulative_wait_ns=100000000,
            pause_calls=1,kernel_free_pages=1156,kernel_minimum_pages=900,kernel_reserved_pages=206)
        validate_backpressure(record)
        for key,value in [('kernel_free_pages',1155),('cumulative_wait_ns',10000000001),
            ('recovered_admissions',0),('IO_or_GPU_operations_retried',True),('last_qualified',False),
            ('maximum_boundary_wait_ms',3000),('kernel_reserved_pages',0)]:
            bad=dict(record);bad[key]=value
            with self.assertRaises(ValueError):validate_backpressure(bad)

    def test_batched_prefill_counts_partial_prompt_batch_and_single_token_decode(self):
        self.record.update(schema='ps5-qwen-completed-performance-v5',
            source_read_ns_is_producer_wait_time=True,maximum_parallel_source_reads=2,
            file_range_schedule_enabled=True,physical_read_bytes_include_alignment=True,
            worker_times_overlap_consumers=True,prefill_batch_tokens=4,
            generated_token_batch_tokens=1,all_prompt_outputs_requested=True)
        self.record['delta'].update(source_bytes=100,source_chunks=6,source_completed_windows=6,
            source_parallel_batches=1,source_coalesced_batches=1,source_selected_serial_batches=1,
            source_pipeline_batches=1,source_physical_read_bytes=128,source_physical_read_calls=5,
            source_worker_read_ns=999,source_worker_dispatch_ns=999,process_calls=30)
        self.result['prefill_batch_tokens']=4
        validate_performance(self.record,self.result)
        self.result.update(token_ids=list(range(22)),output_bytes=[49]*22)
        aggregate=copy.deepcopy(self.result);aggregate.pop('prefill_batch_tokens')
        validate_first_performance(self.record,aggregate,self.result)
        for field in ('metrics','token_ids','output_bytes','stop_reason'):
            bad=copy.deepcopy(self.result);bad.pop(field)
            with self.assertRaises(ValueError):validate_first_performance(self.record,aggregate,bad)
        bad=copy.deepcopy(aggregate);bad['prefill_batch_tokens']=2
        with self.assertRaises(ValueError):validate_first_performance(self.record,bad,self.result)
        for key,value in [('prefill_batch_tokens',8),('generated_token_batch_tokens',2),
                          ('all_prompt_outputs_requested',False)]:
            bad=copy.deepcopy(self.record);bad[key]=value
            with self.assertRaises(ValueError):validate_performance(bad,self.result)
        for count in (29,31,52):
            bad=copy.deepcopy(self.record);bad['delta']['process_calls']=count
            with self.assertRaises(ValueError):validate_performance(bad,self.result)
        bad=copy.deepcopy(self.result);bad.pop('prefill_batch_tokens')
        with self.assertRaises(ValueError):validate_performance(self.record,bad)
        self.result['stop_reason']='output_token_limit'
        self.record['delta']['process_calls']=29
        validate_performance(self.record,self.result)

    def test_selected_schedule_v4_requires_physical_read_and_completion_accounting(self):
        self.record.update(schema='ps5-qwen-completed-performance-v4',
            source_read_ns_is_producer_wait_time=True,maximum_parallel_source_reads=2,
            file_range_schedule_enabled=True,physical_read_bytes_include_alignment=True,
            worker_times_overlap_consumers=True)
        self.record['delta'].update(source_bytes=100,source_chunks=6,source_completed_windows=6,
            source_pipeline_batches=1,source_worker_read_ns=20,source_worker_dispatch_ns=1,
            source_parallel_batches=1,source_coalesced_batches=1,source_selected_serial_batches=1,
            source_physical_read_bytes=120,source_physical_read_calls=5)
        validate_performance(self.record,self.result)
        for field,value in [('source_physical_read_bytes',99),('source_physical_read_calls',6),
                            ('source_selected_serial_batches',0),('source_parallel_batches',2)]:
            bad=copy.deepcopy(self.record);bad['delta'][field]=value
            with self.assertRaises(ValueError):validate_performance(bad,self.result)

    def test_v2_wait_allowance_is_finite_and_does_not_change_memory_reserves(self):
        record=dict(schema='ps5-qwen-memory-backpressure-v2',enabled=True,
            maximum_boundary_wait_ms=20000,maximum_total_wait_ms=60000,poll_interval_ms=100,
            memory_reserves_unchanged=True,IO_or_GPU_operations_retried=False,last_qualified=True,
            kernel_page_size=16384,kernel_extra_margin_bytes=4<<20,
            observations=40,pressure_events=3,recovered_admissions=3,cumulative_wait_ns=3300000000,
            pause_calls=33,kernel_free_pages=1156,kernel_minimum_pages=900,kernel_reserved_pages=206)
        validate_backpressure(record)
        for key,value in [('cumulative_wait_ns',60000000001),('maximum_total_wait_ms',60001),
            ('memory_reserves_unchanged',False),('pause_calls',601)]:
            bad=dict(record);bad[key]=value
            with self.assertRaises(ValueError):validate_backpressure(bad)


if __name__ == '__main__': unittest.main()

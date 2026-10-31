#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record approximate-answer quality while preserving stream and resource proof."""
import observe_four_next_normal as base
from build_speculative_batch_probe import once
from expert_q4 import require
original=base.base.selected.observer_source

def observer_source():
 source=original()
 return once(source,"row['counting_quality_passed'] and row['request_reset_completed']",
             "type(row['counting_quality_passed']) is bool and row['request_reset_completed']")

base.base.selected.observer_source=observer_source

def bounded_actual_io(rows):
 require(bool(rows)and all(x['flags']==5 and 0<=x['maximum_lifetime_quad_inflight']<=4 and all(x[k]>=0 for k in('adjacent_calls_saved','extra_bundled_Experts','quad_batches'))for x in rows),'Original bounded I/O and unaltered event counters required')

# An effective cache can eliminate the demand that would exercise an I/O feature.
base.base.selected.validate_retained_io_cohort=bounded_actual_io
if __name__=='__main__':base.base.main()

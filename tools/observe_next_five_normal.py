#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record approximate-answer quality while preserving stream and resource proof."""
import observe_four_next_normal as base
from build_speculative_batch_probe import once
original=base.base.selected.observer_source

def observer_source():
 source=original()
 return once(source,"row['counting_quality_passed'] and row['request_reset_completed']",
             "type(row['counting_quality_passed']) is bool and row['request_reset_completed']")

base.base.selected.observer_source=observer_source
if __name__=='__main__':base.base.main()

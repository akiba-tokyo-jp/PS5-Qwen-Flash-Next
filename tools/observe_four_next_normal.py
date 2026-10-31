#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve the normal API/frame protocol while validating copy-free attempts."""
import observe_weight_followup_normal as base
from build_speculative_batch_probe import once
original=base.selected.observer_source
def observer_source():
 source=original()
 return once(source,"c['captures']==s['attempts'] and c['restores']==s['rejected']",
             "c['captures']==0 and c['restores']==0")
base.selected.observer_source=observer_source
if __name__=='__main__':base.main()

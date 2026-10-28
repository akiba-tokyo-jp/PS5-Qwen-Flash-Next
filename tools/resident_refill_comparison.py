#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Matched actual-model six-demand delivery, one model and the same worker."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def generate(kind,source,unused_tail,flags):
    if kind!='refill':raise ValueError('Explicit six-demand cohort required')
    from resident_additional_comparisons import generate as additional
    text,inputs=additional('cache',source,unused_tail,flags)
    changes=[('#include "resident_additional_policy.h"','#include "resident_refill_policy.h"\n#include "six_bank_refill.h"'),
        ('qwen_app::require_resident_additional_policy(policy,"cache");','qwen_app::require_resident_refill_policy(policy);'),
        ('const unsigned request_count=prefix_comparison?9:3;','const unsigned request_count=5;'),
        ('const char *arm=ordinal==0?"warmup":(reuse?"prefix":"ordinary");',
         'const bool refill=ordinal==2||ordinal==3;\n            const char *arm=ordinal==0?"warmup":(refill?"six-demand":"ordinary");'),
        ('            std::size_t rows=0;double max_error=0;',
         '            qwen_app::configure_native_six_bank_refill(refill);\n            qwen_six_bank_refill_stats refill_before{};qwen_app_six_bank_refill_counters(&refill_before);\n            std::size_t rows=0;double max_error=0;'),
        ('            Json row={{"ordinal",ordinal}',
         '            qwen_six_bank_refill_stats refill_after{};qwen_app_six_bank_refill_counters(&refill_after);\n'
         '            if(refill_after.batches<refill_before.batches||refill_after.reads<refill_before.reads||refill_after.logical_bytes<refill_before.logical_bytes)\n'
         '                throw std::runtime_error("Six-demand counters decreased");\n'
         '            const auto batches=refill_after.batches-refill_before.batches,reads=refill_after.reads-refill_before.reads,logical=refill_after.logical_bytes-refill_before.logical_bytes;\n'
         '            if(reads!=6*batches||logical!=reads*qwen_app::bank_expert_bytes||(refill?!batches:batches))\n'
         '                throw std::runtime_error("Actual six-demand delivery and source accounting differ");\n'
         '            Json row={{"six_demand",{{"enabled",refill},{"batches",batches},{"reads",reads},{"logical_bytes",logical}}},{"ordinal",ordinal}'),
        ('{"kind",prefix_comparison?"prefix":"cache"}','{"kind","refill"}')]
    for old,new in changes:
        if text.count(old)!=1:raise ValueError('Unique original refill frontier required: '+old[:80])
        text=text.replace(old,new)
    return text,inputs+[Path(__file__),ROOT/'native/app/resident_refill_policy.h',ROOT/'native/app/six_bank_refill.h']

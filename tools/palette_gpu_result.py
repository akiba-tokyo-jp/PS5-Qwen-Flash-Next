#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate a finite GPU palette result; a delivery win never admits production."""
from statistics import median

def parse(result,policy,owner_pid):
    def require(value,message):
        if not value:raise ValueError(message)
    def integer(value):return type(value)is int and value>0
    p=policy['native_palette_validation']
    require(result.get('schema')=='ps5-qwen-exact-palette-GPU-result-v1','Unknown GPU result schema')
    require(integer(owner_pid)and type(result.get('pid'))is int and result['pid']==owner_pid,'GPU owner differs')
    for key in ('passed','all65536_BF16_patterns_exact','positive_device_idle_and_epoch_retirement',
                'all_fences_positively_completed','source_file_closed','palette_delivery_includes_validation_dispatch_fence'):
        require(result.get(key)is True,'Positive GPU/source completion is required: '+key)
    for key in ('model_loaded','full_model_inference','quantization','raw_delivery_includes_copy_check'):
        require(result.get(key)is False,'The finite original-bit scope differs: '+key)
    for key,expected in (('GPU_dispatches',110),('original_matrix_deliveries',108),('automatic_retries',0),('live_GPU_buffer_bytes',8<<20)):
        require(type(result.get(key))is int and result[key]==expected,'Fixed cohort differs: '+key)
    require(p['rounds']==6 and len(p['samples'])==9,'Fixed source geometry differs')
    rows=result.get('rounds');require(type(rows)is list and len(rows)==108,'Incomplete delivery cohort')
    totals=[[0,0]for _ in range(6)];reads=[[0,0]for _ in range(6)]
    order=[(r,s,(r+o)%2)for r in range(6)for s in range(9)for o in range(2)]
    for row,(r,s,mode)in zip(rows,order):
        require(all(type(row.get(k))is int and row[k]==v for k,v in (('round',r),('sample',s),('mode',mode))),'Rotated pair order differs')
        require(row.get('original_SHA256_exact')is True,'Original matrix digest is incomplete')
        read=row.get('read_ns');dispatch=row.get('dispatch_completion_ns');delivery=row.get('delivery_ns')
        require(all(integer(v)for v in (read,dispatch,delivery)),'Timing must be positive integer nanoseconds')
        require(delivery>=read+dispatch if mode else delivery==read,'Complete delivery timing scope differs')
        expected=p['samples'][s]['encoded'if mode else'raw']['requested']
        require(type(row.get('physical_bytes'))is int and row['physical_bytes']==expected,'Physical source envelope differs')
        totals[r][mode]+=delivery;reads[r][mode]+=read
    ratios=[raw/palette for raw,palette in totals]
    return dict(completed=True,all_original_bits_and_positive_retirement=True,
        rounds=6,original_matrix_deliveries=108,GPU_dispatches=110,
        paired_round_delivery_ratios=ratios,paired_round_median_ratio=median(ratios),
        raw_median_round_delivery_ns=median(x[0]for x in totals),
        palette_median_round_delivery_ns=median(x[1]for x in totals),
        initial_delivery_screen_passed=median(ratios)>1.05 and all(x>1 for x in ratios),
        raw_copy_check_excluded_from_baseline=True,palette_includes_validation_dispatch_fence=True,
        full_model_admitted=False,production_adoption=False)

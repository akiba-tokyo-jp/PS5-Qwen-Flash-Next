# SPDX-License-Identifier: MIT
"""Refuse incomplete, contradictory or non-reproducible speed promotion."""
import copy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_matched_cache_monitor import require_winner
from review_resident_results import paired

complete=dict(kind='cache',cases=[4780,4880,4900,4920],native_requests=12,cross_cache_F32_rows=92,
    all_expert_selections_exact=True,only_completed_native_evidence_used=True,
    decode=paired([0.391,0.392],[0.408,0.409],True),total=paired([106,106.3],[102,102.3],False))
require_winner(complete)
controls=[]
for key,value in (('kind','refill'),('cases',[4780,4880]),('native_requests',9),('cross_cache_F32_rows',69),
                  ('all_expert_selections_exact',False),('only_completed_native_evidence_used',False)):
    row=copy.deepcopy(complete);row[key]=value;controls.append(row)
for metric,candidate in (('decode',[0.408,0.390]),('total',[102,107]),('decode',[float('nan'),0.409]),('total',[0,102])):
    row=copy.deepcopy(complete);row[metric]['candidate']=candidate;controls.append(row)
for metric in ('decode','total'):
    row=copy.deepcopy(complete);row[metric]['reproducible_in_this_finite_cohort']=False;controls.append(row)
for row in controls:
    try:require_winner(row)
    except ValueError:pass
    else:raise AssertionError('Unqualified cache promotion accepted')
print(f'Cache promotion: one positive and {len(controls)} refusal controls passed; no console calls')

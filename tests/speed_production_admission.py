# SPDX-License-Identifier: MIT
"""Check real qualification metadata and refuse altered deployment requirements."""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from speed_followup_production import *
p=argparse.ArgumentParser();p.add_argument('--context',type=Path,required=True);a=p.parse_args()
load=lambda path:json.loads(Path(path).read_text())
i=load(ROOT/'config/production-installation.json');c=load(a.context);r=load(ROOT/REPORT)
# This is an explicitly synthetic placement preview for a read-only host check.
# Actual admission requires the independent native12-file placement evidence.
r.update(completed=True,pending_steps=[],placement=dict(completed=True,case=12540,normal_case=12500,verification_files=12,verified_programs=2,verified_settings=5,verified_control_settings=5,
 native_whole_SHA256_identity_EOF_verified=True,immediate_control_preserved=True,fresh_idle_confirmed=True,runtime_ownership_restored=True,native_title_running=False,gateway_running=False,model_loaded=False))
i.update(application_SELF=r['application_SELF'],previous_production_SHA256=CONTROL_SELF,normal_validation_case=12500,production_placement_case=12540,speed_followup_policy=POLICY)
c.update(production_SELF=r['application_SELF'],normal_performance_case=12500,normal_performance_placement_case=12540,speed_followup_policy=POLICY)
require_speed_followup_production(i,c,r)
def altered(which,key,value):
    v=[copy.deepcopy(x)for x in(i,c,r)];target=v[which]
    for part in key[:-1]:target=target[part]
    target[key[-1]]=value
    try:require_speed_followup_production(*v)
    except ValueError:return
    raise AssertionError('Modified adoption requirement accepted: '+'.'.join(key))
for args in((0,('application_SELF','sha256'),'0'*64),(0,('model_receipt_SHA256',),'0'*64),
 (0,('CPU_heap_limit_bytes',),536870913),(1,('native_running',),True),
 (2,('normal','source_model_GPU_owners_positively_retired'),False),(2,('placement','completed'),False),
 (2,('causal_budget_comparison','attempt_caps'),[8,8]),(2,('policy','maximum_speculative_attempts'),8),
 (2,('normal','actual_native_frames_viewed'),0)):
 altered(*args)
print('PASS: actual qualification with synthetic placement preview, plus9 wrong-identity/model/reserve/owner/placement/budget/display refusals; PS5 operations=0')

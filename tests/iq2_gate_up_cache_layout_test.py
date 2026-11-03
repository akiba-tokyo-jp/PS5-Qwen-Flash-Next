#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise combined Gate/Up launch boundaries against the completed native proofs."""
import argparse
import copy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_performance_quantizer import record
from iq2_up_model_scope import require_cache_layout


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arithmetic-qualification',type=Path,required=True)
    p.add_argument('--Gate-input-proof',type=Path,required=True)
    a=p.parse_args()
    scope=dict(arm='candidate',selected_cache_slots=3712,IQ2_Up_layers=list(range(48)),
        IQ2_Gate_layers=list(range(48)),IQ2_only_FP32_accumulation=True,normal_F16_enabled=True,
        backend_environment=dict(GGML_VK_DISABLE_MMVQ='1'),arithmetic_qualification=record(a.arithmetic_qualification),
        Gate_input_identity=record(a.Gate_input_proof))
    candidate=dict(headless_audit_kind='Q2-IQ2-Gate-Up-model',overrides=dict(native_headless_model_audit=scope))
    require_cache_layout(candidate)
    control=copy.deepcopy(candidate);s=control['overrides']['native_headless_model_audit']
    s.update(arm='control',IQ2_Up_layers=[],IQ2_Gate_layers=[],backend_environment={});require_cache_layout(control)
    cases=[]
    changes=[dict(IQ2_Gate_layers=[0]),dict(IQ2_Up_layers=list(range(47))),
        dict(IQ2_Gate_layers=list(reversed(range(48)))),dict(Gate_input_identity=None),
        dict(selected_cache_slots=4000),dict(normal_F16_enabled=False)]
    for change in changes:
        wrong=copy.deepcopy(candidate);wrong['overrides']['native_headless_model_audit'].update(change);cases.append(wrong)
    wrong=copy.deepcopy(candidate);wrong['headless_audit_kind']='Q2-IQ2-Up-model';cases.append(wrong)
    wrong=copy.deepcopy(control);wrong['overrides']['native_headless_model_audit']['IQ2_Gate_layers']=[0];cases.append(wrong)
    for wrong in cases:
        try:require_cache_layout(wrong)
        except RuntimeError:continue
        raise AssertionError('An unqualified or nonuniform combined layout reached model admission')
    print(dict(completed=True,positive_controls=2,negative_controls=len(cases),PS5_operations=0))


if __name__=='__main__':main()

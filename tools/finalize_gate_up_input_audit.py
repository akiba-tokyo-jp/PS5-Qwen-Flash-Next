#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Seal a completed metadata-only Gate/Up audit without another console operation."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','case','closure','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();built=load(a.build);closed=load(a.closure);plan=load(a.case/'plan.private.json')
    folder=a.case/'headless-observer';terminal=load(folder/'native.private.bin');audit=load(folder/'native.audit.private.json')
    need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         closed['native_owners']==0 and not closed['unknown_completion'],'Positive ordinary restoration required')
    need(terminal['completed'] and terminal['kind']=='Gate-Up-input-audit' and terminal['audit']==audit and
         terminal['candidate_SELF_sha256']==plan['SELF']['sha256'] and terminal['all_model_source_device_owners_positively_retired'] and
         terminal['device_ledger_live_bytes']==0 and terminal['model_loads']==1 and len(terminal['requests'])==3 and
         all(r['full_F32_finite'] and r['counting_quality_passed'] and r['request_reset_completed'] for r in terminal['requests']),
         'Exact finite completed audit required')
    need(audit['completed'] and audit['all_observed_inputs_and_IDs_identical'] and audit['all48_layers_observed'] and
         audit['layer_masks']==[(1<<48)-1]*4+[0] and audit['width_buckets']==[1,2,30,32,'other'] and
         audit['calls']==sum(audit['width_calls']) and audit['width_calls'][-1]==0 and
         all(audit[k]==0 for k in ('unsupported','geometry_failures','input_pointer_mismatches','ID_pointer_mismatches',
             'retained_tensor_pointers','tensor_values_read','graph_operations_added','GPU_calls_added','scheduler_splits_added')),
         'All observed widths and layers must pass the unchanged input/ID contract')
    need(built['completed'] and built['original_GGML_operations_preserved'] and record(built['provider']['path'])==built['provider'],
         'Exact compiled observer required')
    a.out.mkdir(parents=True,exist_ok=False);source_folder=a.build.parent
    inputs=[record(source_folder/name) for name in ('gate_up_input_audit.h','gate_up_input_audit.cpp')]
    for row in inputs:
        current=record(ROOT/'native/app'/Path(row['path']).name)
        need(all(row[k]==current[k] for k in ('bytes','sha256')),'Authored observer differs from the measured compiled source')
    command=built['commands'][2].copy();artifact=a.out/'observer-reproduced.o';command[command.index('-o')+1]=str(artifact)
    result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
    (a.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
    reproduced=record(artifact)
    need(all(reproduced[k]==built['provider'][k] for k in ('bytes','sha256')),'Complete observer object did not reproduce')
    save(a.out/'result.private.json',dict(completed=True,native_requests=3,native_input_identity_qualified=True,
        graph_construction_widths=[1,2,30,32],all48_layers_per_width=True,calls=audit['calls'],width_calls=audit['width_calls'],
        original_GGML_operations_preserved=True,source_inputs=inputs,observer_object_reproduced_byte_exact=True,
        reproduced=reproduced,command=command,build=record(a.build),native_terminal=record(folder/'native.private.bin'),
        audit=record(folder/'native.audit.private.json'),closure=record(a.closure),PS5_operations=0,
        calibration_scope='Up moments cover Gate for the observed unchanged graph/input scope',
        full_quantized_model_quality_qualified=False,native_speed_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,calls=audit['calls'],all48_layers_per_width=True,widths=[1,2,30,32],PS5_operations=0)))


if __name__=='__main__':main()

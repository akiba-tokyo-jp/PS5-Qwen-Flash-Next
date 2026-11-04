#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Continue full Up placement, capacity admission and matched timing after its prefix seals."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def stable_load(path):
    for attempt in range(3):
        try:return load(path)
        except json.JSONDecodeError:
            need(attempt<2,'A terminal host receipt remains incomplete; preserve the existing owner')
            time.sleep(1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','performance-root','Up-preparation','prefix-publication','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();base=a.performance_root;up=load(a.Up_preparation)
    need(up['completed'] and up['IQ2_Up_layers']==list(range(48)) and not up.get('IQ2_Gate_layers'),
         'Only the complete uniform Up candidate may use this continuation')
    names=['publish_iq2_up_model_overlay.py','success_case_control.py','build_iq2_up_model.py',
        'iq2_up_model_scope.py','run_native_paired_down.py','run_headless_decode_sequence.py',
        'run_successful_headless_audit.py','run_successful_model_case.py','close_successful_current_model.py',
        'analyze_headless_decode_sequence.py']
    frozen=[record(ROOT/'tools'/name) for name in names]
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'intent.private.json',dict(Up_preparation=record(a.Up_preparation),
        prefix_publication=str(a.prefix_publication),tools=frozen,automatic_retries=0,
        initializer_requests=0,reboots=0,production_adoption=False,broader_quality_pending=True))
    while not a.prefix_publication.exists():time.sleep(30)
    prefix=stable_load(a.prefix_publication)
    need(prefix['completed'] and prefix['whole_new_bytes_and_all_parent_identities_qualified'],
         'The original whole-file prefix must positively seal first')
    # The finalizer writes its receipt before retiring the host-only source marker.
    deadline=time.monotonic()+60
    while True:
        state=stable_load(a.current/'active-console.private.json')
        if not state.get('source_publication_owner') and not state.get('CPU_source_seal_owner'):break
        need(time.monotonic()<deadline,'The previous IO owner must retire; do not overlap or replay it')
        time.sleep(1)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and state.get('GPU_retirement_readmission_pending') is True,
         'The expected restored P1 and completed retained-device readmission gate are required')
    def unchanged():
        need(all(record(row['path'])==row for row in frozen),'A queued workflow input changed; stop before the next operation')
    def run(name,arguments,label,timeout):
        unchanged();command=[sys.executable,'-B',str(ROOT/'tools'/name),*map(str,arguments)]
        save(a.out/(label+'-command.private.json'),dict(command=command,automatic_retries=0))
        print(json.dumps(dict(phase=label,started_once=True)),flush=True)
        with (a.out/(label+'.private.log')).open('xb') as log:
            child=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,
                env=dict(os.environ,PYTHONPATH=str(ROOT/'tools')))
        need(child.returncode==0,'Stop without retry; inspect '+str(a.out/(label+'.private.log')))
    mount=base/'mount-63133/plan.private.json'
    direct=base/'Direct-assigned-port-native-64818/result.private.json'
    arithmetic=base/'Q2-F16-storage-FP32acc-prefill-native-65313/result.private.json'
    common=['--workspace',a.workspace,'--current',a.current,'--mount-plan',mount]
    publication=a.out/'publication'
    run('publish_iq2_up_model_overlay.py',common+['--preparation',a.Up_preparation,
        '--retained-Up-publication',a.prefix_publication,'--source-seal-window-proof',
        base/'Q2-owned-sealed-fragment-native-concat-65238/result.private.json','--out',publication,'--execute'],
        'remaining-Up-source',3600)
    packages=a.out/'packages'
    run('build_iq2_up_model.py',['--workspace',a.workspace,'--current',a.current,'--preparation',a.Up_preparation,
        '--publication',publication/'result.private.json','--cache-baseline',
        base/'selected-cache-original-overlay-object-65094/result.private.json',
        '--arithmetic-qualification',arithmetic,'--out',packages],'model-packages',1200)
    capacity=a.out/'capacity'
    run('run_native_paired_down.py',common+['--package',base/'Q3-F16-six-wide-GGML-SELF-65343/result.private.json',
        '--direct-staging-proof',direct,'--mode','CPU','--CPU-startup-proof',
        base/'Q3-generic-indexed-CPU-capacity-65329/result.private.json','--retained-component-exit-proof',
        base/'Q3-generic-indexed-GGML-GPU-65330/result.private.json','--GGML-completion-controls',
        base/'Q3-F16-wide-completion-controls-65338/result.private.json','--out',capacity,'--execute'],
        'fresh-capacity',1200)
    admitted=load(capacity/'result.private.json')
    need(admitted['completed'] and admitted['native_passed'] and admitted['mode']=='CPU' and
         admitted['ordinary_exit_observed'] and admitted['current_seven_restored_and_native_hashed'],
         'The fresh actual CPU capacity control and exact ordinary restoration must pass')
    built=load(packages/'result.private.json');sequence=a.out/'ABBA'
    run('run_headless_decode_sequence.py',common+['--model-proof',base/'model-readmission-63410/model-proof.private.json',
        '--direct-staging-proof',direct,'--control',built['packages']['control']['path'],
        '--candidate',built['packages']['candidate']['path'],'--numerical-proof',arithmetic,
        '--native-VM-proof',base/'native-VM-single-reader-65028/result.private.json',
        '--scope','Q2','--case-base','65400','--out',sequence],'full-model-ABBA',3600)
    run('analyze_headless_decode_sequence.py',['--sequence',sequence/'result.private.json',
        '--out',a.out/'analysis.private.json'],'decode-analysis',120)
    save(a.out/'result.private.json',dict(completed=True,publication=record(publication/'result.private.json'),
        packages=record(packages/'result.private.json'),capacity=record(capacity/'result.private.json'),
        sequence=record(sequence/'result.private.json'),analysis=record(a.out/'analysis.private.json'),
        broader_quality_pending=True,production_adopted=False,automatic_retries=0,initializer_requests=0))
    print(json.dumps(dict(completed=True,original_decode_metric=True,quality_review_pending=True,
        production_adopted=False,automatic_retries=0)),flush=True)


if __name__=='__main__':main()

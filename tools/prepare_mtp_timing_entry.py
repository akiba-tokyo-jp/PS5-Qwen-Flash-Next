#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Enable timing of the unchanged compact MTP audit without the extra F32 SHA provider."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from mtp_shadow_host_check import require_online_profile
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.build);profile=load(old['application_policy']['path']);require_online_profile(profile)
    for name in ('source','entry','application_policy','ordinary_compact_engine_contract'):
        need(record(old[name]['path'])==old[name],'The source-correct compact build must remain exact')
    need(profile['no_unused_prefix_checkpoint'] and profile['all_original_native_guards_unchanged'],
         'Only the source-correct ordinary compact scope is admitted')
    a.out.mkdir(parents=True,exist_ok=False);prior=Path(old['source']['path']).parent
    for header in prior.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    original=Path(old['source']['path']).read_text(encoding='utf-8')
    text=once(original,'{"timings_usable_for_performance",false}','{"timings_usable_for_performance",true}')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');artifact=a.out/'entry.o'
    job=next(c for c in reversed(old['commands']) if '-c' in c and c[c.index('-c')+1]==old['source']['path']).copy()
    overlay=load(job[job.index('-ivfsoverlay')+1])
    for root in overlay['roots']:
        candidate=a.out/Path(root['external-contents']).name
        if candidate.exists():root['external-contents']=candidate.resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    job=[str(a.out) if x==str(prior) else x for x in job];job[1:1]=['-I',str(a.out)]
    job[job.index('-ivfsoverlay')+1]=str(view);job[job.index('-c')+1]=str(source);job[job.index('-o')+1]=str(artifact)
    if '-MF' in job:job[job.index('-MF')+1]=str(a.out/'entry.private.d')
    completed=subprocess.run(job,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
    (a.out/'compile.private.log').write_bytes(completed.stdout+completed.stderr)
    need(completed.returncode==0,(completed.stdout+completed.stderr).decode(errors='replace')[-3000:])
    revised=copy.deepcopy(profile);revised.update(entry_artifact=record(artifact),source=record(source),performance_timings_usable=True,
        timing_scope='Existing causal audit retained; extra full-vocabulary SHA observer omitted',
        production_adopted=False,native_performance_qualified=False)
    policy=a.out/'application-policy.private.json';save(policy,revised)
    result=copy.deepcopy(old);result.update(application_policy=record(policy),entry=record(artifact),source=record(source),
        original_instrumented_entry=record(a.build),only_terminal_timing_label_changed=True,
        extra_full_F32_SHA_provider_must_be_omitted=True,commands=old['commands']+[job])
    save(a.out/'result.private.json',result)
    print(dict(completed=True,only_terminal_label_changed=True,old_math_checks_replayed=0,PS5_operations=0))


if __name__=='__main__':main()

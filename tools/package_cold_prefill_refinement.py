#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink/package both completed P1 phase providers without replaying their checks."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','refinement','formatter-from','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();value=load(a.refinement)
    need(value['completed'] and value['actual_PS5_ABI_compiled'] and len(value['new_selector_controls'])==16,
         'Reuse all sixteen completed new request-scope controls')
    a.out.mkdir(parents=True,exist_ok=False)
    current_package=load(a.current/'provenance/current-package.private.json')
    identity=current_package['required_bundle_identity_audit']['provider']
    need(record(identity['path'])==identity,'Selected finalized input identities changed')
    base=load(a.current/'provenance/selected-entry-build.private.json');original=load(base['application_policy']['path'])
    packages={};jobs=[]
    for arm in ('control','candidate'):
        entry=value['entries'][arm];need(record(entry['entry']['path'])==entry['entry'] and record(entry['source']['path'])==entry['source'],
            'An actual completed native P1 entry changed')
        profile=copy.deepcopy(original);profile.update(kind='P1-cold-prefill',entry_artifact=entry['entry'],source=entry['source'],
            P1_refinement=record(a.refinement),P1_arm=arm,configuration_enforced_by_compiled_binary=True,
            native_performance_qualified=False,production_adopted=False)
        profile_path=a.out/(arm+'-policy.private.json');save(profile_path,profile)
        reader=profile['CPU_SELF_provider']['artifact'];need(record(reader['path'])==reader,'Original selected SELF reader changed')
        relink=a.out/(arm+'-relink');package=a.out/(arm+'-SELF')
        command=[sys.executable,'-B',str(ROOT/'tools/relink_retained_current.py'),'--current',str(a.current),'--out',str(relink),
            '--replace','entry.o='+entry['entry']['path'],'--replace','model_graph.o='+value['model_provider_reused']['path'],
            '--replace','early-SELF.o='+reader['path'],'--add-object',value['selector']['path'],
            '--link-flag=--wrap=llama_process','--link-flag=--wrap=llama_sampler_apply','--link-flag=--wrap=llama_sampler_sample',
            '--application-policy',str(profile_path)]
        packaging=[sys.executable,'-B',str(ROOT/'tools/package_retained_current.py'),'--workspace',str(a.workspace),
            '--current',str(a.current),'--relink',str(relink/'result.private.json'),'--out',str(package),'--formatter-from',str(a.formatter_from),
            '--identity-provider',identity['path']]
        for label,job in (('link',command),('package',packaging)):
            run=subprocess.run(job,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
            (a.out/(arm+'-'+label+'.private.log')).write_bytes(run.stdout+run.stderr)
            need(run.returncode==0,run.stderr.decode(errors='replace')[-4000:]);jobs.append(job)
        packages[arm]=record(package/'result.private.json')
    save(a.out/'result.private.json',dict(completed=True,refinement=record(a.refinement),packages=packages,commands=jobs,
        same_post_trunk_graph_both_arms=True,only_candidate_cold_request_narrows_outputs=True,
        retained_and_prefix_original_output_selection=True,all_original_memory_and_completion_guards=True,
        previous_checks_replayed=0,native_model_comparison_qualified=False,production_adopted=False,PS5_operations=0))
    print(json.dumps(dict(completed=True,paired_SELFs=2,old_checks_replayed=0,PS5_operations=0)))


if __name__=='__main__':main()

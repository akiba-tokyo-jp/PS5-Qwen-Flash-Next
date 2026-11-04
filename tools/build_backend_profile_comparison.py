#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price the IQ2 F32 prerequisite against current P1 before publishing model weights."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from start_success_route import load, need, save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--profiles',nargs='+',choices=('default','F32','no_mmvq'),default=['default','F32'])
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    need(len(a.profiles)==len(set(a.profiles)),'Each distinct profile may be prepared only once')
    selected=load(a.current/'provenance/selected-entry-build.private.json')
    profile=load(selected['application_policy']['path'])
    need(record(profile['source']['path'])==profile['source'],'The adopted P1 entry must remain exact')
    original=Path(profile['source']['path']);baseline=original.read_text()
    identity=load(a.current/'provenance/current-package.private.json')['required_bundle_identity_audit']['provider']
    jobs=[];packages={}
    def run(command,label):
        command=list(map(str,command));jobs.append(command)
        r=subprocess.run(command,capture_output=True,timeout=300,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-4000:])
    for arm in a.profiles:
        out=a.out/arm;out.mkdir()
        for h in original.parent.glob('*.h'):shutil.copyfile(h,out/h.name)
        scope=dict(schema='ps5-qwen-backend-profile-v1',kind='backend-profile',arm=arm,
            requests=3,model_loads=1,HTTP_requests=0,VideoOut_starts=0,
            maximum_output_tokens_per_request=32,original_cold_retained_exact_prefix_sequence=True,
            model_weights_unchanged=True,adopted_P1_graph_and_selector_unchanged=True,
            explicit_F32_profile=arm=='F32',selected_cache_slots=3712,
            original_live_reserves_preserved=True,persistent_caches=False)
        marker='        const auto policy = Json::parse(policy_file);'
        environment=''
        for name in ('GGML_VK_DISABLE_MMVQ','GGML_VK_DISABLE_F16'):
            disabled=arm=='F32' or (arm=='no_mmvq' and name=='GGML_VK_DISABLE_MMVQ')
            operation='setenv("'+name+'","1",1)' if disabled else 'unsetenv("'+name+'")'
            condition='!getenv("'+name+'")||std::strcmp(getenv("'+name+'"),"1")' if disabled else 'getenv("'+name+'")'
            environment+='        if('+operation+'||'+condition+')throw std::runtime_error("Exact backend profile unavailable");\n'
        text=once(baseline,marker,marker+'\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact backend profile scope required");\n'+environment)
        text=once(text,'(ordinal==1&&rows!=reference_rows)','false')
        text=once(text,'            else if(ordinal==1&&(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes))\n                throw std::runtime_error("Original additional tokens or bytes differ");',
            '            // Profile quality differences are recorded before ordinary owner retirement.')
        text=headless_entry(text,scope['kind'],3,'Json{{"completed",true},{"backend_profile_scope",policy.at("native_headless_model_audit")},{"requests",completed}}')
        text=once(text,'{"timings_usable_for_performance",false}','{"timings_usable_for_performance",true}')
        for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                     'model_file_identity','model_directory_identity','resident_reset_empty_context'):
            need(body(text,name)==body(baseline,name),'An original memory/identity/reset guard changed: '+name)
        source=out/'entry.private.cpp';source.write_text(text,newline='\n');obj=out/'entry.o'
        command=next(c.copy() for c in selected['commands'] if '-ivfsoverlay' in c)
        view=load(command[command.index('-ivfsoverlay')+1])
        for row in view['roots']:
            local=out/Path(row['external-contents']).name
            if local.exists():row['external-contents']=local.resolve().as_posix()
        overlay=out/'selected-view.private.json';save(overlay,view)
        command=[str(out) if v==str(original.parent) else v for v in command]
        command[1:1]=['-I',str(out)]
        command[command.index('-ivfsoverlay')+1]=str(overlay)
        command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        if '-MF' in command:command[command.index('-MF')+1]=str(out/'entry.private.d')
        run(command,arm+'-compile')
        changed=copy.deepcopy(profile)
        changed.update(kind='headless-model-audit',entry_artifact=record(obj),source=record(source),
            headless_model_audit=True,headless_audit_kind=scope['kind'],headless_requests=3,
            model_and_GPU_topology_unchanged=False,model_and_GPU_guards_preserved=True,
            overrides=dict(profile['overrides'],native_headless_model_audit=scope),
            performance_timings_usable=True,native_performance_qualified=False,production_adopted=False)
        policy=out/'application-policy.private.json';save(policy,changed)
        run([sys.executable,'-B',ROOT/'tools/relink_retained_current.py','--current',a.current,'--out',out/'link',
            '--replace','entry.o='+str(obj),'--replace','early-SELF.o='+profile['CPU_SELF_provider']['artifact']['path'],
            '--application-policy',policy],arm+'-link')
        run([sys.executable,'-B',ROOT/'tools/package_retained_current.py','--workspace',a.workspace,'--current',a.current,
            '--relink',out/'link/result.private.json','--out',out/'SELF','--formatter-from',
            a.current/'provenance/current-package.private.json','--identity-provider',identity['path']],arm+'-SELF')
        packages[arm]=record(out/'SELF/result.private.json')
    save(a.out/'result.private.json',dict(completed=True,packages=packages,commands=jobs,
        original_P1_source=profile['source'],original_memory_identity_reset_guards_unchanged=True,
        model_source_publications=0,cache_rebuilds=0,GPU_rebuilds=0,PS5_operations=0,
        native_quality_and_rate_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,packages=len(packages),model_source_publications=0,PS5_operations=0)))


if __name__=='__main__':main()

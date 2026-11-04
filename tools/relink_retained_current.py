#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the current frozen inputs without depending on deleted trial trees."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from driver_table_storage import audit_linked_storage

TABLE_SCRIPT='SECTIONS { .qwen_driver_tables (NOLOAD) : ALIGN(16384) { __qwen_driver_tables_start = .; KEEP(*(.qwen_cold_table_*)) . = ALIGN(16384); __qwen_driver_tables_end = .; } } INSERT BEFORE .bss;\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--replace',action='append',default=[],metavar='ORIGINAL_BASENAME=OBJECT')
    parser.add_argument('--add-object',action='append',default=[],type=Path)
    parser.add_argument('--link-flag',action='append',default=[])
    parser.add_argument('--application-policy',type=Path,help='Bind a compiled entry to its explicit effective application policy')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
    original=load(args.current/'provenance/native-link.receipt.private.json')
    recipe=original.get('retained_link_command',original['link_command'])
    package=load(args.current/'provenance/receipt.private.json')
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    actual=[];mapping={}
    for row in retained:
        checked=record(row['path'])
        if checked!={k:row[k] for k in ('path','bytes','sha256')}:raise ValueError('Current retained input changed')
        actual.append(checked);mapping[row['original_path']]=checked['path']
    replacements={};new=[]
    for specification in args.replace:
        name,path=specification.split('=',1)
        matches=[old for old in mapping if Path(old).name==name and old in recipe]
        if len(matches)!=1:raise ValueError('One actual linked replacement provider required: '+name)
        value=record(path);replacements[matches[0]]=value['path'];new.append(value)
    for path in args.add_object:new.append(record(path))
    application_policy=None
    if args.application_policy:
        policy=load(args.application_policy)
        guarded_headless=policy['kind']=='Q2-calibration' and policy.get('headless_calibration') and policy.get('model_and_GPU_guards_preserved')
        guarded_fixture=policy['kind']=='Q2-IQ2-fixture' and policy.get('unloaded_GPU_fixture') and policy.get('model_and_GPU_guards_preserved')
        guarded_audit=policy['kind']=='headless-model-audit' and policy.get('headless_model_audit') and policy.get('model_and_GPU_guards_preserved')
        if not policy['completed'] or policy['kind'] not in ('R1-direct','CPU-SELF-window','P1-cold-prefill','Q1-shared','Q2-calibration','Q2-IQ2-fixture','headless-model-audit') or not (policy['model_and_GPU_topology_unchanged'] or guarded_headless or guarded_fixture or guarded_audit):
            raise ValueError('A completed scoped direct-entry policy is required')
        if policy['entry_artifact'] not in new or record(policy['entry_artifact']['path'])!=policy['entry_artifact']:
            raise ValueError('The effective policy must belong to the actual replaced entry')
        if policy['kind'] in ('CPU-SELF-window','P1-cold-prefill','Q1-shared','Q2-calibration','Q2-IQ2-fixture','headless-model-audit'):
            reader=policy['CPU_SELF_provider']['artifact']
            if reader not in new or record(reader['path'])!=reader or not policy['CPU_SELF_provider']['OS_minimum_plus_21_unchanged']:
                raise ValueError('The smaller SELF window must use the actual audited CPU-only replacement provider')
        if policy['kind']=='P1-cold-prefill':
            proof=policy['P1_refinement'];checked=load(proof['path'])
            if record(proof['path'])!=proof or not checked['completed'] or len(checked['new_selector_controls'])!=16 or not checked['actual_PS5_ABI_compiled']:
                raise ValueError('Actual completed cold/retained/prefix selector controls required')
            arm=policy['P1_arm']
            if arm not in ('control','candidate') or checked['entries'][arm]['entry']!=policy['entry_artifact'] or checked['entries'][arm]['source']!=policy['source'] or checked['selector'] not in new or checked['model_provider_reused'] not in new:
                raise ValueError('The exact scoped P1 entry, selector and completed post-trunk graph must be linked together')
        application_policy=dict(profile=record(args.application_policy),overrides=policy['overrides'],kind=policy['kind'],
                                token_sync_policy=policy['token_sync_policy'])
        if policy['kind']=='Q1-shared' or (policy['kind']=='headless-model-audit' and 'model_layer' in policy):
            layer=policy['model_layer']
            if record(layer['publication']['path'])!=layer['publication'] or not load(layer['publication']['path'])['completed']:
                raise ValueError('A positively completed new-only source publication is required')
            if policy['kind']=='headless-model-audit':
                valid=(layer['kind'],policy['headless_audit_kind']) in (
                    ('IQ2-Up','Q2-IQ2-Up-model'),('IQ2-Gate-Up','Q2-IQ2-Gate-Up-model'),('IQ2-Down','Q3-IQ2-Down-model'))
                if not valid:raise ValueError('Only an explicitly compiled and qualified IQ2 model layer may extend this headless scope')
                from iq2_up_model_scope import require_cache_layout
                require_cache_layout(policy)
                from iq2_format_stream_scope import require_stream_profile
                stream = require_stream_profile(policy)
                if stream:
                    caches=[p for p in replacements if Path(p).name=='cache.o']
                    owner=stream['unchanged_original_source_owner']
                    if len(caches)!=1 or replacements[caches[0]]!=stream['artifact']['path'] or owner not in actual or any(Path(p).name=='owner.o' for p in replacements):
                        raise ValueError('Format streaming must link its exact cache with the byte-exact original source owner')
                    if stream['wrapper'] and (stream['wrapper'] not in new or not all(f in args.link_flag for f in stream['required_link_flags'])):
                        raise ValueError('The exact request wrapper and explicit link flag must be linked together')
                    if policy['overrides']['native_headless_model_audit']['format_stream_observation_only']:
                        observer=load(policy['qualification_observer']['path'])
                        if observer['artifact'] not in new or not all(f in args.link_flag for f in observer['link_flags']):
                            raise ValueError('Native stream observation requires the actual complete F32 observer')
                if layer['kind']=='IQ2-Down':
                    scope=policy['overrides']['native_headless_model_audit'];provider=load(scope['Down_resource_provider']['path'])
                    for name,key in (('gpu.o','GPU'),('shader-registry.o','shader_registry')):
                        matches=[p for p in replacements if Path(p).name==name]
                        if len(matches)!=1 or replacements[matches[0]]!=provider[key]['path']:
                            raise ValueError('The exact qualified Down GPU and registry providers must be selected')
                    if any(provider[k] not in new for k in ('shader_data','shader_wrapper')) or not all(f in args.link_flag for f in provider['link_flags']):
                        raise ValueError('The complete qualified Down data and shader lease providers must be linked')
                    caches=[p for p in replacements if Path(p).name=='cache.o']
                    disabled = policy.get('original_Q2_bundle_and_six_refill_paths_disabled') if stream else policy['original_Q2_bundle_six_refill_and_quad_paths_disabled']
                    if len(caches)!=1 or replacements[caches[0]]!=policy['candidate_cache_provider']['path'] or not disabled:
                        raise ValueError('The Down carrier cache must disable incompatible original Q2 payload paths')
                    source=policy['candidate_cache_source']
                    if record(source['path'])!=source or 'const bool bundle_refill=false;' not in Path(source['path']).read_text() or 'const bool six_refill=false;' not in Path(source['path']).read_text():
                        raise ValueError('The exact compiled Down cache source must disable original bundle and six-bank payloads')
            application_policy['model_layer']=layer
    tables=original['lossless_driver_tables'];script=args.out/'tables.ld'
    script.write_text(TABLE_SCRIPT,encoding='utf-8',newline='\n')
    if record(script)['sha256']!=tables['linker_script']['sha256']:raise ValueError('Exact selected table script was not reconstructed')
    mapping[tables['linker_script']['path']]=str(script)
    image=args.out/'qwen-native.pie.elf';command=[]
    for argument in recipe:
        if argument.startswith('-Map='):argument='-Map='+str(args.out/'native-link.private.map')
        command.append(replacements.get(argument,mapping.get(argument,argument)))
    command[command.index('-o')+1]=str(image)
    command[1:1]=args.link_flag+[str(p.resolve()) for p in args.add_object]
    result=subprocess.run(command,capture_output=True,timeout=600,
                          env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'link.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-5000:])
    for before in actual:
        if record(before['path'])!=before:raise ValueError('Retained provider changed during relink')
    geometry=audit_linked_storage(image,tables)
    artifact=record(image)
    baseline=not(args.replace or args.add_object or args.link_flag)
    if baseline and artifact['sha256']!=package['native_pie']['sha256']:
        raise ValueError('The no-change relink is not byte-identical to the deployed native ELF')
    report=dict(completed=True,baseline_relink=baseline,
                exact_current_native_ELF_reproduced=baseline,
                original_native_ELF_SHA256=package['native_pie']['sha256'],artifact=artifact,
                current_manifest=record(args.current/'deployment.private.json'),
                retained_inputs_verified=len(actual),inputs=actual,new_inputs=new,
                replacements=replacements,link_command=command,driver_table_geometry=geometry,
                driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',driver_profile='cumulative-idle',
                persistent_caches=False,SELF_packaged=False,PS5_operations=0,native_quality_or_speed_measured=False,
                production_adopted=False)
    if application_policy:report['effective_application_policy']=application_policy
    (args.out/'result.private.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('artifact','current_manifest','inputs','new_inputs',
                                                              'replacements','link_command','driver_table_geometry','effective_application_policy')}))


if __name__=='__main__':main()

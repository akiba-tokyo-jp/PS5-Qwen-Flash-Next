#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Adopt the positively qualified direct R1 build with canonical rebuild inputs."""
import argparse
import copy
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

from build_performance_quantizer import record
from driver_table_storage import audit_linked_storage
from relink_retained_current import TABLE_SCRIPT
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module

ROOT=Path(__file__).resolve().parents[1]


def atomic_json(path,value):
    pending=path.with_name(path.name+'.pending-'+secrets.token_hex(8))
    save(pending,value);os.replace(pending,path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','package','entry-build','analysis','numerics','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);performance=load(args.analysis);numerics=load(args.numerics)
    need(performance['completed'] and performance['scope']=='R1-direct' and performance['native_requests']==12 and
         performance['both_warm_whole_request_gains_beyond_control_spread'] and
         performance['all_actual_native_token_bytes_exact'] and performance['all_actual_ordered_routes_exact'] and
         performance['all_source_demand_equal'] and performance['all_completed_durable_token_payloads_exact'] and
         performance['all_counting_and_finite_F32_checks_passed'] and performance['all_ordinary_closes_and_exact_restores'] and
         performance['final_token_ledger_sync_and_close_included_in_complete_request_span'],
         'A positively completed direct R1 ABBA with complete warm gains and exact state/output evidence is required')
    need(numerics['completed'] and numerics['whole_F32_bytes_routes_tokens_exact'] and numerics['native_cases']==2 and
         numerics['matched_whole_vocabulary_columns']==248320 and numerics['full_F32_rows_per_case']==69 and
         numerics['all_ordinary_closes_and_exact_restores'],'The separate closed whole-vocabulary R1 comparison is required')
    package=load(args.package);effective=package['effective_application_policy'];profile=load(effective['profile']['path'])
    need(record(effective['profile']['path'])==effective['profile'] and profile['kind']=='R1-direct' and
         profile['token_sync_policy']=='request_end' and profile['model_and_GPU_topology_unchanged'],
         'Only the exact directly compiled, explicitly disclosed request-end implementation may be adopted')
    sequence=load(performance['evidence'][0]['path'])
    need(all(load(sequence['cases'][i]['package']['path'])['SELF']==package['SELF'] for i in (1,2)),
         'The production SELF must be the actually measured direct candidate')
    comparison=load(numerics['evidence'][0]['path']);checked_package=load(comparison['cases'][1]['package']['path'])
    need(load(checked_package['effective_application_policy']['profile']['path'])['entry_artifact']==profile['entry_artifact'],
         'The exact production entry must have passed full-row qualification')
    entry_build=load(args.entry_build);need(entry_build['completed'] and
        entry_build['artifacts']['candidate']['entry']==profile['entry_artifact'],'The actual paired entry build is required')
    for row in (profile['entry_artifact'],profile['source'],package['SELF']):need(record(row['path'])==row,'Qualified input changed')
    current=args.current;state_path=current/'active-console.private.json';state=load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positive idle native completion required before adoption')
    old=current_files(current);prior=load(current/'provenance/native-link.receipt.private.json')
    old_package=load(current/'provenance/receipt.private.json');retained=load(current/'provenance/retained-relink-inputs.private.json')
    for row in retained:need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Current rebuild input changed')
    save(args.out/'intent.private.json',dict(old_files=old,qualified_SELF=package['SELF'],performance=record(args.analysis),
        whole_F32=record(args.numerics),native_publications_maximum=1,title_launches=0,initializer_requests=0,automatic_retries=0))
    view=current/'provenance'/('R1-source-'+secrets.token_hex(8));view.mkdir()
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,view/header.name)
    source=view/'entry.private.cpp';shutil.copyfile(profile['source']['path'],source)
    command=entry_build['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent)
    overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(view/Path(root['external-contents']).name).resolve().as_posix()
    selected=view/'selected-view.private.json';save(selected,overlay)
    command=[str(view) if v==old_view else v for v in command];command[command.index('-ivfsoverlay')+1]=str(selected)
    obj=args.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(args.out/'entry.private.d')
    result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'canonical-compile.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    need(all(record(obj)[k]==profile['entry_artifact'][k] for k in ('bytes','sha256')),
         'Canonical selected headers/source must reproduce the entire qualified entry object byte-for-byte')
    canonical_obj=current/'linked-inputs'/(record(obj)['sha256'][:16]+'-entry.o');shutil.copyfile(obj,canonical_obj)
    identity=load(package['required_bundle_identity_audit']['provider']['path'])
    for row in (identity['artifact'],identity['source']):need(record(row['path'])==row,'Qualified data-only identity provider changed')
    identity_obj=current/'linked-inputs'/(identity['artifact']['sha256'][:16]+'-required-input-identities.o')
    shutil.copyfile(identity['artifact']['path'],identity_obj);identity_source=view/'required-input-identities.c'
    shutil.copyfile(identity['source']['path'],identity_source)
    new_inputs=[];entries=sources=0
    for row in retained:
        item=dict(row);name=Path(row['original_path']).name
        if name=='entry.o':item.update(record(canonical_obj));entries+=1
        if name=='entry.private.cpp':item.update(record(source));sources+=1
        new_inputs.append(item)
    need(entries==sources==1,'One actually selected entry object and source required')
    new_inputs.extend(dict(record(p),original_path=str(p)) for p in (identity_obj,identity_source))
    mapping={r['original_path']:r['path'] for r in new_inputs}
    tables=copy.deepcopy(prior['lossless_driver_tables']);script=view/'tables.ld';script.write_text(TABLE_SCRIPT,encoding='utf-8',newline='\n')
    need(record(script)['sha256']==tables['linker_script']['sha256'],'The selected driver linker script changed')
    logical=prior.get('retained_link_command',prior['link_command']).copy()
    logical=[str(script) if v==tables['linker_script']['path'] else v for v in logical];logical[1:1]=[str(identity_obj)]
    tables['linker_script']=record(script);mapping[str(script)]=str(script)
    image=args.out/'qwen-native.pie.elf';link=[mapping.get(v,v) for v in logical]
    link=[('-Map='+str(args.out/'canonical-link.private.map')) if v.startswith('-Map=') else v for v in link]
    link[link.index('-o')+1]=str(image)
    result=subprocess.run(link,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
    (args.out/'canonical-link.private.log').write_bytes(result.stdout+result.stderr)
    need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    measured_link=load(package['relink']['path'])
    need(all(record(image)[k]==measured_link['artifact'][k] for k in ('bytes','sha256')),
         'Canonical current-only inputs must reproduce the complete actually measured native ELF byte-for-byte')
    geometry=audit_linked_storage(image,tables)
    canonical_image=current/'provenance/qwen-native.pie.elf';canonical_SELF=current/'eboot.bin'
    new_profile=dict(profile,entry_artifact=record(canonical_obj),source=record(source),native_performance_qualified=True)
    profile_path=view/'application-policy.private.json';save(profile_path,new_profile)
    effective=dict(effective,profile=record(profile_path))
    development=load(current/'qwen-runtime/development.json');development.update(effective['overrides'])
    gate=development['native_first_generation_validation'];gate.update(candidate_SELF_bytes=package['SELF']['bytes'],candidate_SELF_sha256=package['SELF']['sha256'])
    development_path=args.out/'development.json';save(development_path,development)
    app_path=args.out/'app.json';shutil.copyfile(old[1]['path'],app_path)
    updates=[dict(package['SELF'],remote=old[0]['remote']),dict(record(app_path),remote=old[1]['remote']),dict(record(development_path),remote=old[2]['remote'])]
    selected_files={r['remote']:r for r in updates};new=[selected_files.get(r['remote'],r) for r in old]
    prefix='/data/ai/moss-qwen-case-'+secrets.token_hex(16)
    pending=[dict(r,target=r['remote'],remote=prefix+('-candidate-SELF.bin' if i==0 else '-'+str(i)+'.json')) for i,r in enumerate(updates)]
    publication=build(args.workspace,args.mount_plan,old,new,pending,'publish',args.out/'publication')
    save(args.out/'prepared.private.json',dict(completed=True,canonical_entry_byte_exact=True,canonical_native_ELF_byte_exact=True,
        selected_inputs=len(new_inputs),application_policy=record(profile_path),publication=record(args.out/'publication/plan.private.json'),
        no_driver_or_model_changes=True,PS5_operations=0,production_adopted=False))
    if not args.execute:print('Canonical R1 adoption prepared and byte-exact; PS5 operations=0');return
    # The concrete production payload and its complete rebuild proof are ready.
    state.update(state='verified_R1_publication_in_progress',unknown_completion=True)
    atomic_json(state_path,state);lan=lan_module();publish(lan,pending,publication,args.out/'publication')
    # Publication positively hashes all seven files in both console namespaces.
    # Replace the PC's selected files, without creating a rollback archive.
    for source_path,target in ((package['SELF']['path'],canonical_SELF),(app_path,Path(old[1]['path'])),
                               (development_path,Path(old[2]['path'])),(image,canonical_image)):
        staged=Path(target).with_name(Path(target).name+'.pending-'+secrets.token_hex(8));shutil.copyfile(source_path,staged);os.replace(staged,target)
    selected_SELF=record(canonical_SELF);native_image=record(canonical_image)
    command[command.index('-o')+1]=str(canonical_obj)
    import_stubs=current/'provenance/import-stubs';import_stubs.mkdir(exist_ok=True);formatter_stubs=[]
    convert=next(job for name,job in package['commands'] if name=='convert')
    for index,value in enumerate(convert):
        if value=='--stub':
            stub=Path(convert[index+1]);target=import_stubs/stub.name;shutil.copyfile(stub,target)
            need(record(target)['sha256']==record(stub)['sha256'],'Qualified formatter import stub changed')
            formatter_stubs.append(record(target))
    need(formatter_stubs,'The actual qualified formatter requires explicit import stubs')
    revision=subprocess.check_output(['git','rev-parse','9601f90'],cwd=ROOT,text=True).strip()
    full_native=copy.deepcopy(prior);full_native.update(artifact=native_image,link_command=link,retained_link_command=logical,
        compile_commands=[command,*prior['compile_commands'][1:]],inputs_before=[{k:r[k] for k in ('path','bytes','sha256')} for r in new_inputs],
        lossless_driver_tables=tables,lossless_driver_table_geometry=geometry,formatter_stubs=formatter_stubs,
        selected_R1_application_layer=dict(profile=record(profile_path),performance=record(args.analysis),whole_F32=record(args.numerics),
            base_application_source='2b683814c9b6ed18c13352963c0a989f9e4d0b15',source_overlay_commit=revision))
    atomic_json(current/'provenance/native-link.receipt.private.json',full_native)
    atomic_json(current/'provenance/retained-relink-inputs.private.json',new_inputs)
    rebuild=dict(measured_link,artifact=native_image,inputs=[{k:r[k] for k in ('path','bytes','sha256')} for r in new_inputs],
        new_inputs=[record(identity_obj)],link_command=link,effective_application_policy=effective,production_adopted=True)
    rebuild_path=current/'provenance/current-native-rebuild.private.json';atomic_json(rebuild_path,rebuild)
    formatter=current/'provenance/ps5-native-tool.exe';shutil.copyfile(package['formatter']['path'],formatter)
    selected_package=dict(package,SELF=selected_SELF,relink=record(rebuild_path),formatter=record(formatter),
        effective_application_policy=effective,native_quality_or_speed_measured=True,production_adopted=True)
    package_path=current/'provenance/current-package.private.json';atomic_json(package_path,selected_package)
    old_package.update(SELF=selected_SELF,native_pie=native_image,native_link_receipt=record(current/'provenance/native-link.receipt.private.json'),
        format_tool=record(formatter),installed=True,model_loaded=False,release_qualified=True,selected_R1_package=record(package_path))
    atomic_json(current/'provenance/receipt.private.json',old_package)
    deployment=load(current/'deployment.private.json');deployment.update(SELF=selected_SELF,
        application_files=[dict(record(r['path']),remote=r['remote']) for r in deployment['application_files']],
        application_source_revision=revision,rebuilt_or_relinked=True,
        retained_relink_input_manifest=record(current/'provenance/retained-relink-inputs.private.json'),
        current_validation_status='R1-native-ABBA-and-full-F32-qualified-adopted',inference_admitted=True,
        selected_package=record(package_path),R1_adoption=dict(performance=record(args.analysis),whole_F32=record(args.numerics),
            per_token_fsync_preserved=False,token_record_sync_policy='request_end',completed_ledger_synced_before_result=True,
            interrupted_request_may_lose_unsynced_tail=True))
    atomic_json(current/'deployment.private.json',deployment)
    state.update(state='verified_R1_selected_PC_and_PS5_native_hashed_idle',original_restored=True,native_running=False,model_loaded=False,
        gateway_running=False,native_owners=0,unknown_completion=False,current_boot_Qwen_model_admitted=True,
        current_boot_readmission_pending=False,selected_current_SELF=selected_SELF)
    state['selected_R1_adoption']=dict(package=record(package_path),publication=record(args.out/'publication/result.private.json'),
        performance=record(args.analysis),whole_F32=record(args.numerics));atomic_json(state_path,state)
    result=dict(completed=True,production_adopted=True,SELF=selected_SELF,retained_inputs=len(new_inputs),
        PC_and_PS5_same_selected_current=True,all_seven_console_files_native_hashed_both_namespaces=True,
        canonical_entry_and_ELF_byte_exact=True,driver_and_model_unchanged=True,persistent_caches=False,
        token_record_sync_policy='request_end',completed_ledger_synced_before_result=True,interrupted_request_may_lose_unsynced_tail=True,
        native_running=False,model_loaded=False,unknown_completion=False,title_launches=0,initializer_requests=0,automatic_retries=0)
    save(args.out/'result.private.json',result);print(json.dumps(result))


if __name__=='__main__':main()

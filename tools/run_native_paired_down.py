#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure standalone native startup, then separately admit its finite GPU scope."""
import argparse
import json
from pathlib import Path
import secrets
import struct
import time
import urllib.error
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query
from run_successful_model_case import publish
from price_unloaded_iq2_startup import initializer_count
from start_success_route import load, need, save
from success_case_control import ALIAS, PHYSICAL, build, current_files, execute, lan_module


def exact(row):
    need(record(row['path'])==row,'An immutable standalone native input changed')
    return load(row['path'])


def geometry(package):
    linked=exact(package['relink']);need(record(linked['artifact']['path'])==linked['artifact'],'Actual linked ELF changed')
    raw=Path(linked['artifact']['path']).read_bytes();offset=struct.unpack_from('<Q',raw,32)[0]
    stride,count=struct.unpack_from('<HH',raw,54)
    need(stride==56 and count>0,'Complete ELF64 program headers required')
    rows=[struct.unpack_from('<IIQQQQQQ',raw,offset+i*stride) for i in range(count)]
    file_pages=sum((h[5]+16383)//16384 for h in rows if h[0]==1)
    zero_pages=sum((h[6]-h[5]+16383)//16384 for h in rows if h[0]==1)
    return dict(file_pages=file_pages,zero_pages=zero_pages)


def price_CPU(package,prior_dir):
    done=load(prior_dir/'result.private.json');closed=exact(done['closure']);terminal=exact(done['terminal'])
    need(done['completed'] and closed['ordinary_exit_observed'] and not closed['unknown_completion'] and
         terminal['audit']['GPU_calls']==terminal['audit']['model_loads']==0,'Completed current-boot original CPU control required')
    old_case=load(prior_dir/'case/plan.private.json');old=exact(old_case['package'])
    vm=load(prior_dir/'VM-before/result.private.json')['observations'];native=terminal['audit']['main_SELF']
    need(native['completed'] and native['full_current_SELF_SHA256_passed'] and vm['minimum']==898 and vm['page_bytes']==16384,
         'Exact positive original SELF and memory geometry required')
    current,control=geometry(package),geometry(old)
    constructors,old_constructors=initializer_count(package),initializer_count(old)
    need(constructors<=old_constructors,'Additional unmeasured constructors require separate pricing')
    removed=max(0,control['file_pages']-current['file_pages'])
    added=max(0,current['zero_pages']-control['zero_pages'])
    startup=min(vm['free_first'],vm['free_last'])-native['free_before']
    required=startup-removed+added+1154+256
    return dict(mode='CPU',required_pages=required,observed_control_constructor_global_drop=startup,
        removed_ELF_file_pages=removed,additional_ELF_zero_pages=added,native_IO_floor=1154,selected_operational_slack=256,
        changed_reader='Static64KiB, unchanged minimum/reserve predicate, bounded passive wait before a read',
        control=record(prior_dir/'result.private.json'),geometry=current,constructors=constructors,control_constructors=old_constructors,
        empirical_cost_model_not_measured_RAM_gain=True,universal_allocation_bound_claimed=False,ordinary_model_screen_unchanged=7374)


def price_GPU(package_path,startup_path,reuse_path=None):
    done=load(startup_path)
    need(done['completed'] and done['mode']=='CPU' and done['native_passed'] and done['ordinary_exit_observed'] and
         done['current_seven_restored_and_native_hashed'],
         'The standalone binary needs positive CPU startup and ordinary restoration first')
    extra=0
    if done['package']!=record(package_path):
        need(reuse_path is not None,'A different binary needs exact CPU-code reuse qualification')
        reuse=load(reuse_path)
        need(reuse['completed'] and reuse['startup']==record(startup_path) and reuse['new_package']==record(package_path) and
             reuse['old_package']==done['package'] and reuse['GPU_only_completed_case_checkpoint_insertion'] and
             reuse['actual_C_reader_and_hash_objects_byte_exact'] and
             'main' in reuse['actual_CPU_functions_and_normalized_relocations_equal'],
             'Exact actual CPU code/relocations and the sole GPU boundary insertion must be qualified')
        extra=reuse['additional_ELF_pages_priced']
    native=exact(done['native']);before=exact(done['VM_before'])['observations']
    need(native['SELF_verified'] and native['GPU_calls']==native['model_loads']==native['source_payload_reads']==0 and
         native['CPU_libc_fallbacks']==0 and native['CPU_heap_peak_bytes']<=64<<20,
         'Exact completed standalone CPU allocation observations required')
    low=min(native['VM_main_free'],native['VM_after_SELF_free'],native['VM_minimum_SELF_free'])
    drop=max(0,min(before['free_first'],before['free_last'])-low)
    return dict(mode='GPU',required_pages=drop+162+1185+256+256+extra,observed_CPU_code_startup_drop_pages=drop,
        previously_observed_successful_Direct_table_and_pre_GPU_tail_pages=162,native_before_GPU_floor=1185,
        selected_GPU_metadata_allowance=256,selected_operational_slack=256,startup_proof=record(startup_path),
        additional_ELF_pages=extra,CPU_code_reuse=record(reuse_path) if reuse_path else None,
        universal_allocation_bound_claimed=False,ordinary_model_screen_unchanged=7374)


def completed_operation(lan,plan,out):
    try:return execute(lan,plan,out,60)
    except Exception:
        need((out/'execution/execution.once.private.json').exists(),'No submitted operation exists to collect')
        from success_case_control import complete
        deadline=time.monotonic()+90
        while True:
            raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20,8)
            if b'\nEND ' in raw:break
            need(time.monotonic()<deadline,'Retain the same unknown operation; never resubmit it');time.sleep(1)
        path=out/'collected-native.private.log';path.write_bytes(raw)
        return complete(lan,plan,out,raw,path)


def publish_pack(a,lan,relink,rows):
    from direct_component_staging import upload
    pack=relink['component_pack'];local=pack['local'];application=pack['application_path']
    need(record(local['path'])==local and local['bytes']<=128<<20 and application==
         '/app0/qwen-runtime/paired-Down-'+local['sha256'][:24]+'.bin','Exact standalone component pack required')
    if a.component_pack_proof:
        previous=load(a.component_pack_proof)
        need(previous['completed'] and previous['whole_SHA256_both_namespaces'] and previous['immutable_mode']==292 and
             all(previous['pack'][k]==local[k] for k in ('bytes','sha256')) and
             previous['target']==PHYSICAL+application[5:] and previous['alias']==ALIAS+application[5:],
             'Only the exact previously sealed unchanged content-bound component pack may be reused')
        save(a.out/'component-pack-reuse.private.json',dict(completed=True,previous=record(a.component_pack_proof),
            pack=local,new_transfers=0,new_publications=0,fresh_whole_SHA_required_natively_before_GPU=True))
        return
    out=a.out/'component-pack';out.mkdir()
    need(a.component_transfer_proof is not None or a.model_part_receiver_proof is not None,
         'Completed component-size or bounded model-part receiver controls required before native transfer')
    size_control=a.component_transfer_proof
    pending='/data/ai/moss-qwen-case-'+secrets.token_hex(16)+'-candidate-SELF.bin'
    target=PHYSICAL+application[5:];alias=ALIAS+application[5:]
    lan.absent(pending);lan.absent(target)
    context='#define CASE_COMPONENT_PENDING '+json.dumps(pending)+'\n#define CASE_COMPONENT_TARGET '+json.dumps(target)+'\n'
    context+='#define CASE_COMPONENT_ALIAS '+json.dumps(alias)+'\n#define CASE_COMPONENT_BYTES '+str(local['bytes'])+'ULL\n'
    context+='#define CASE_COMPONENT_SHA256 '+json.dumps(local['sha256'])+'\n'
    plan=build(a.workspace,a.mount_plan,rows,rows,[],'publish-component',out/'native',component_publish_context=context)
    save(out/'intent.private.json',dict(pack=local,pending=pending,target=target,alias=alias,maximum_publications=1))
    def verify(capture,remote):
        need(remote==pending,'Exact new component staging path required')
        result=completed_operation(lan,plan,out/'native');need(result['operation_calls']==1,'One complete new-only publication required')
        return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,sha256=local['sha256'],bytes=local['bytes'])
    if a.model_part_receiver_proof:
        from direct_model_part import stage
        stage(local,pending,out/'Direct-transfer',lan,workspace=a.workspace,current_rows=rows,
              mount_plan=a.mount_plan,original_proof=a.direct_staging_proof,receiver_proof=a.model_part_receiver_proof)
        verify(local,pending)
    else:
        upload(local,pending,out/'Direct-transfer',lan,verify,current_rows=rows,workspace=a.workspace,
               mount_plan=a.mount_plan,qualified=a.direct_staging_proof,component_control=size_control)
    save(out/'result.private.json',dict(completed=True,pack=local,target=target,alias=alias,whole_SHA256_both_namespaces=True,
        immutable_mode=292,current_seven_unchanged=True,title_launches=0,GPU_calls=0))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','package','direct-staging-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=('CPU','GPU'),required=True)
    p.add_argument('--prior-CPU',type=Path)
    p.add_argument('--startup-proof',type=Path)
    p.add_argument('--startup-reuse',type=Path)
    p.add_argument('--component-transfer-proof',type=Path)
    p.add_argument('--component-pack-proof',type=Path)
    p.add_argument('--model-part-receiver-proof',type=Path)
    p.add_argument('--pre-device-exit-proof',type=Path)
    p.add_argument('--post-completion-close-proof',type=Path)
    p.add_argument('--P1-contract-close-proof',type=Path)
    p.add_argument('--retained-component-exit-proof',type=Path)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    package=load(a.package);relink=exact(package['relink'])
    need(package['completed'] and package['normalized_SELF_roundtrip_equal'] and not package['CPU_only'] and
         relink['completed'] and not relink['model_engine_linked'] and relink['CPU_startup_only_mode'] and
         relink['same_selected_Direct_table_mapping_and_incremental_restoration'] and
         (relink['new_post_device_controls']==15 or (relink.get('retained_idle_device_until_ordinary_close') and
          relink.get('paired_down_carrier') and relink.get('retained_device_controls')==19)) and
         len(relink['linked_driver'])==1 and relink['maximum_GPU_dispatches']==24 and
         relink['successful_driver_whole_archive_preserved'] and
         all(r['pointer_matches'] for r in relink['actual_physical_dispatch_audit']),
         'Exact new standalone package and all actual driver callbacks required')
    image=package['SELF'];need(record(image['path'])==image and image['bytes']<=32<<20,'Exact native standalone SELF required')
    pricing=price_CPU(package,a.prior_CPU) if a.mode=='CPU' else price_GPU(a.package,a.startup_proof,a.startup_reuse)
    save(a.out/'pricing.private.json',pricing)
    if not a.execute:
        print(json.dumps(dict(prepared=True,pricing=pricing,PS5_operations=0)));return
    state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'],'Restored idle native process state required')
    readmission=None
    if state['unknown_completion'] or state.get('GPU_retirement_readmission_pending'):
        need(a.mode=='CPU' and sum(x is not None for x in (a.pre_device_exit_proof,a.post_completion_close_proof,a.P1_contract_close_proof,a.retained_component_exit_proof))==1 and relink['CPU_Direct_capacity_readmission'],
             'Only an explicitly qualified CPU capacity readmission may run while GPU capacity admission is pending')
        if a.retained_component_exit_proof:
            readmission=load(a.retained_component_exit_proof)
            from retained_component_completion import validate_terminal
            need(readmission['completed'] and readmission['native_passed'] and readmission['ordinary_exit_observed'] and
                 readmission['completed_idle_device_retained_until_ordinary_exit'] and readmission['fresh_capacity_readmission_required'] and
                 readmission['current_seven_restored_and_native_hashed'] and not readmission['unknown_completion'] and
                 state['retained_component_ordinary_exit']['native']==readmission['native'] and
                 readmission['package']==record(a.package) and record(readmission['native']['path'])==readmission['native'],
                 'The exact completed retained owner, same package and positive ordinary exit are required')
            validate_terminal(load(readmission['native']['path']))
        elif a.P1_contract_close_proof:
            readmission=load(a.P1_contract_close_proof)
            known_P1=(readmission['all_five_initialization_GPU_epochs_completed'] and readmission['target_request_operations']==0) or (
                 readmission.get('checkpoint_preallocation_refusal') is True and readmission.get('last_active_epoch_positive_checkpoint') is True and
                 readmission['target_request_operations']==2) or (
                 readmission.get('G1_integrated_device_refusal') is True and readmission['target_request_operations']==0) or (
                 readmission.get('S1_post_request_certificate_refusal') is True and readmission['target_request_operations']==1)
            need(readmission['completed'] and readmission['ordinary_OS_closes']==1 and readmission['ordinary_exit_observed'] and
                 readmission['current_seven_restored_and_native_hashed'] and known_P1 and
                 not readmission['unknown_completion'] and readmission['GPU_capacity_readmission_pending'] and
                 state['GPU_retirement_readmission_proof']==record(a.P1_contract_close_proof) and
                 record(readmission['source_audit']['path'])==readmission['source_audit'],
                 'Exact P1 pre-request CPU refusal, completed initialization epochs and ordinary exit required')
        elif a.post_completion_close_proof:
            readmission=load(a.post_completion_close_proof)
            need(readmission['completed'] and readmission['ordinary_OS_closes']==1 and readmission['ordinary_exit_observed'] and
                 readmission['current_seven_restored_and_native_hashed'] and readmission['positive_reference_dispatches']==24 and
                 not readmission['unknown_completion'] and readmission['GPU_capacity_readmission_pending'] and
                 state['paired_Down_positive_boundary_close']==readmission['source_audit'] and
                 record(readmission['source_audit']['path'])==readmission['source_audit'],
                 'Exact completed GPU boundary, ordinary exit and current restoration required')
        else:
            readmission=load(a.pre_device_exit_proof)
            need(readmission['completed'] and readmission['known_pre_device_process_exit'] and
                 readmission['source_bound_frontend_queue_submissions']==0 and readmission['complete_driver_journal_contains_no_submission'] and
                 readmission['only_capacity_CPU_readmission_permitted'] and readmission['current_boot']==state['current_boot'],
                 'Exact same-boot pre-device process exit and zero submission evidence required')
    lan=lan_module();vm_dir=a.out/'VM-before';vm_dir.mkdir();vm=query(lan.HOST,vm_dir)
    need(vm['boot_before']==vm['boot_after']==state['current_boot'] and vm['minimum']==898 and
         vm['reserved']==206 and vm['page_bytes']==16384,'Exact current boot and native page geometry required')
    admitted=min(vm['free_first'],vm['free_last'])>=pricing['required_pages']
    save(vm_dir/'result.private.json',dict(completed=True,observations=vm,pricing=pricing,admitted=admitted))
    need(admitted,'Changed standalone scope refuses before any publication or title launch')
    old=current_files(a.current)
    if a.mode=='GPU':
        print(json.dumps(dict(phase='new-component-pack-publication')),flush=True);publish_pack(a,lan,relink,old)
    run=secrets.token_hex(16);report='/app0/qwen-runtime/plan-'+run+'.json'
    policy=dict(schema='ps5-qwen-paired-Down-native-v1',run_id=run,SELF_bytes=image['bytes'],SELF_sha256=image['sha256'],
                component_pack_sha256=relink['component_pack']['local']['sha256'],CPU_only=a.mode=='CPU')
    policy_path=a.out/'development.json';policy_path.write_text(json.dumps(policy,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
    replacements=[dict(image,remote=old[0]['remote']),old[1],dict(record(policy_path),remote=old[2]['remote'])]
    new=replacements+old[3:];prefix='/data/ai/moss-qwen-case-'+run
    pending=[dict(row,target=row['remote'],remote=prefix+('-candidate-SELF.bin' if i==0 else '-'+str(i)+'.json')) for i,row in enumerate(replacements)]
    publication=build(a.workspace,a.mount_plan,old,new,pending,'publish',a.out/'publication')
    launch=build(a.workspace,a.mount_plan,new,new,[],'launch',a.out/'launch')
    save(a.out/'plan.private.json',dict(package=record(a.package),mode=a.mode,run_id=run,report=report,SELF=image,
        old_files=old,new_files=new,pending=pending,maximum_title_launches=1,initializer_requests=0))
    state['active_successful_native_case']=dict(plan=record(a.out/'plan.private.json'),run_id=run,phase='standalone-Q3-publication')
    state['state']='standalone_Q3_publication_in_progress';state_path.write_text(json.dumps(state,indent=2)+'\n')
    direct=dict(workspace=a.workspace,mount_plan=a.mount_plan,qualified=a.direct_staging_proof)
    print(json.dumps(dict(phase='standalone-publication',mode=a.mode,required=pricing['required_pages'],free=vm['free_last'])),flush=True)
    publish(lan,pending,publication,a.out/'publication',direct_staging=direct)
    state.update(original_restored=False,temporary_installed_SELF=image);state_path.write_text(json.dumps(state,indent=2)+'\n')
    launched=completed_operation(lan,launch,a.out/'launch');need(launched['operation_calls']==1,'One accepted ordinary native launch required')
    state.update(native_running=True,unknown_completion=True)
    state['active_successful_native_case'].update(phase='standalone-Q3-completion-pending',app_id=launched['app_id'])
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    remote=PHYSICAL+report[5:];deadline=time.monotonic()+300;notice=0
    while True:
        try:
            first_raw=lan.web('/fs'+urllib.parse.quote(remote+'.first.start',safe='/'),4096,8)
            first=json.loads(first_raw)
            need(first['run_id']==run and first['candidate_SELF_sha256']==image['sha256'],'Exact native startup owner required')
            (a.out/'observed-first.private.json').write_bytes(first_raw)
            boot=state['current_boot'];stage_remote=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.stages'
            stages=lan.web('/fs'+urllib.parse.quote(stage_remote,safe='/'),8<<20,8)
            (a.out/'observed-stages.private.log').write_bytes(stages)
            last=stages.splitlines()[-1]
            need(not last.startswith(b'fatal_operation='),'Native owner is retained at a fatal boundary; audit this SAME process, never relaunch')
            CPU=last==b'paired_Down_native_CPU_returned_GPU_not_started_waiting_for_ordinary_close'
            from retained_component_completion import STAGE
            retained_GPU=last==STAGE and relink.get('retained_idle_device_until_ordinary_close') is True
            GPU=last==b'paired_Down_native_GPU_completed_owners_retired_waiting_for_ordinary_close' or retained_GPU
            if CPU or GPU:break
        except urllib.error.HTTPError as error:need(error.code==404,'Native observation state unknown')
        need(time.monotonic()<deadline,'Native completion unknown; retain the SAME owner and never resubmit')
        if time.monotonic()>=notice:
            print(json.dumps(dict(phase='observing-same-standalone-owner',mode=a.mode)),flush=True);notice=time.monotonic()+30
        time.sleep(3)
    terminal_remote=remote
    try:terminal_raw=lan.web('/fs'+urllib.parse.quote(terminal_remote,safe='/'),1<<20,8)
    except urllib.error.HTTPError as error:
        need(CPU and error.code==404,'Exact native terminal report required')
        terminal_remote=remote+'.failure';terminal_raw=lan.web('/fs'+urllib.parse.quote(terminal_remote,safe='/'),1<<20,8)
    terminal=json.loads(terminal_raw)
    need(terminal['run_id']==run and terminal['pid']==first['pid'] and terminal['candidate_SELF_sha256']==image['sha256'],
         'Exact native completion owner and artifact required')
    if CPU:need(terminal['CPU_only'] and terminal['all_CPU_IO_returned'] and terminal['GPU_calls']==terminal['model_loads']==0,'Positive returned CPU scope required')
    elif retained_GPU:
        from retained_component_completion import validate_terminal
        validate_terminal(terminal)
    else:need(terminal['completed'] and not terminal['unknown_completion'] and terminal['all_GPU_resources_positively_retired'] and
        terminal['device_ledger_live_bytes']==0 and terminal['all_model_source_device_owners_positively_retired'] and
        terminal['positive_reference_dispatches']<=24,'Positive GPU fences and exact owner retirement required')
    reports=[]
    for name,data,path in (('native-first.private.json',first_raw,remote+'.first.start'),('native-result.private.json',terminal_raw,terminal_remote),
                           ('native-stages.private.log',stages,stage_remote)):
        local=a.out/name;local.write_bytes(data);reports.append(dict(record(local),remote=path))
    IO=lan.web('/fs'+urllib.parse.quote(remote+'.IO',safe='/'),1<<20,8);(a.out/'native-IO.private.log').write_bytes(IO)
    close_proof=dict(pid=first['pid'],app_id=launched['app_id'],reports=reports)
    if CPU:close_proof.update(CPU_only=True,all_CPU_IO_returned=True)
    elif retained_GPU:close_proof.update(completed=True,retained_component_package=record(a.package))
    else:close_proof.update(completed=True,all_model_source_device_owners_positively_retired=True,device_ledger_live_bytes=0)
    state.update(unknown_completion=False,native_owners=1,observed_native_pid=first['pid']);state_path.write_text(json.dumps(state,indent=2)+'\n')
    close=build(a.workspace,a.mount_plan,new,new,[],'close',a.out/'ordinary-close',close=close_proof)
    print(json.dumps(dict(phase='positive-completion-ordinary-close',CPU_only=CPU,native_completed=terminal['completed'])),flush=True)
    closed=completed_operation(lan,close,a.out/'ordinary-close');need(closed['operation_calls']==1,'Exactly one ordinary close required')
    until=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
            owners=[row for row in json.loads(response.read())['processes'] if row['name']=='eboot.bin']
        if not owners:break
        need(time.monotonic()<until,'Ordinary exit unknown; never repeat close');time.sleep(.25)
    need(current_files(a.current)==old,'Selected production inputs changed')
    restore_pending=[dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')) for i,row in enumerate(old[:3])]
    restore=build(a.workspace,a.mount_plan,new,old,restore_pending,'publish',a.out/'restore')
    print(json.dumps(dict(phase='restore-exact-production')),flush=True)
    publish(lan,restore_pending,restore,a.out/'restore',direct_staging=direct)
    state.update(state='standalone_Q3_ordinary_exit_exact_current_restored',original_restored=True,native_running=False,
                 model_loaded=False,gateway_running=False,native_owners=0,unknown_completion=False)
    if retained_GPU:
        state['GPU_retirement_readmission_pending']=True
        state['retained_component_ordinary_exit']=dict(package=record(a.package),native=record(a.out/'native-result.private.json'),
            ordinary_exit_observed=True,all_case_resources_retired=True,device_retained_until_ordinary_exit=True,
            individual_old_BO_release_claimed=False,fresh_capacity_readmission_required=True)
    state.pop('temporary_installed_SELF',None);state['active_successful_native_case'].update(phase='standalone-completed-original-restored',native_pid=first['pid'])
    if readmission and terminal['completed']:
        capacity=terminal['Direct_readmission']
        need(capacity['completed'] and capacity['canaries_exact'] and capacity['Direct_total_bytes']==12280922112 and
             min(capacity['available_first'],capacity['available_last'])>=capacity['baseline_bytes']==12184453120,
             'Completed native capacity baseline and ordinary exit required before clearing the pending gate')
        state['GPU_retirement_readmission_pending']=False
        state['standalone_pre_device_exit_capacity_readmission']=dict(source=record(a.retained_component_exit_proof or a.P1_contract_close_proof or a.post_completion_close_proof or a.pre_device_exit_proof),native=record(a.out/'native-result.private.json'),
            individual_old_BO_release_claimed=False,ordinary_exit_observed=True)
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    passed=terminal['completed'] and (CPU if a.mode=='CPU' else GPU and terminal['all_outputs_passed'])
    save(a.out/'result.private.json',dict(completed=True,mode=a.mode,native_passed=passed,package=record(a.package),
        native=record(a.out/'native-result.private.json'),VM_before=record(vm_dir/'result.private.json'),
        ordinary_exit_observed=True,ordinary_close_calls=1,current_seven_restored_and_native_hashed=True,
        completed_idle_device_retained_until_ordinary_exit=bool(retained_GPU),
        fresh_capacity_readmission_required=bool(retained_GPU),
        model_loads=0,native_owners=0,unknown_completion=False,initializer_requests=0,production_adopted=False))
    print(json.dumps(dict(completed=True,mode=a.mode,native_passed=passed,exact_current_restored=True)),flush=True)


if __name__=='__main__':main()

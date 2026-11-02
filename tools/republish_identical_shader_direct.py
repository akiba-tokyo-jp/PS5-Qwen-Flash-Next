#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Republish the exact current SELF/app/shader bytes through bounded Direct IO."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import secrets

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from direct_self_staging import qualification,upload
from kernel_vm_preflight import query
from run_successful_model_case import metadata
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,current_files,execute,lan_module

ROOT=Path(__file__).resolve().parents[1]


def verify_prior(current,state,rows):
    prior=state['successful_route_20261102']['current_boot_shader_CPU'];need(record(prior['path'])['sha256']==prior['report_sha256'] and
        record(prior['path'])['bytes']==prior['report_bytes'],'Protected complete shader CPU report must remain exact')
    report=load(prior['path']);need(report['GPU_calls']==0 and not report['Vulkan_initialized'] and not report['model_loaded'] and
        not report['failed'] and not report['active_lease'] and not report['persistent_caches_enabled'] and report['all_original_SPIRV_bytes_preserved'] and
        report['CPU_verified_assets']==report['shader_count']==1527 and report['CPU_verified_lookups']==report['lookup_entries']==382 and
        report['external_file_SHA256_verified'] and report['external_file_bytes']==rows[-1]['bytes'],
        'All1527 original assets/382 lookups and the unchanged encoded storage must be qualified')
    entry=load(current/'provenance/selected-entry-build.private.json');profile=load(entry['application_policy']['path'])
    need(record(profile['source']['path'])==profile['source'],'Canonical selected entry source changed')
    selected=Path(profile['source']['path']).read_text(encoding='utf-8');public=(ROOT/'native/app/native_main.cpp').read_text(encoding='utf-8')
    functions={}
    for name in ('validate_prior_shader_CPU','read_prior_shader_CPU','admit_shader_storage_CPU'):
        actual=body(selected,name);need(actual==body(public,name),'Current original-byte admission helper changed')
        functions[name]=hashlib.sha256(actual.encode()).hexdigest()
    need('identity' not in body(selected,'validate_prior_shader_CPU'),'Prior content proof must not be treated as a current inode proof')
    return dict(original_CPU_report=prior,selected_entry_source=profile['source'],exact_admission_function_SHA256=functions,
        old_CPU_report_reused_for_unchanged_encoded_bytes_and_per_use_decoder_only=True,
        current_inode_is_still_freshly_checked_by_each_native_launch=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','direct-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args();state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'] and
        not state['current_boot_shader_CPU_proof_pending'],'Positive idle original deployment and complete CPU proof required')
    rows=current_files(a.current);storage=rows[-1];need(len(rows)==7 and storage['remote']==PHYSICAL+'/qwen-runtime/shader-storage-'+storage['sha256']+'.bin' and
        all(record(row['path'])=={key:row[key] for key in ('path','bytes','sha256')} for row in rows),'Only the exact selected seven files may be used')
    qualified=qualification(a.direct_proof);prior=verify_prior(a.current,state,rows)
    retained=load(a.current/'provenance/retained-relink-inputs.private.json');native=load(a.current/'provenance/native-link.receipt.private.json')
    package=load(a.current/'provenance/current-package.private.json');protected=rows+retained+native['formatter_stubs']+[package['formatter']]
    unique={Path(row['path']).resolve():record(row['path']) for row in protected};need(len(unique)==108 and all(
        all(unique[Path(row['path']).resolve()][key]==row[key] for key in ('bytes','sha256')) for row in protected),'All108 selected inputs must remain exact')
    a.out.mkdir(parents=True,exist_ok=False);run=secrets.token_hex(16);prefix='/data/ai/moss-qwen-case-'+run
    chosen=[rows[0],rows[1],storage];suffixes=('-candidate-SELF.bin','-identical-app.json','-shader-storage.bin')
    pending=[dict(row,target=row['remote'],remote=prefix+suffix) for row,suffix in zip(chosen,suffixes)]
    publication=build(a.workspace,a.mount_plan,rows,rows,pending,'publish',a.out/'publication')
    save(a.out/'intent.private.json',dict(current_files=rows,pending=pending,publication=record(a.out/'publication/plan.private.json'),
        protected=list(unique.values()),content_proof=prior,qualification=qualified,selected_data_mode_after_standard_publication='0644',
        all_current_file_payloads_identical=True,model_weights_driver_and_persistent_cache_policy_unchanged=True,
        title_launches=0,GPU_calls=0,initializer_requests=0,automatic_retries=0))
    if not a.execute:return
    lan=lan_module();before=a.out/'VM-before';before.mkdir();vm=query(lan.HOST,before)
    need(vm['boot_before']==vm['boot_after']==state['current_boot'],'Same boot required');save(before/'result.private.json',dict(completed=True,observations=vm,GPU_calls=0))
    state['identical_storage_publication_pending']=dict(intent=record(a.out/'intent.private.json'),run_id=run);state['unknown_completion']=True
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    metadata(lan,[pending[1]])
    upload({key:storage[key] for key in ('path','bytes','sha256')},pending[2]['remote'],a.out/'shader-transfer',lan,None,
        workspace=a.workspace,mount_plan=a.mount_plan,current_rows=rows,qualified=a.direct_proof,kind='selected_shader_storage')
    def publish(capture,remote):
        need(remote==pending[0]['remote'],'Only the exact pending selected SELF may finish this transaction')
        result=execute(lan,publication,a.out/'publication',60);need(result['completed'] and result['operation_calls']==3,'All three byte-identical publications must complete')
        return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,sha256=capture['sha256'],bytes=capture['bytes'])
    upload({key:rows[0][key] for key in ('path','bytes','sha256')},pending[0]['remote'],a.out/'SELF-transfer',lan,publish,
        workspace=a.workspace,mount_plan=a.mount_plan,current_rows=rows,qualified=a.direct_proof)
    inspect=build(a.workspace,a.mount_plan,rows,rows,[],'inspect-descriptors',a.out/'metadata',dependencies=[storage['remote'],ALIAS+storage['remote'][len(PHYSICAL):]])
    observed=execute(lan,inspect,a.out/'metadata',60);need(observed['completed'],'Fresh physical/alias storage metadata must complete')
    text=Path(observed['raw']['path']).read_text(encoding='ascii');facts=re.findall(r'DESCRIPTOR_METADATA index=(\d+) .*?fstat_rc=(\d+).*?mode=(\d+) uid=(\d+) gid=(\d+) bytes=(\d+)',text)
    need(len(facts)==2 and all(int(mode)&0o7777==0o644 and int(uid)<=1 and int(gid)==0 and int(size)==storage['bytes'] and int(rc)==0 for _,rc,mode,uid,gid,size in facts),
        'Standard data mode and complete physical/alias descriptor metadata required')
    need(all(record(path)==row for path,row in unique.items()),'A selected input changed');verify_prior(a.current,state,rows)
    after=a.out/'VM-after';after.mkdir();vm_after=query(lan.HOST,after);need(vm_after['boot_before']==vm_after['boot_after']==state['current_boot'],'Same boot after completed identical publication required')
    save(after/'result.private.json',dict(completed=True,observations=vm_after,GPU_calls=0))
    state['unknown_completion']=False;state.pop('identical_storage_publication_pending');state['last_identical_storage_publication']=dict(intent=record(a.out/'intent.private.json'),native=record(a.out/'publication/result.private.json'))
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=True,selected_SELF=rows[0],selected_shader_storage=storage,all_current_seven_payloads_identical_and_natively_hashed=True,
        old_and_new_shader_bytes_identical=True,prior_complete1527_asset382_lookup_CPU_content_proof_preserved=True,
        current_physical_and_alias_identity_checked=True,data_mode='0644',protected_current_inputs=108,all108_PC_whole_SHA_values_unchanged=True,
        native=record(a.out/'publication/result.private.json'),metadata=record(a.out/'metadata/result.private.json'),
        before_free_pages=min(vm['free_first'],vm['free_last']),after_free_pages=min(vm_after['free_first'],vm_after['free_last']),
        global_not_exclusive_attribution=True,model_speed_measured=False,title_launches=0,GPU_calls=0,initializer_requests=0,automatic_retries=0)
    save(a.out/'result.private.json',result);print(json.dumps({key:result[key] for key in ('completed','before_free_pages','after_free_pages','protected_current_inputs','GPU_calls','title_launches')}))


if __name__=='__main__':main()

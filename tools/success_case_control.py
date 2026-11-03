#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and run one ordinary publication/launch/CPU-only-close operation."""
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]
PHYSICAL='/data/ai/native-moss-image-sft/PPSA99190'
ALIAS='/system_ex/app/PPSA99190'


def lan_module():
    spec=importlib.util.spec_from_file_location('successful_case_lan','D:/PS5-AI/moss/tools/live_moss_root_v1.py')
    lan=importlib.util.module_from_spec(spec);spec.loader.exec_module(lan);return lan


def current_files(current):
    deployment=load(Path(current)/'deployment.private.json')
    return [dict(deployment['SELF'],remote=PHYSICAL+'/eboot.bin'),*deployment['application_files'],
            dict(deployment['shader_source_storage'],remote=PHYSICAL+'/qwen-runtime/'+Path(deployment['shader_source_storage']['path']).name)]


def digest_expression(row,path=None):
    return 'qwen_launch_digest_matches('+json.dumps(path or row['remote'])+','+str(row['bytes'])+'ULL,'+json.dumps(row['sha256'])+')'


def build(workspace,mount_plan,old_files,new_files,pending,operation,out,close=None,readmission_context=None,resident=None,dependencies=None,bundle_link=None,finalize_context=None,source_seal_context=None,activation_export_context=None,component_publish_context=None,completed_images_context=None,direct_stage_context=None,closed_log_export_context=None,direct_stage_header=None,concat_context=None,source_seal_window_proof=None):
    workspace=Path(workspace);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    base_plan=load(mount_plan);base=base_plan['controller'];need(record(base['path'])==base,'Successful controller input changed')
    text=Path(base['path']).read_text();prefix='/data/ai/moss-qwen-case-'+secrets.token_hex(16)
    text,n=re.subn(r'^#define LAUNCH_LOG_PREFIX .*$', '#define LAUNCH_LOG_PREFIX '+json.dumps(prefix),text,flags=re.M);need(n==1,'One scoped journal prefix required')
    marker='#include "launch_integrity_native.h"'
    need(text.count(marker)==1 and text.count('512*sizeof(struct kinfo_proc)')==1,'Exact complete process enumeration and integrity window required')
    text=text.replace(marker,'#define QWEN_LAUNCH_WINDOW 16384u\n#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 21u\n'+marker,1)
    text=text.replace('512*sizeof(struct kinfo_proc)','128*sizeof(struct kinfo_proc)',1)
    for name,rows,mounted in (('new_files_valid',new_files,False),('new_mounted_valid',new_files,True)):
        expression='&&'.join(digest_expression(r,ALIAS+r['remote'][len(PHYSICAL):] if mounted else None) for r in rows)
        text,n=re.subn(r'static int '+name+r'\(void\)\{[^\n]*\}',lambda m:'static int '+name+'(void){return '+expression+';}',text)
        need(n==1,'Exact successful file validator required')
    text=text[:text.index('static int claim(const char*mode)')]
    text+='''static int claim(const char*mode){
 char path[256];int n=snprintf(path,sizeof(path),LAUNCH_LOG_PREFIX "-%s.once",mode);
 if(n<0||(size_t)n>=sizeof(path))return 0;
 int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)return 0;
 const char value[]="single owned case operation; no retry\\n";
 int ok=write(fd,value,sizeof(value)-1)==sizeof(value)-1&&!fsync(fd);
 if(close(fd))ok=0;return ok;
}
'''
    text+='static int old_files_valid(void){return '+'&&'.join(digest_expression(r) for r in old_files)+';}\n'
    text+='static int pending_valid(void){return '+('&&'.join(digest_expression(r) for r in pending) or '0')+';}\n'
    numbers={'publish':1,'launch':2,'close':3,'observe':4,'readmission':5,'clock':6,'dependencies':7,'restore-bundle':8,'finalize-bundle':9,'seal-shared-Q4':10,'export-activation':11,'retire-activation':12,'publish-component':13,'retire-completed-images':14,'inspect-descriptors':15,'observe-direct':16,'receive-direct-stage':17,'export-closed-logs':18,'concatenate-model-parts':19,'inspect-staged-parts':20};need(operation in numbers,'One known operation required')
    if operation in ('receive-direct-stage','export-closed-logs'):
        text=text.replace('#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 21u','#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 37u',1)
    if operation=='concatenate-model-parts':
        text=text.replace('#define QWEN_LAUNCH_WINDOW 16384u','#define QWEN_LAUNCH_WINDOW 262144u',1)
        text=text.replace('#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 21u','#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 68u',1)
    if source_seal_window_proof:
        qualified=load(source_seal_window_proof)
        original=load(Path(source_seal_window_proof).parent/'intent.private.json')['native_plan']
        need(operation=='seal-shared-Q4' and qualified['completed'] and qualified['whole_SHA256_and_EOF'] and
             qualified['all_source_and_target_descriptors_positively_closed'] and qualified['helper_exited'] and
             record(original['path'])==original and load(original['path'])['whole_integrity_window_bytes']==262144 and
             load(original['path'])['CPU_metadata_margin_pages']==68,
             'A completed original262KiB Direct whole-file read and positive owner retirement are required')
        text=text.replace('#define QWEN_LAUNCH_WINDOW 16384u','#define QWEN_LAUNCH_WINDOW 262144u',1)
        text=text.replace('#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 21u','#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 97u',1)
    if operation not in ('restore-bundle','concatenate-model-parts') and not source_seal_window_proof:
        text=text.replace('#include "launch_integrity_native.h"','#define QWEN_LAUNCH_CPU_INDEPENDENT_THRESHOLDS 1\n#include "launch_integrity_native.h"',1)
    need(len(old_files)==len(new_files)==7 and all(r['remote'].startswith(PHYSICAL+'/') for r in old_files+new_files),
         'Exactly the seven current owned application files are required')
    if operation=='publish':need(len(pending)==3,'One SELF and two startup files are required')
    context='#define CASE_OPERATION '+str(numbers[operation])+'\n#define CASE_ARGUMENT '+json.dumps('--'+operation)+'\n#define CASE_LOG '+json.dumps(prefix+'.log')+'\n'
    context+='int sceSystemServiceKillApp(int,int,int,int);\n'
    if operation=='concatenate-model-parts':
        need(isinstance(concat_context,str) and concat_context,'Exact owned input parts and new output required')
        context+=concat_context+'\n#include "direct_model_concat.h"\n'
    if operation=='seal-shared-Q4':
        need(isinstance(source_seal_context,str) and source_seal_context,'Exact new-only source seal context required')
        context+=source_seal_context+'\n#include "shared_q4_publication.h"\n'
    if operation=='finalize-bundle':
        need(isinstance(finalize_context,str) and finalize_context,'Exact completed native CPU output context required')
        context+=finalize_context+'\n#include "required_bundle_finalize.h"\n'
    if operation in ('export-activation','retire-activation'):
        need(isinstance(activation_export_context,str) and activation_export_context,'Exact completed activation output context required')
        context+=activation_export_context+'\n#include "'+('activation_capture_retire.h' if operation=='retire-activation' else 'activation_capture_export.h')+'"\n'
    if operation=='publish-component':
        need(isinstance(component_publish_context,str) and component_publish_context,'One exact bounded component publication required')
        context+=component_publish_context+'\n#include "component_pack_publish.h"\n'
    if operation=='retire-completed-images':
        need(isinstance(completed_images_context,str) and completed_images_context,'Two exact independently copied images from one closed case required')
        context+=completed_images_context+'\n'
    if operation=='receive-direct-stage':
        need(isinstance(direct_stage_context,str) and direct_stage_context,'One exact bounded Direct staging protocol required')
        receiver_window=16384;receiver_extra_pages=0;receiver_socket=32768;receiver_socket_pages=0
        if direct_stage_header:
            from model_part_receiver_geometry import receiver_text
            original=(ROOT/'native/qwen_flash_next/direct_stage_receive.h').read_text()
            profiles=((16384,32768,False,False),(262144,32768,False,False),
                      (262144,262144,True,False),(262144,262144,True,True))
            matches=[row for row in profiles if Path(direct_stage_header).read_text()==receiver_text(original,*row)]
            need(len(matches)==1,'Only a completely source-bound finite model-part receiver geometry is admitted')
            receiver_window,receiver_socket,verified_socket,receiver_wait_all=matches[0]
            receiver_socket_pages=32 if verified_socket else 0
            receiver_extra_pages=2*(receiver_window-16384)//16384+receiver_socket_pages
            if receiver_extra_pages:
                text=text.replace('#define QWEN_LAUNCH_WINDOW 16384u','#define QWEN_LAUNCH_WINDOW '+str(receiver_window)+'u',1)
                text=text.replace('#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES 37u',
                    '#define QWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES '+str(37+receiver_extra_pages)+'u',1)
            context+=direct_stage_context+'\n#include '+json.dumps(Path(direct_stage_header).resolve().as_posix())+'\n'
        else:context+=direct_stage_context+'\n#include "direct_stage_receive.h"\n'
    if operation=='export-closed-logs':
        need(isinstance(closed_log_export_context,str) and closed_log_export_context,'Exact obsolete closed-log read-only scope required')
        context+=closed_log_export_context+'\n#include "closed_log_export.h"\n'
    if operation=='restore-bundle':
        need(bundle_link and bundle_link['CPU_only'] is True and bundle_link['source_writes']==0 and
             bundle_link['GPU_calls']==0 and bundle_link['Direct_CPU_bytes'] in (4<<20,8<<20),'Bounded successful CPU packer required')
        for row in bundle_link['objects']+bundle_link['libraries']:
            need(record(row['path'])==row,'CPU pack input changed')
        context+='int qwen_bundle_payload_main(int,char**);\n'
        marker='#include "launch_integrity_native.h"'
        need(text.count(marker)==1,'Exact bounded CPU helper metadata required')
        text=text.replace(marker,'#define QWEN_LAUNCH_CPU_HEADROOM_WAIT 1\n'+marker,1)
        # This still collects every process or refuses the scope; it never
        # truncates enumeration. The complete boot/service/native guards stay.
    if operation in ('dependencies','inspect-descriptors','inspect-staged-parts'):
        need(dependencies and len(dependencies)<=256 and len(set(dependencies))==len(dependencies) and
             (all(re.fullmatch(r'/data/ai/moss-qwen-case-[0-9a-f]{32}-candidate-SELF\.bin',p) for p in dependencies)
              if operation=='inspect-staged-parts' else
              all(p.startswith((PHYSICAL+'/',ALIAS+'/')) and '..' not in p.split('/') for p in dependencies)),
             'Exact distinct owned dependency paths required')
        context+='#define CASE_DEPENDENCY_COUNT '+str(len(dependencies))+'u\n'
        context+='static const char*case_dependencies[]={'+','.join(map(json.dumps,dependencies))+'};\n'
    if resident:
        need(operation=='launch' and re.fullmatch('[0-9a-f]{32}',resident['run_id']) and
             re.fullmatch('[0-9a-f]{32}',resident['nonce']),'Fresh same-launch integrity scope required')
        image=new_files[0];shader=new_files[-1];run=resident['run_id']
        values=dict(RESIDENT_RUN_ID=run,RESIDENT_RECEIPT_NONCE=resident['nonce'],
            RESIDENT_RECEIPT_PATH=PHYSICAL+'/qwen-runtime/resident-launch-'+run+'.json',
            RESIDENT_SELF_PATH=image['remote'],RESIDENT_SELF_SHA256=image['sha256'],
            RESIDENT_SHADER_SOURCE_PATH=shader['remote'],RESIDENT_SHADER_APP_PATH='/app0'+shader['remote'][len(PHYSICAL):],
            RESIDENT_SHADER_FILENAME=Path(shader['remote']).name,RESIDENT_SHADER_SHA256=shader['sha256'])
        header=''.join('#define '+k+' '+json.dumps(v)+'\n' for k,v in values.items())
        header+='#define RESIDENT_SELF_BYTES '+str(image['bytes'])+'ULL\n#define RESIDENT_SHADER_BYTES '+str(shader['bytes'])+'ULL\n'
        (out/'resident_launch_integrity_context.h').write_text(header,encoding='utf-8',newline='\n')
        text=text.replace('qwen_launch_digest_matches(','resident_launch_digest_matches(')
        marker='#include "launch_integrity_native.h"'
        need(text.count(marker)==1,'Exact native launch integrity include required')
        text=text.replace(marker,marker+'\n#ifndef NEW_STAGE\n#define NEW_STAGE STAGE\n#endif\n#include "resident_launch_integrity_writer.h"',1)
    if operation=='readmission':
        need(isinstance(readmission_context,str) and readmission_context,'Exact model readmission inputs required')
        context+=readmission_context+'\n#include "model_readmission.h"\n'
    if operation=='publish':
        context+='#define CASE_PUBLICATION_COUNT '+str(len(pending))+'u\n'
        context+='static const char*case_pending[]={'+','.join(json.dumps(r['remote']) for r in pending)+'};\n'
        context+='static const char*case_targets[]={'+','.join(json.dumps(r['target']) for r in pending)+'};\n'
    if operation=='close':
        retained_component=False
        if close and close.get('retained_component_package'):
            from retained_component_completion import validate_close
            retained_component=validate_close(close,new_files)
        CPU_closed=close and close.get('CPU_only') is True and close.get('all_CPU_IO_returned') is True
        model_closed=close and close.get('completed') is True and close.get('all_model_source_device_owners_positively_retired') is True and close.get('device_ledger_live_bytes')==0
        pre_GPU=close and close.get('known_returned_pre_GPU_exception') is True and close.get('native_resources_started') is False and close.get('model_loaded') is False and close.get('CPU_worker_completion_unknown') is False and close.get('all_probe_ranges_unmapped') is True
        unloaded=close and close.get('known_IQ2_CPU_teardown_failure') is True and close.get('model_loaded') is False and close.get('GPU_graphs_positively_completed')==72 and close.get('all_GGML_backends_retired') is True and close.get('final_driver_producer_completed') is True and close.get('all_source_IO_completed') is True and close.get('CPU_worker_completion_unknown') is False and close.get('source_audit_SHA256')=='002b695b4896bfea2d540055656adf5aacd56832b5964cd2ed129b8d04de2150'
        idle_MTP=close and close.get('known_MTP_returned_prefill_scope_failure') is True and close.get('model_loaded') is True and close.get('all_GPU_epochs_positively_completed')==5 and close.get('target_prefill_GPU_calls')==0 and close.get('auxiliary_contexts_created')==0 and close.get('all_source_IO_completed') is True and close.get('CPU_worker_completion_unknown') is False and close.get('source_audit_SHA256')=='16e60fcc805ace70534fe4b2efeaa17b924d0535034d639123521fc8c9a03af9'
        idle_paired=close and close.get('known_paired_Down_post_completion_CPU_failure') is True and close.get('model_loaded') is False and close.get('positive_reference_dispatches')==24 and close.get('all_case_resources_retired') is True and close.get('final_driver_producer_completed') is True and close.get('all_source_IO_completed') is True and close.get('CPU_worker_completion_unknown') is False and close.get('source_audit_SHA256')=='2d356cca75a0fb594e0c94fb8bdca17fd82d114b0cce7242ed300626942f1b8b' and close.get('support_SHA256')=='b193d0659c68bb569bbba22cf59b88d2691bcd49ab1d673f1e9a64b5328d6f7e'
        idle_P1=close and close.get('known_P1_pre_request_contract_failure') is True and close.get('model_loaded') is True and close.get('all_GPU_epochs_positively_completed')==5 and close.get('target_request_operations')==0 and close.get('all_source_IO_completed') is True and close.get('CPU_worker_completion_unknown') is False and close.get('source_audit_SHA256')=='08c68e6997fc0ae231b79649496ae89970ccfa54fb7e9417dbe22f90edcfb63d' and close.get('SELF_SHA256')=='dcad1baacefbe1a4f39402b1a24cf95335770a85592da83df28ca8074ad60f1e'
        checkpoint_P1=close and close.get('known_P1_checkpoint_preallocation_refusal') is True and close.get('model_loaded') is True and close.get('completed_requests')==2 and close.get('completed_GPU_epochs')==15 and close.get('last_active_epoch_positive_checkpoint') is True and close.get('post_checkpoint_GPU_submissions')==0 and close.get('all_source_IO_completed') is True and close.get('CPU_worker_completion_unknown') is False and close.get('source_audit_SHA256')=='411515f3af833fde580b3aa8a418d47efbcc2634f76358474582bcb458df3f78' and close.get('SELF_SHA256')=='7c2433678ba088085d9c627ab2112cbebc928a9a54ca1da1bac38d7081c4e26d'
        idle_G1=close and close.get('known_G1_IGPU_graph_contract_failure') is True and close.get('model_loaded') is True and close.get('completed_GPU_epochs')==2 and close.get('last_active_epoch_CPU_graph_only') is True and close.get('target_request_operations')==0 and close.get('all_source_IO_completed') is True and close.get('CPU_worker_completion_unknown') is False and close.get('source_audit_SHA256')=='57a0dc13258bc4550e8f8f1d276fe02765e83c6be02ca2c05c916b8e46c20301' and close.get('SELF_SHA256')=='fc74cb5865e9caf7d061f0f5f5190124e65d541a2f32ac216566c3c6cdb742fc'
        idle_S1=close and close.get('known_S1_post_request_backing_certificate_failure') is True and close.get('model_loaded') is True and close.get('completed_GPU_epochs')==49 and close.get('completed_F32_rows')==23 and close.get('completed_token_records')==22 and close.get('auxiliary_positively_retired') is True and close.get('all_source_IO_completed') is True and close.get('CPU_worker_completion_unknown') is False and close.get('source_audit_SHA256')=='ad4bedee1fa68fde8c5ac932813aad403401bbd15508becde377b8e649624112' and close.get('SELF_SHA256')=='e5284dfcaaca41562c2bf9e9003240d3a0fc566bb4cf4b80c516521758147163'
        need(CPU_closed or model_closed or retained_component or pre_GPU or unloaded or idle_MTP or idle_paired or idle_P1 or checkpoint_P1 or idle_G1 or idle_S1,'Positive returned work and exact scoped owner completion required')
        if idle_MTP:context+='#define CASE_RETAINED_IDLE_MTP_CLOSE 1\n'
        need(close['pid']>0 and close['app_id']>0,'Exact native PID and application ID required')
        need(len(close.get('reports',[]))>=2,'Two immutable completed native reports required')
        for needle in ('    for(size_t i=0;i<n;i+=sizeof(struct kinfo_proc)){',
                       'if(!strcmp(p.ki_comm,"eboot.bin"))return 0;',
                       '    for(unsigned j=0;j<8;++j)if(seen[j]!=1)return 0;'):
            need(text.count(needle)==1,'Exact native owner admission boundary required')
        text=text.replace('    for(size_t i=0;i<n;i+=sizeof(struct kinfo_proc)){','    unsigned native_seen=0;\n    for(size_t i=0;i<n;i+=sizeof(struct kinfo_proc)){',1)
        text=text.replace('if(!strcmp(p.ki_comm,"eboot.bin"))return 0;',
                          'if(!strcmp(p.ki_comm,"eboot.bin")){if(p.ki_pid!='+str(close['pid'])+')return 0;++native_seen;}')
        text=text.replace('    for(unsigned j=0;j<8;++j)if(seen[j]!=1)return 0;',
                          '    if(native_seen!=1)return 0;\n    for(unsigned j=0;j<8;++j)if(seen[j]!=1)return 0;',1)
        text=text.replace('no_native_owner=1','exact_completed_CPU_native_owner=1')
        need(all(r['remote'].startswith(PHYSICAL+'/qwen-runtime/') for r in close['reports']),
             'Only exact owned CPU completion metadata is a close proof')
        context+='#define CASE_CLOSE_APP_ID '+str(close['app_id'])+'\n'
        context+='static int case_CPU_close_proof(void){return '+ '&&'.join(digest_expression(r) for r in close['reports'])+';}\n'
    controller=out/'controller.c';controller.write_text(text,encoding='utf-8',newline='\n')
    (out/'case_context.h').write_text(context,encoding='utf-8',newline='\n')
    project_source=ROOT/'native/qwen_flash_next/successful_case_control.c';source=out/'case_main.private.c'
    source.write_bytes(project_source.read_bytes());obj=out/'control.o';artifact=out/'control.elf'
    tools=workspace/'toolchain/fast/llvm-mingw-20261006-ucrt-x86_64/bin';sdk=workspace/'toolchain/ps5-payload-sdk'
    old=Path('D:/PS5-AI/archives/c-drive-cleanup-20261019/build/gpu_probe');crt=old/'credential-preserving-crt'
    common=[str(tools/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-isystem',str(sdk/'target/include'),
            '-I',str(old/'sd-pid807-signal-state/overlay'),'-I',str(ROOT/'native/qwen_flash_next'),'-I',str(out),
            '-D_BSD_SOURCE','-std=gnu11','-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC','-O2',
            '-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Wno-unused-function']
    jobs=[common+['-c',str(source),'-o',str(obj)],common+['-c',str(workspace/'native/model_hash/sha256.c'),'-o',str(out/'sha256.o')],
          [str(tools/'ld.lld.exe'),'-m','elf_x86_64','-pie','-T',str(sdk/'ldscripts/elf_x86_64.x'),'--eh-frame-hdr',
           '--gc-sections','-z','max-page-size=0x4000','--hash-style=gnu','-L',str(sdk/'target/lib'),'-o',str(artifact),
           str(obj),str(out/'sha256.o'),str(crt/'crt1-credential-preserving.o'),str(crt/'patch-syscall-only.o'),
           '-lc','-lkernel_web','-lSceLibcInternal','--as-needed','-lSceSystemService','-lSceAppInstUtil','-lSceUserService']]
    if bundle_link:
        need(operation=='restore-bundle','CPU pack code must not enter another controller')
        at=jobs[-1].index('-lc')
        jobs[-1][at:at]=[r['path'] for r in bundle_link['objects']]+['--start-group']+[r['path'] for r in bundle_link['libraries']]+['--end-group']
    for i,job in enumerate(jobs):
        result=subprocess.run(job,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(out),TEMP=str(out)))
        (out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    imports=subprocess.check_output([str(tools/'llvm-nm.exe'),'--undefined-only',str(artifact)],text=True)
    forbidden=r'\b(?:kill|ptrace|nmount|unmount|kernel_set\w*|sceAgc\w*)\b'
    need(not re.search(forbidden,imports),'Ordinary case controller contains a forbidden import')
    need(operation=='launch' or 'sceSystemServiceLaunchApp' not in imports,'Launch API in a non-launch helper')
    need(operation=='close' or 'sceSystemServiceKillApp' not in imports,'Close API in a non-close helper')
    plan=dict(completed=True,operation=operation,artifact=record(artifact),controller=record(controller),
              context=record(out/'case_context.h'),source=record(source),project_source=record(project_source),imports=imports,commands=jobs,
              original_mount_plan=record(mount_plan),old_files=old_files,new_files=new_files,pending=pending,
              close_admission=close,bundle_link=bundle_link,remote=prefix+'.elf',log=prefix+'.log',claim=prefix+'-'+operation+'.once',
              initializer_requests=0,mount_calls=0,GPU_calls=0,automatic_retries=0,
              maximum_complete_process_rows=128,whole_integrity_window_bytes=16384,
              CPU_metadata_margin_pages=37 if operation in ('receive-direct-stage','export-closed-logs') else 21,OS_minimum_and_reserved_read_only=True)
    plan['CPU_control_independent_thresholds']=operation not in ('restore-bundle','concatenate-model-parts')
    if source_seal_window_proof:
        plan.update(whole_integrity_window_bytes=262144,CPU_metadata_margin_pages=97,
            CPU_control_independent_thresholds=False,minimum_live_free_pages=1201,
            qualified_large_window=record(source_seal_window_proof),
            application_source_seal_only=True,full_physical_alias_SHA256_EOF_unchanged=True)
    if operation=='concatenate-model-parts':
        plan.update(whole_integrity_window_bytes=262144,CPU_metadata_margin_pages=68,
            additional_fixed_CPU_buffer_pages=47,minimum_live_free_pages=1201,
            concat_source=record(ROOT/'native/qwen_flash_next/direct_model_concat.h'),
            stream_source=record(ROOT/'native/qwen_flash_next/bounded_part_concat.h'))
    if operation=='receive-direct-stage':
        plan['receiver_source']=record(direct_stage_header or ROOT/'native/qwen_flash_next/direct_stage_receive.h')
        plan['isolated_large_model_part_receiver']=bool(direct_stage_header)
        plan.update(receive_window_bytes=receiver_window,whole_integrity_window_bytes=receiver_window,
                    CPU_metadata_margin_pages=37+receiver_extra_pages,additional_fixed_CPU_buffer_pages=receiver_extra_pages-receiver_socket_pages,
                    receive_socket_buffer_bytes=receiver_socket,additional_socket_kernel_allowance_pages=receiver_socket_pages)
        plan['receive_wait_all']=receiver_wait_all if direct_stage_header else False
    if operation=='export-closed-logs':plan['exporter_source']=record(ROOT/'native/qwen_flash_next/closed_log_export.h')
    save(out/'plan.private.json',plan);return plan


def execute(lan,plan,out,observation_seconds=45):
    out=Path(out)
    need(type(observation_seconds) is int and 1<=observation_seconds<=60,'The existing transport permits at most60 observation seconds')
    raw=lan.execute_once(Path(plan['artifact']['path']),plan['artifact']['sha256'],'--'+plan['operation'],
                         plan['remote'],plan['log'],out/'execution',observation_seconds)
    return complete(lan,plan,out,raw)


def complete(lan,plan,out,raw,raw_path=None):
    """Collect an already submitted helper; never submit or replay an operation."""
    out=Path(out)
    terminal=re.search(rb'\nEND success=(\d+) operation_calls=(\d+) app_id=(-?\d+) log_healthy=(\d+) GPU_calls=0 initializer_requests=0 mount_calls=0\n$',raw)
    need(terminal is not None,'Case helper completion unknown; never resubmit')
    pid=int(re.search(rb'BEGIN pid=(\d+)',raw)[1]);deadline=time.monotonic()+10
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(int(r['pid'])==pid for r in rows):break
        need(time.monotonic()<deadline,'Case helper retirement unknown; retain helper files');time.sleep(.2)
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw FTP mode required')
        for path in (plan['remote'],plan['log'],plan['claim']):
            try:reply=ftp.sendcmd('DELE '+path)
            except lan.ftplib.error_perm as error:need(str(error).startswith('550') and path==plan['claim'],'Owned helper cleanup failed');continue
            need(reply.startswith(('226 ','250 ')),'Owned helper removal failed')
    for path in (plan['remote'],plan['log'],plan['claim']):lan.absent(path)
    result=dict(completed=terminal[1]==b'1' and terminal[4]==b'1',operation=plan['operation'],
                operation_calls=int(terminal[2]),app_id=int(terminal[3]),helper_exited=True,helper_files_removed=True,
                initializer_requests=0,mount_calls=0,GPU_calls=0,raw=record(raw_path or out/'execution/console.private.log'))
    save(out/'result.private.json',result)
    need(result['completed'],'Case helper refused or failed; do not replay unchanged')
    return result

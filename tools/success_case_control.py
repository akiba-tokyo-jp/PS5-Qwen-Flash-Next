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


def build(workspace,mount_plan,old_files,new_files,pending,operation,out,close=None,readmission_context=None,resident=None,dependencies=None,bundle_link=None,finalize_context=None,source_seal_context=None,activation_export_context=None):
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
    numbers={'publish':1,'launch':2,'close':3,'observe':4,'readmission':5,'clock':6,'dependencies':7,'restore-bundle':8,'finalize-bundle':9,'seal-shared-Q4':10,'export-activation':11,'retire-activation':12};need(operation in numbers,'One known operation required')
    if operation!='restore-bundle':
        text=text.replace('#include "launch_integrity_native.h"','#define QWEN_LAUNCH_CPU_INDEPENDENT_THRESHOLDS 1\n#include "launch_integrity_native.h"',1)
    need(len(old_files)==len(new_files)==7 and all(r['remote'].startswith(PHYSICAL+'/') for r in old_files+new_files),
         'Exactly the seven current owned application files are required')
    if operation=='publish':need(len(pending)==3,'One SELF and two startup files are required')
    context='#define CASE_OPERATION '+str(numbers[operation])+'\n#define CASE_ARGUMENT '+json.dumps('--'+operation)+'\n#define CASE_LOG '+json.dumps(prefix+'.log')+'\n'
    context+='int sceSystemServiceKillApp(int,int,int,int);\n'
    if operation=='seal-shared-Q4':
        need(isinstance(source_seal_context,str) and source_seal_context,'Exact new-only source seal context required')
        context+=source_seal_context+'\n#include "shared_q4_publication.h"\n'
    if operation=='finalize-bundle':
        need(isinstance(finalize_context,str) and finalize_context,'Exact completed native CPU output context required')
        context+=finalize_context+'\n#include "required_bundle_finalize.h"\n'
    if operation in ('export-activation','retire-activation'):
        need(isinstance(activation_export_context,str) and activation_export_context,'Exact completed activation output context required')
        context+=activation_export_context+'\n#include "'+('activation_capture_retire.h' if operation=='retire-activation' else 'activation_capture_export.h')+'"\n'
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
    if operation=='dependencies':
        need(dependencies and len(dependencies)<=256 and len(set(dependencies))==len(dependencies) and
             all(p.startswith((PHYSICAL+'/',ALIAS+'/')) and '..' not in p.split('/') for p in dependencies),'Exact distinct owned dependency paths required')
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
        CPU_closed=close and close.get('CPU_only') is True and close.get('all_CPU_IO_returned') is True
        model_closed=close and close.get('completed') is True and close.get('all_model_source_device_owners_positively_retired') is True and close.get('device_ledger_live_bytes')==0
        pre_GPU=close and close.get('known_returned_pre_GPU_exception') is True and close.get('native_resources_started') is False and close.get('model_loaded') is False and close.get('CPU_worker_completion_unknown') is False and close.get('all_probe_ranges_unmapped') is True
        need(CPU_closed or model_closed or pre_GPU,'Positive CPU-only, returned pre-GPU exception, or retired model completion required')
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
    source=ROOT/'native/qwen_flash_next/successful_case_control.c';obj=out/'control.o';artifact=out/'control.elf'
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
              context=record(out/'case_context.h'),source=record(source),imports=imports,commands=jobs,
              original_mount_plan=record(mount_plan),old_files=old_files,new_files=new_files,pending=pending,
              close_admission=close,bundle_link=bundle_link,remote=prefix+'.elf',log=prefix+'.log',claim=prefix+'-'+operation+'.once',
              initializer_requests=0,mount_calls=0,GPU_calls=0,automatic_retries=0,
              maximum_complete_process_rows=128,whole_integrity_window_bytes=16384,
              CPU_metadata_margin_pages=21,OS_minimum_and_reserved_read_only=True)
    plan['CPU_control_independent_thresholds']=operation!='restore-bundle'
    save(out/'plan.private.json',plan);return plan


def execute(lan,plan,out):
    out=Path(out)
    raw=lan.execute_once(Path(plan['artifact']['path']),plan['artifact']['sha256'],'--'+plan['operation'],
                         plan['remote'],plan['log'],out/'execution',45)
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

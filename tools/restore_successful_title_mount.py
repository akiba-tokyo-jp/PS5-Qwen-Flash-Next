#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rebind the existing successful title-mount source to current immutable files."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import urllib.error

from build_performance_quantizer import record
from start_success_route import NAMES,load,need,save

ROOT=Path(__file__).resolve().parents[1]
GUARDS=r'''
#include "launch_integrity_native.h"
#define NEW_STAGE STAGE
#define LAUNCH_LOG_PREFIX @PREFIX@
static int live_context(void){
    struct timeval boot={0};size_t n=sizeof(boot);
    if(sysctlbyname("kern.boottime",&boot,&n,NULL,0)||n!=sizeof(boot)||
       boot.tv_sec!=@BOOT_SEC@LL||boot.tv_usec!=@BOOT_USEC@LL||!kstuff_check_query())return 0;
    static struct {uint64_t pre;unsigned char data[512*sizeof(struct kinfo_proc)];uint64_t post;} rows;
    rows.pre=rows.post=UINT64_C(0x2a39672a3967);n=sizeof(rows.data);
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PROC,0};
    if(sysctl(mib,4,rows.data,&n,NULL,0)||n>sizeof(rows.data)||n%sizeof(struct kinfo_proc)||
       rows.pre!=UINT64_C(0x2a39672a3967)||rows.post!=rows.pre)return 0;
    const char*names[]={@SERVICE_NAMES@,"payload"};
    const int pids[]={@SERVICE_PIDS@,@RUNTIME_PID@};unsigned seen[8]={0};
    for(size_t i=0;i<n;i+=sizeof(struct kinfo_proc)){
        struct kinfo_proc p;memcpy(&p,rows.data+i,sizeof(p));
        if(p.ki_structsize!=sizeof(p)||!memchr(p.ki_comm,0,sizeof(p.ki_comm)))return 0;
        if(!strcmp(p.ki_comm,"eboot.bin"))return 0;
        if(!strcmp(p.ki_comm,"payload")&&p.ki_pid==getpid())continue;
        for(unsigned j=0;j<8;++j)if(!strcmp(p.ki_comm,names[j])){
            if(p.ki_pid!=pids[j]||p.ki_uid||p.ki_start.tv_sec<boot.tv_sec||p.ki_tracer||(p.ki_flag&P_TRACED))return 0;
            ++seen[j];
        }
    }
    for(unsigned j=0;j<8;++j)if(seen[j]!=1)return 0;
    return report("CURRENT_CONTEXT exact_boot_services_runtime=1 no_native_owner=1");
}
static int no_native_owner(void){return idle();}
static int registered_metadata_valid(void){return @METADATA_CHECKS@;}
static int new_files_valid(void){return @PHYSICAL_CHECKS@;}
static int new_mounted_valid(void){return @MOUNTED_CHECKS@;}
static int claim(const char*mode){
    if(strcmp(mode,"restore-mount"))return 0;
    int fd=open(LAUNCH_LOG_PREFIX "-mount.once",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(fd<0)return 0;const char value[]="one existing-title mount; no retry\n";
    int ok=write(fd,value,sizeof(value)-1)==sizeof(value)-1&&!fsync(fd);
    if(close(fd))ok=0;return ok;
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','current','runtime','admission','metadata','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    runtime=load(args.runtime);observation=load(args.admission);metadata=load(args.metadata)
    need(runtime['completed'] and runtime['positive_kernel_entry_return'] and runtime['runtime_requests']==1,
         'Positive successful runtime initialization required')
    need(runtime['boot']==observation['boot'],'Same admitted boot required')
    deployment=load(args.current/'deployment.private.json')
    physical='/data/ai/native-moss-image-sft/PPSA99190';alias='/system_ex/app/PPSA99190'
    files=[dict(deployment['SELF'],remote=physical+'/eboot.bin'),*deployment['application_files'],
           dict(deployment['shader_source_storage'],remote=physical+'/qwen-runtime/'+Path(deployment['shader_source_storage']['path']).name)]
    for row in files:need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Current PC artifact differs')
    parameters=[r for r in metadata['files'] if r['remote'].endswith('/param.json')]
    need(len(parameters)==2 and parameters[0]['sha256']==parameters[1]['sha256'],'Exact registered and source metadata required')
    for row in parameters:
        need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Metadata snapshot differs')
        need(load(row['path'])['titleId']=='PPSA99190','Exact existing title required')
    prefix='/data/ai/moss-qwen-success-mount-'+secrets.token_hex(16)
    services={}
    for name in NAMES:
        rows=[r for r in observation['processes'] if r['name']==name];need(len(rows)==1,'One protected service required')
        services[name]=int(rows[0]['pid'])
    def check(path,size,digest):return 'qwen_launch_digest_matches('+json.dumps(path)+','+str(size)+'ULL,'+json.dumps(digest)+')'
    substitutions=dict(PREFIX=json.dumps(prefix),BOOT_SEC=str(runtime['boot'][0]),BOOT_USEC=str(runtime['boot'][1]),
                       SERVICE_NAMES=','.join(json.dumps(n) for n in NAMES),
                       SERVICE_PIDS=','.join(str(services[n]) for n in NAMES),RUNTIME_PID=str(runtime['runtime_pid']),
                       METADATA_CHECKS='&&'.join(check(r['remote'],r['bytes'],r['sha256']) for r in parameters),
                       PHYSICAL_CHECKS='&&'.join(check(r['remote'],r['bytes'],r['sha256']) for r in files),
                       MOUNTED_CHECKS='&&'.join(check(alias+r['remote'][len(physical):],r['bytes'],r['sha256']) for r in files))
    base=args.workspace/'native/native_entry_controller/controller.c'
    text=base.read_text();text=text.replace('"../../native/model_hash/sha256.h"',json.dumps((args.workspace/'native/model_hash/sha256.h').as_posix()))
    text=text.replace('"../../vendor/ShadowMountPlus/include/sm_kstuff.h"',json.dumps((args.workspace/'vendor/ShadowMountPlus/include/sm_kstuff.h').as_posix()))
    text=text.replace('#define TITLE "PPSA99188"','#define TITLE "PPSA99190"')
    text=text.replace('#define STAGE "/data/ai/native-entry-gate/" TITLE','#define STAGE "/data/ai/native-moss-image-sft/" TITLE')
    text='#include <sys/param.h>\n#include <sys/proc.h>\n#include <sys/user.h>\n#include <sys/sysctl.h>\n#include <sys/time.h>\n#include <sys/mount.h>\n#include <dirent.h>\n#define main prior_registered_launcher_main\n'+text+'\n#undef main\n'
    guards=GUARDS
    for name,value in substitutions.items():guards=guards.replace('@'+name+'@',value)
    need(not re.search(r'@[A-Z_]+@',guards),'All current context placeholders must be bound')
    (args.out/'controller.c').write_text(text+guards,encoding='utf-8',newline='\n')
    template=ROOT/'native/qwen_flash_next/restore_title_mount.c';body=template.read_text()
    body=body.replace('    if(journal<0)return 1;','    if(journal<0)return 1;\n    if(!report("HELPER_PID pid=%d",getpid()))return 1;',1)
    generated=args.out/'mount.c';generated.write_text(body,encoding='utf-8',newline='\n')
    tools=args.workspace/'toolchain/fast/llvm-mingw-20261006-ucrt-x86_64/bin'
    sdk=args.workspace/'toolchain/ps5-payload-sdk'
    old=Path('D:/PS5-AI/archives/c-drive-cleanup-20261019/build/gpu_probe')
    crt=old/'credential-preserving-crt';obj=args.out/'mount.o';artifact=args.out/'mount.elf'
    jobs=[[str(tools/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-isystem',str(sdk/'target/include'),
           '-I',str(old/'sd-pid807-signal-state/overlay'),'-I',str(ROOT/'native/qwen_flash_next'),'-I',str(args.out),
           '-D_BSD_SOURCE','-std=gnu11','-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC','-O2',
           '-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Wno-unused-function','-c',str(generated),'-o',str(obj)],
          [str(tools/'ld.lld.exe'),'-m','elf_x86_64','-pie','-T',str(sdk/'ldscripts/elf_x86_64.x'),'--eh-frame-hdr',
           '--gc-sections','-z','max-page-size=0x4000','--hash-style=gnu','-L',str(sdk/'target/lib'),'-o',str(artifact),
           str(obj),str(args.out/'sha256.o'),str(crt/'crt1-credential-preserving.o'),str(crt/'patch-syscall-only.o'),'-lc','-lkernel_web',
           '-lSceLibcInternal','--as-needed','-lSceSystemService','-lSceAppInstUtil']]
    hash_source=args.workspace/'native/model_hash/sha256.c'
    hash_command=jobs[0].copy();hash_command[hash_command.index('-c')+1]=str(hash_source)
    hash_command[hash_command.index('-o')+1]=str(args.out/'sha256.o');jobs.insert(1,hash_command)
    for index,job in enumerate(jobs):
        result=subprocess.run(job,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
        (args.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    imports=subprocess.check_output([str(tools/'llvm-nm.exe'),'--undefined-only',str(artifact)],text=True)
    need(not re.search(r'\b(?:kill|ptrace|unmount|kernel_set\w*|sceSystemServiceLaunchApp|sceAgc\w*)\b',imports),'Mount-only artifact has a forbidden import')
    plan=dict(completed=True,artifact=record(artifact),source=record(generated),controller=record(args.out/'controller.c'),
              original_controller=record(base),successful_mount_template=record(template),SHA256_source=record(hash_source),commands=jobs,imports=imports,
              runtime=record(args.runtime),metadata=record(args.metadata),maximum_mount_calls=1,maximum_runtime_requests=0,
              title_launches=0,GPU_calls=0,remote=prefix+'.elf',log=prefix+'-mount.log',claim=prefix+'-mount.once')
    save(args.out/'plan.private.json',plan)
    if not args.execute:
        print(json.dumps(dict(mount_only_built=True,PS5_operations=0)));return
    spec=importlib.util.spec_from_file_location('success_mount_lan','D:/PS5-AI/moss/tools/live_moss_root_v1.py')
    lan=importlib.util.module_from_spec(spec);spec.loader.exec_module(lan)
    raw=lan.execute_once(artifact,plan['artifact']['sha256'],'--restore-mount',plan['remote'],plan['log'],args.out/'execution',45)
    terminal=re.search(rb'\nEND success=(\d+) mount_calls=(\d+) log_healthy=(\d+) GPU_calls=0 title_launches=0 unmount_calls=0 system_volume_remounts=0 registration_calls=0\n$',raw)
    need(terminal is not None,'Mount completion unknown; retain files and never resubmit')
    pid=int(re.search(rb'HELPER_PID pid=(\d+)',raw)[1])
    deadline=time.monotonic()+10
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(int(r['pid'])==pid for r in rows):break
        need(time.monotonic()<deadline,'Mount helper has not retired; no further operation');time.sleep(.2)
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw FTP mode required')
        for path in (plan['remote'],plan['log'],plan['claim']):
            try:reply=ftp.sendcmd('DELE '+path)
            except lan.ftplib.error_perm as error:need(str(error).startswith('550') and path==plan['claim'],'Owned mount helper cleanup failed');continue
            need(reply.startswith(('226 ','250 ')),'Owned helper removal failed')
    for path in (plan['remote'],plan['log'],plan['claim']):lan.absent(path)
    success=terminal[1]==b'1' and terminal[2]==b'1' and terminal[3]==b'1'
    result=dict(completed=success,mount_calls=int(terminal[2]),helper_exited=True,helper_files_removed=True,
                runtime_requests=0,title_launches=0,GPU_calls=0,unmount_calls=0,system_volume_remounts=0,
                registration_changes=0,source_and_alias_whole_hashes_verified=7 if success else 0,
                raw=record(args.out/'execution/console.private.log'))
    save(args.out/'result.private.json',result);print(json.dumps({k:v for k,v in result.items() if k!='raw'}))
    need(success,'Mount scope refused or failed; do not replay unchanged')


if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reduce packet-sized receive calls without weakening the bounded stream contract."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from model_part_receiver_geometry import receiver_text
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','socket-profile','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.socket_profile)
    need(old['completed'] and old['receive_window_bytes']==old['receive_socket_buffer_bytes']==262144 and
         old['socket_configuration_controls']['socket_configuration_cases']==10 and
         old['CPU_metadata_margin_pages']==99 and old['reused_changed_data_transport_cases']==14 and
         old['reused_changed_integrity_controls']==25 and record(old['receiver']['path'])==old['receiver'] and
         record(old['original_receiver']['path'])==old['original_receiver'],
         'Reuse the exact completed larger socket, transport and integrity qualifications')
    a.out.mkdir(parents=True,exist_ok=False)
    text=receiver_text(Path(old['original_receiver']['path']).read_text(),262144,262144,True,True)
    original=Path(old['receiver']['path']).read_text()
    expected=original.replace('recv(fd,(unsigned char*)value+offset,bytes-offset,0)',
        'recv(fd,(unsigned char*)value+offset,bytes-offset,MSG_WAITALL)',1).replace(
        'if(got<=0)return 0;offset+=(size_t)got;','if(got<=0||(size_t)got>bytes-offset)return 0;offset+=(size_t)got;',1)
    expected=expected.replace('#include <sys/time.h>\n','#include <sys/time.h>\n_Static_assert(MSG_WAITALL==0x40,"The qualified PS5 wait-all socket ABI is required");\n',1)
    need(text==expected,'Only wait-all and the stronger returned-length check may change')
    receiver=a.out/'wait_all_model_part_receive.h';receiver.write_text(text,newline='\n')
    body=text[text.index('static int direct_receive_exact('):text.index('static int case_receive_direct_stage(')]
    source=a.out/'wait-all-boundaries.c'
    source.write_text('''// SPDX-License-Identifier: MIT
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef long long ssize_t;
#define MSG_WAITALL 0x40
#define CHECK(x) do{if(!(x)){fprintf(stderr,"wait-all boundary failed line%d case%u\\n",__LINE__,scenario);exit(1);}}while(0)
static unsigned scenario;static size_t cursor,total;static unsigned receives,clock_calls;
static unsigned char input[262144],output[262144];
static uint64_t qwen_launch_now(void*p){(void)p;++clock_calls;
 return scenario==7?10:scenario==8&&clock_calls>1?10:scenario==10?0:clock_calls;}
static ssize_t recv(int fd,void*data,size_t bytes,int flags){
 CHECK(fd==11&&flags==MSG_WAITALL&&bytes&&bytes<=sizeof(output));++receives;
 if(scenario==4||(scenario==6&&cursor))return 0;
 if(scenario==5)return -1;if(scenario==9)return (ssize_t)bytes+1;
 size_t n=bytes;if((scenario==3||scenario==6||scenario==8)&&!cursor)n=997;
 CHECK(cursor+n<=total);memcpy(data,input+cursor,n);cursor+=n;return (ssize_t)n;
}
'''+body+'''
int main(void){
 for(size_t i=0;i<sizeof(input);++i)input[i]=(unsigned char)(i*37+61);
 for(scenario=0;scenario<11;++scenario){
  cursor=receives=clock_calls=0;memset(output,0xa5,sizeof(output));
  total=scenario==0?128:scenario==2?180224:262144;unsigned calls=0;
  int ok=direct_receive_exact(11,output,total,10,&calls);
  CHECK(ok==(scenario<4)&&calls==receives&&receives<=2);
  if(ok)CHECK(cursor==total&&!memcmp(input,output,total)&&receives==(scenario==3?2u:1u));
  if(scenario==7||scenario==10)CHECK(!receives);
  if(scenario==8)CHECK(receives==1&&cursor==997);
 }
 puts("{\\"completed\\":true,\\"positive_controls\\":4,\\"negative_controls\\":7,\\"OS_objects\\":0,\\"PS5_operations\\":0}");
}
''',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'wait-all-boundaries.exe'
    command=[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    run=subprocess.run(command,capture_output=True,timeout=60,env=env);(a.out/'compile.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    run=subprocess.run([str(exe)],capture_output=True,timeout=15,env=env);(a.out/'controls.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')[-3000:]);tested=json.loads(run.stdout)
    result=dict(old,receiver=record(receiver),wait_all_receive=True,new_wait_all_controls=tested,
        unchanged_socket_transport_integrity_controls_replayed=0,previous_socket_profile=record(a.socket_profile),
        only_receive_flag_and_returned_length_guard_changed=True,native_large_model_part_qualified=False,
        inputs=[record(source),record(receiver),record(ROOT/'tools/model_part_receiver_geometry.py'),record(Path(__file__))],
        command=command,PS5_operations=0)
    save(a.out/'result.private.json',result)
    print(json.dumps(dict(completed=True,new_receive_controls=11,previous_controls_reused=True,PS5_operations=0)))


if __name__=='__main__':main()

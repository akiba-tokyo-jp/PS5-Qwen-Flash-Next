#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify bounded256KiB socket settings over the completed batch-data geometry."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from model_part_receiver_geometry import receiver_text
from start_success_route import load, need, save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','data-geometry','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=load(a.data_geometry)
    need(prior['completed'] and prior['receive_window_bytes']==262144 and prior['new_transport_geometry_controls']['returned_transport_and_file_cases']==14 and
         prior['new_integrity_geometry_controls']==dict(positive_sizes=12,returned_fault_modes=8,EOF_size_refusals=2,misalignment_empty_and_deadline_refusals=3),
         'The completed exact batch receive/readback controls are required')
    need(record(prior['receiver']['path'])==prior['receiver'] and record(prior['original_receiver']['path'])==prior['original_receiver'],
         'The completed actual receiver bodies changed')
    a.out.mkdir(parents=True,exist_ok=False)
    text=receiver_text(Path(prior['original_receiver']['path']).read_text(),262144,262144,True)
    receiver=a.out/'socket_batched_model_part_receive.h';receiver.write_text(text,newline='\n')
    mocked=text
    for name in ('sys/socket.h','netinet/in.h','sys/time.h'):
        mocked=once(mocked,'#include <'+name+'>\n','')
    mocked=once(mocked,'static _Alignas(16384) unsigned char direct_stage_window[262144];','static unsigned char *direct_stage_window;')
    (a.out/'direct_stage_under_test.h').write_text(mocked,newline='\n')
    fixture=(a.data_geometry.parent/'transport-geometry.c').read_text()
    before='static int setsockopt(int fd,int level,int name,const void *value,socklen_t bytes){CHECK((fd==10||fd==11)&&level==SOL_SOCKET&&name&&value&&bytes);return 0;}'
    after='''static unsigned config_case;
static int setsockopt(int fd,int level,int name,const void *value,socklen_t bytes){
    CHECK((fd==10||fd==11)&&level==SOL_SOCKET&&name&&value&&bytes);
    if(name==SO_RCVBUF){CHECK(fd==10&&bytes==sizeof(int)&&*(const int*)value==262144);if(config_case==2)return -1;}
    else{const struct timeval*t=value;CHECK(bytes==sizeof(*t)&&t->tv_sec==20&&!t->tv_usec);
        if((config_case==3&&fd==10&&name==SO_RCVTIMEO)||(config_case==4&&fd==11&&name==SO_RCVTIMEO)||
           (config_case==5&&fd==11&&name==SO_SNDTIMEO))return -1;}
    return 0;
}
static int getsockopt(int fd,int level,int name,void*value,socklen_t*bytes){
    CHECK(fd==10&&level==SOL_SOCKET&&name==SO_RCVBUF&&value&&bytes&&*bytes==sizeof(int));
    if(config_case==6)return -1;
    *bytes=sizeof(int)+(config_case==7);
    *(int*)value=config_case==1?524288:config_case==8?524289:config_case==9?262143:262144;
    return 0;
}'''
    fixture=once(fixture,before,after)
    fixture=once(fixture,'for(fault=GOOD;fault<FAULT_COUNT;++fault){','for(config_case=0;config_case<10;++config_case){fault=GOOD;')
    fixture=fixture.replace('fault==GOOD','config_case<2')
    marker='        if(fault==EXISTS||fault==PEER'
    need(fixture.count(marker)==1,'One original pre-open refusal assertion required')
    fixture=fixture.replace(marker,'        if(config_case>=2)CHECK(!opens&&!acks);\n'+marker,1)
    start=fixture.index('    printf(',fixture.index('int main(void)'))
    end=fixture.index('    return 0;',start)
    fixture=fixture[:start]+'''    printf("{\\"completed\\":true,\\"socket_configuration_cases\\":10,\\"positive_controls\\":2,\\"negative_controls\\":8,\\"OS_objects\\":0,\\"PS5_operations\\":0}\\n");
'''+fixture[end:]
    source=a.out/'socket-profile-controls.c';source.write_text(fixture,newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';sha=a.workspace/'native/model_hash/sha256.c';exe=a.out/'socket-controls.exe'
    command=list(map(str,[host/'clang.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',a.out,'-I',sha.parent,source,sha,'-o',exe]))
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    result=subprocess.run(command,capture_output=True,timeout=120,env=env);(a.out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    need(not result.returncode,result.stderr.decode(errors='replace')[-3500:])
    result=subprocess.run([str(exe)],capture_output=True,timeout=20,env=env);(a.out/'controls.private.log').write_bytes(result.stdout+result.stderr)
    need(not result.returncode,(result.stdout+result.stderr).decode(errors='replace')[-2500:]);tested=json.loads(result.stdout)
    need(tested['positive_controls']==2 and tested['negative_controls']==8 and tested['OS_objects']==0,'All actual socket-setting and bounded-observation controls must pass')
    save(a.out/'result.private.json',dict(completed=True,receiver=record(receiver),original_receiver=prior['original_receiver'],
        original_qualification=prior['original_qualification'],data_geometry=record(a.data_geometry),maximum_model_part_bytes=512<<20,
        receive_window_bytes=262144,whole_integrity_window_bytes=262144,host_send_window_bytes=16384,receive_socket_buffer_bytes=262144,
        maximum_observed_socket_setting_bytes=524288,additional_fixed_CPU_buffer_pages=30,additional_socket_kernel_allowance_pages=32,
        CPU_metadata_margin_pages=99,host_acknowledgement_timeout_seconds=90,socket_configuration_controls=tested,
        reused_ceiling_boundaries=7,reused_changed_data_transport_cases=14,reused_changed_integrity_controls=25,
        original_180_second_receive_deadline_preserved=True,all_before_and_returned_IO_stages_synced=True,
        native_large_model_part_qualified=False,inputs=[record(x) for x in (Path(__file__),ROOT/'tools/model_part_receiver_geometry.py',source,sha)],
        command=command,PS5_operations=0))
    print(json.dumps(dict(completed=True,new_socket_controls=10,reused_data_controls=39,extra_buffer_pages=30,extra_socket_allowance_pages=32,PS5_operations=0)))


if __name__=='__main__':main()

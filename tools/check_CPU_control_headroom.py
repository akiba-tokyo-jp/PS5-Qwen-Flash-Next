#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual CPU-control guard against malformed and changing samples."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    header=ROOT/'native/qwen_flash_next/launch_integrity_native.h';text=header.read_text()
    start=text.index('static int qwen_launch_headroom_sample(');end=text.index('static int qwen_launch_headroom(void',start)
    source='''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
static uint32_t values[7];static unsigned free_calls;static int fault;
static int report(const char*format,...){(void)format;return 1;}
static int sysctlbyname(const char*name,void*result,size_t*size,void*new_value,size_t new_size){
 const char*names[]={"vm.stats.vm0.v_free_count","hw.pagesize","vm.stats.vm0.v_page_count",
  "vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_target","vm.stats.vm0.v_free_reserved"};
 assert(!new_value&&!new_size);if(fault==1)return -1;if(fault==2){*size=3;return 0;}
 for(unsigned i=0;i<6;++i)if(!strcmp(name,names[i])){unsigned at=i;if(!i&&free_calls++)at=6;memcpy(result,values+at,4);return 0;}
 assert(0);return -1;
}
'''+text[start:end]+'''
static void reset(void){uint32_t original[]={2000,16384,138739,898,2974,206,2000};memcpy(values,original,sizeof(values));free_calls=0;fault=0;}
int main(void){
 reset();assert(qwen_launch_headroom_sample(NULL));
 reset();values[0]=values[6]=919;assert(qwen_launch_headroom_sample(NULL)==EXPECTED_919);
 reset();values[0]=values[6]=1125;assert(qwen_launch_headroom_sample(NULL)==EXPECTED_1125);
 reset();values[0]=values[6]=918;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[0]=values[6]=897;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[6]=897;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[0]=897;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[1]=8192;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[2]=0;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[5]=0;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[5]=899;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[3]=2974;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[4]=138740;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[0]=138740;assert(!qwen_launch_headroom_sample(NULL));
 reset();values[6]=138740;assert(!qwen_launch_headroom_sample(NULL));
 reset();fault=1;assert(!qwen_launch_headroom_sample(NULL));
 reset();fault=2;assert(!qwen_launch_headroom_sample(NULL));
 puts("17 actual guard controls passed; no OS writes");
}
'''
    path=args.out/'actual-CPU-guard.c';path.write_text(source,encoding='utf-8',newline='\n')
    host=args.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    profiles={'default':['-DEXPECTED_919=0','-DEXPECTED_1125=0'],
        'CPU-additive':['-DQWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES=21','-DEXPECTED_919=0','-DEXPECTED_1125=1'],
        'CPU-independent':['-DQWEN_LAUNCH_CPU_METADATA_MARGIN_PAGES=21','-DQWEN_LAUNCH_CPU_INDEPENDENT_THRESHOLDS=1','-DEXPECTED_919=1','-DEXPECTED_1125=1']}
    for name,flags in profiles.items():
        executable=args.out/(name+'.exe')
        for i,command in enumerate(([str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',*flags,str(path),'-o',str(executable)],[str(executable)])):
            result=subprocess.run(command,capture_output=True,timeout=60,env=env)
            (args.out/(name+'-'+str(i)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
    receipt=dict(completed=True,profiles=list(profiles),actual_source=record(header),controls_per_profile=17,
        all_OS_counter_queries_read_only=True,both_observed_OS_thresholds_preserved=True,
        PS5_operations=0,native_CPU_policy_qualification=False)
    (args.out/'result.private.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':main()

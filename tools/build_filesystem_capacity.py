#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a new read-only statfs helper using the qualified CPU publication ABI."""
import argparse,json,os,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();old=json.loads(a.parent.read_text());require(old['CPU_only']and old['GPU_calls']==0,'CPU-only parent required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();base=a.parent.parent;nonce=secrets.token_hex(16)
    remote='/data/ai/moss-qwen-capacity-'+nonce
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):
        (a.out/name).write_bytes((base/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[x.replace(str(base),str(a.out))for x in c]for c in old['commands']]
    commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/filesystem_capacity.cpp')
    # The unused quantizer object remains the same pinned parent object.
    for i,x in enumerate(commands[-1]):
        if Path(x).name=='encoder.o':commands[-1][i]=str(base/'encoder.o') if (base/'encoder.o').exists()else x
    # The parent may reference its ancestor encoder by its unchanged path.
    for i,cmd in enumerate(commands):
        run=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe'
    names={r.split()[0]for r in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if r.split()}
    require(names<=old['runtime_imports'].keys(),'Unexpected read-only helper import')
    require(not any(x.startswith(('sceAgc','sceKernelAllocateDirect','sceSystemServiceLaunch'))for x in names),'Read-only helper may not launch or allocate GPU memory')
    write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,
        parent=record(a.parent),source=record(ROOT/'native/qwen_flash_next/filesystem_capacity.cpp'),nonce=nonce,
        remote_elf=remote+'.elf',remote_log=remote+'.log',GPU_calls=0,title_launches=0,automatic_retries=0,
        runtime_imports={k:old['runtime_imports'][k]for k in sorted(names)}))
    print('Read-only filesystem capacity helper built; no console operations.')
if __name__=='__main__':main()

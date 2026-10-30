#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a CPU seal for complete triplets from one positively closed short write."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','failed-build','failed-result','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();parent=json.loads(a.parent.read_text());failed=json.loads(a.failed_result.read_text());build=json.loads(a.failed_build.read_text())
    require(failed['known_CPU_returned_refusal']and failed['new_output_retained'],'Only a positively returned owned partial is admitted')
    raw=Path(failed['raw']['path']).read_bytes();require(record(failed['raw']['path'])==failed['raw']and b'DIRECT known_completion_cleanup_returned=1 fully_released=1'in raw,'Positive CPU Direct retirement required')
    rows=[dict(re.findall(r'(\w+)=([^ ]+)',line))for line in raw.decode().splitlines()if line.startswith('BUNDLE index=')]
    require(rows and [int(r['index'])for r in rows]==list(range(len(rows)))and len(rows)<84,'A complete strict prefix of returned writes is required')
    original=json.loads(Path(build['selection']['path']).read_text());require(record(build['selection']['path'])==build['selection'],'Original selection changed')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-partial-seal-'+nonce
    header=a.out/'partial_bundle_plan.h';header.write_text('#pragma once\n#define PARTIAL_BUNDLE_NONCE '+json.dumps(nonce)+'\ninline constexpr const char*partial_bundle_path='+json.dumps(build['new_output'])+';\ninline constexpr unsigned partial_bundle_count='+str(len(rows))+';\ninline constexpr const char*partial_bundle_expected[]={'+','.join(json.dumps(r['SHA256'])for r in rows)+'};\n',newline='\n')
    base=a.parent.parent
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((base/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[v.replace(str(base),str(a.out))for v in c]for c in parent['commands']]
    commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/seal_partial_bundle.cpp')
    for i,v in enumerate(commands[-1]):
        if v==str(a.out/'encoder.o'):commands[-1][i]=str(base/'encoder.o')
    for i,cmd in enumerate(commands):
        run=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={r.split()[0]for r in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if r.split()}
    require(names<=parent['runtime_imports'].keys(),'Unaudited CPU partial-seal import')
    selected=dict(original,bundles=len(rows),Experts=original['Experts'][:len(rows)],short_write_full_prefix_only=True)
    write_json(a.out/'selection.private.json',selected)
    write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,nonce=nonce,
        remote_elf=remote+'.elf',remote_log=remote+'.log',partial_output=build['new_output'],verified_Experts=len(rows),
        selection=record(a.out/'selection.private.json'),inputs=[record(a.parent),record(a.failed_build),record(a.failed_result),failed['raw'],record(header),record(ROOT/'native/qwen_flash_next/seal_partial_bundle.cpp')],
        original_source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0))
    print(json.dumps(dict(known_complete_triplets=len(rows),CPU_seal_built=True,PS5_operations=0)))
if __name__=='__main__':main()

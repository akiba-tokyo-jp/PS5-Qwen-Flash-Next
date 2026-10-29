#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an exact, CPU-only new-output publication; never execute the console."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
TITLE='/data/ai/native-moss-image-sft/PPSA99190'
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('candidate','model','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();bound=json.loads(a.candidate.read_text());require(bound['completed'],'Bound explicit Q8 output candidate required')
 receipt=json.loads(Path(bound['candidate']['path']).read_text());parent=json.loads(a.model.read_text());down=json.loads(Path(parent['Down_conversion']['path']).read_text());base_path=Path(down['native_build']['path']);base=json.loads(base_path.read_text())
 for row in [bound['candidate'],bound['parent'],*bound['parts'],down['native_build']]:
  current=record(row['path']);require(all(current[k]==row[k]for k in ('path','bytes','sha256')),'Exact candidate/base input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);meta_nonce=secrets.token_hex(16);root=TITLE+'/expert-q2-'+nonce
 records=[]
 for i,local in enumerate([*bound['parts'],bound['candidate']]):
  source='/data/ai/moss-qwen-layout-'+(nonce if i<2 else meta_nonce)+'-512-'+str(i if i<2 else 0)+'.bin'
  destination=root+'/'+(receipt['files'][-1]['path']if i==0 else'output-Q8.part1.bin'if i==1 else'model-receipt.json')
  records.append(dict(local={k:local[k]for k in ('path','bytes','sha256')},source=source,destination=destination))
 header=a.out/'resident_output_Q8_publish_plan.h';header.write_text('#pragma once\n#include <cstdint>\n#define OUTPUT_Q8_PUBLISH_NONCE '+json.dumps(nonce)+'\ninline constexpr const char*output_Q8_directory='+json.dumps(root)+';\ninline constexpr const char*output_Q8_GGUF_SHA256='+json.dumps(receipt['resident_output_Q8']['converted']['sha256'])+';\nstruct OutputQ8PublicationFile{const char*source;const char*destination;std::uint64_t bytes;const char*sha256;};\ninline constexpr OutputQ8PublicationFile output_Q8_files[]={'+','.join('{'+json.dumps(r['source'])+','+json.dumps(r['destination'])+','+str(r['local']['bytes'])+'ULL,'+json.dumps(r['local']['sha256'])+'}'for r in records)+'};\n',newline='\n')
 require(re.fullmatch(re.escape(TITLE)+r'/expert-q2-[0-9a-f]{32}',root)and len(records)==3,'Only one exact fresh output namespace allowed')
 for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((base_path.parent/name).read_bytes())
 remote='/data/ai/moss-qwen-output-Q8-publish-'+nonce
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 commands=[base['commands'][0].copy(),base['commands'][1].copy(),base['commands'][-1].copy()]
 for c in commands:
  for i,v in enumerate(c):c[i]=v.replace(str(base_path.parent),str(a.out))
 commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/resident_output_q8_publish.cpp')
 for i,v in enumerate(commands[-1]):
  if v==str(a.out/'encoder.o'):commands[-1][i]=str(base_path.parent/'encoder.o')
 for i,c in enumerate(commands):
  r=subprocess.run(c,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-5000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={r.split()[0]for r in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if r.split()}
 require(names<=base['runtime_imports'].keys(),'New unaudited CPU import: '+repr(sorted(names-base['runtime_imports'].keys())))
 require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'CPU publication may not delete originals, launch titles or use GPU')
 inputs=[record(x)for x in [Path(__file__),ROOT/'native/qwen_flash_next/resident_output_q8_publish.cpp',a.candidate,a.model,base_path,header,*[a.out/n for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h','source_split_context.h')]]]
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-resident-output-Q8-publication-build-v1',completed_build=True,artifact=record(artifact),inputs=inputs,commands=commands,nonce=nonce,files=records,new_directory=root,app0_directory='/app0/'+root.rsplit('/',1)[1],full_GGUF_SHA256=receipt['resident_output_Q8']['converted']['sha256'],parent_receipt=bound['parent'],candidate_receipt=bound['candidate'],remote_elf=remote+'.elf',remote_log=remote+'.log',CPU_only=True,owned_Direct_bytes=8<<20,original_source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,runtime_imports={n:base['runtime_imports'][n]for n in sorted(names)}))
 print(json.dumps(dict(CPU_Q8_publication_built=True,new_files=3,new_data_bytes=sum(x['local']['bytes']for x in records),PS5_operations=0)))
if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish two owned all-Q2 metadata files after complete actual source hashing."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('finish','receipt','native-down','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();finish=json.loads(a.finish.read_text());receipt=json.loads(a.receipt.read_text());parent=json.loads(a.native_down.read_text());root=finish['new_directory']
 require(finish['schema']=='ps5-qwen-expert-all-q2-logical-finish-v1'and finish['completed']and finish['all_logical_bytes_native_hashed']and finish['all_payload_hash_spans_verified']and finish['Direct_window_positively_retired'],'Actual native logical model hashes and positive retirement required')
 require(receipt['schema']=='ps5-qwen-expert-all-q2-model-v1'and receipt['complete_conversion']==record(a.finish)and root==parent['new_directory']and re.fullmatch('/data/ai/native-moss-image-sft/PPSA99190/expert-q2-[0-9a-f]{32}',root),'Exact final all-Q2 source directory/receipt required')
 original=json.loads(parent['original_integrity']['raw']);files=[]
 for i,f in enumerate(finish['files']):
  item={k:v for k,v in f.items()if k!='regions'};item['parts']=[]
  for part in (original['logical_files'][i]['parts']if f['reused_original']else f['parts']):
   row=dict(part);row['path']=('/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/model/'if f['reused_original']else root+'/')+part['path'];item['parts'].append(row)
  files.append(item)
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-all-q2-seal-'+nonce
 backing=receipt['retained_mixed_source_seal'];require(record(backing['path'])==backing,'Exact retained mixed source seal required')
 metadata=[dict(remote=root+'/model-receipt.json',local=record(a.receipt)),dict(remote=root+'/retained-mixed-proof.json',local=backing)]
 for i,m in enumerate(metadata):m['staging']=remote+'-metadata-'+str(i)+'.json'
 h='#pragma once\n#include <array>\n#include <cstdint>\n#define Q2_SEAL_NONCE '+json.dumps(nonce)+'\n'
 for name,value in [('q2_seal_directory',root),('q2_seal_receipt',root+'/model-receipt.json'),('q2_seal_receipt_sha256',record(a.receipt)['sha256'])]:h+='inline constexpr const char*'+name+'='+json.dumps(value)+';\n'
 h+='inline constexpr uint64_t q2_seal_receipt_bytes='+str(a.receipt.stat().st_size)+'ULL;\ninline constexpr std::array<uint64_t,10>q2_seal_root_identity={'+','.join(str(v)+'ULL'for v in finish['directory_identity'])+'};\n'
 h+='struct SealMetadata{const char*path;const char*destination;uint64_t bytes;const char*sha256;};\ninline constexpr SealMetadata q2_seal_metadata[]={\n'+''.join('{'+json.dumps(m['staging'])+','+json.dumps(m['remote'])+','+str(m['local']['bytes'])+'ULL,'+json.dumps(m['local']['sha256'])+'},\n'for m in metadata)+'};\n'
 h+='struct SealPart{const char*path;std::array<uint64_t,10>identity;};\ninline constexpr SealPart q2_seal_parts[]={\n'+''.join('{'+json.dumps(v['path'])+',{'+','.join(str(x)+'ULL'for x in v['identity'])+'}},\n'for v in finish['physical_parts'])+'};\n'
 header=a.out/'expert_q2_seal_context.h';header.write_text(h,newline='\n')
 qualified=ROOT/'native/qwen_flash_next/expert_q2_seal.cpp';text=qualified.read_text();require(text.count('metadata_index<3')==1,'Exact qualified fixed-metadata sealer required');source=a.out/'all-Q2-seal.private.cpp';source.write_text(text.replace('three owned metadata files','two owned metadata files').replace('metadata_index<3','metadata_index<2'),newline='\n')
 for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((a.native_down.parent/name).read_bytes())
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 commands=[c.copy()for c in parent['commands']]
 for cmd in commands:
  for i,v in enumerate(cmd):cmd[i]=v.replace(str(a.native_down.parent),str(a.out))
 commands[1][commands[1].index('-c')+1]=str(source)
 for i,v in enumerate(commands[-1]):
  if v==str(a.out/'encoder.o'):commands[-1][i]=str(a.native_down.parent/'encoder.o')
 for i,cmd in enumerate(commands):
  run=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:])
 image=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={l.split()[0]for l in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(image)],text=True).splitlines()if l.split()};require(names<=parent['runtime_imports'].keys(),'Only previously qualified CPU runtime imports allowed')
 require(not any(re.search('(unlink|chown|pwrite|truncate|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'Sealer may only rename its two new metadata files and finalize their permissions')
 inputs=[record(x)for x in (Path(__file__),qualified,source,header,a.finish,a.receipt,a.native_down,a.out/'CPU-only-headroom.private.c',a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h')]+[m['local']for m in metadata]
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-expert-all-q2-seal-build-v1',completed_build=True,artifact=record(image),inputs=inputs,commands=commands,remote_elf=remote+'.elf',remote_log=remote+'.log',source_directory=root,model_receipt=record(a.receipt),finish=record(a.finish),logical_files=files,physical_parts=finish['physical_parts'],metadata_publication=metadata,original_split_integrity=parent['original_integrity'],CPU_only=True,source_writes=0,GPU_calls=0,title_launches=0,production_permission_changes=0,own_metadata_permission_finalizations=2,maximum_executions=1,automatic_retries=0))
 print(json.dumps(dict(actual_all_Q2_metadata_sealer_built=True,physical_sources=len(finish['physical_parts']),PS5_operations=0)),flush=True)
if __name__=='__main__':main()

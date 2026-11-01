#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one bounded native CPU-only repack of all active unchanged Q2 Experts."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
TITLE='/data/ai/native-moss-image-sft/PPSA99190'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('receipt','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();m=json.loads(a.receipt.read_text());require(record(a.receipt)['sha256']=='46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426','Exact current model receipt required')
 finish=json.loads(Path(m['complete_conversion']['path']).read_text());mixed_path=Path(m['retained_mixed_model_receipt']['path']);mixed=json.loads(mixed_path.read_text());seal_path=Path(m['retained_mixed_source_seal']['path']);seal=json.loads(seal_path.read_text());down_path=Path(m['Down_conversion']['path']);down=json.loads(down_path.read_text());parent_path=Path(down['native_build']['path']);parent=json.loads(parent_path.read_text())
 for row in(m['complete_conversion'],m['retained_mixed_model_receipt'],m['retained_mixed_source_seal'],m['Down_conversion'],down['native_build']):require(record(row['path'])==row,'Exact source ancestry changed')
 tensors={t['name']:t for t in mixed['tensors']};files={f['path']:f for f in mixed['files']};logical={f['path']:f for f in seal['logical_files']};sources=[];spans=[];roles=[]
 def index(path,identity):
  path=TITLE+path[5:]if path.startswith('/app0/')else path;row=dict(path=path,identity=identity);require(path.startswith(TITLE+'/expert-q2-')and identity[2]==0o100644 and identity[3]==identity[4]==0,'Only sealed original Q2 sources allowed')
  if row not in sources:sources.append(row)
  return sources.index(row)
 for layer in range(48):
  for role,size in [('gate',537600),('up',537600),('down',460800)]:
   first=len(spans)
   if role=='down':
    part=next(x for x in finish['physical_parts']if x['path'].endswith(f'/down-{layer}.q2_0'));require(part['identity'][5]==size*512,'Whole original Down tensor required');spans.append(dict(source=index(part['path'],part['identity']),role_offset=0,file_offset=0,bytes=size*512))
   else:
    tensor=tensors[f'blk.{layer}.ffn_{role}_exps.weight'];require(tensor['type']=='Q2_K'and tensor['bytes']==size*512,'Exact Gate/Up geometry required');file=files[tensor['file']];start=tensor['offset'];region=next(x for x in file['regions']if x['logical_offset']<=start and start+size*512<=x['logical_offset']+x['bytes']);require(region['storage']=='new','Original Q2_K byte region required');at=region['storage_offset']+start-region['logical_offset'];left=size*512
    for part in logical[tensor['file']]['parts']:
     if not left:break
     if not part['offset']<=at<part['offset']+part['bytes']:continue
     take=min(left,part['offset']+part['bytes']-at);spans.append(dict(source=index(part['path'],part['identity']),role_offset=size*512-left,file_offset=at-part['offset'],bytes=take));at+=take;left-=take
    require(not left,'All original Gate/Up spans required')
   require(sum(x['bytes']for x in spans[first:])==size*512,'Exact role coverage required');roles.append(dict(first_span=first,spans=len(spans)-first,expert_bytes=size))
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-full-bundle-'+nonce;directory=TITLE+'/qwen-full-bundles-'+nonce
 h='#pragma once\n#include <array>\n#include <cstdint>\n#define FULL_BUNDLE_NONCE '+json.dumps(nonce)+'\n';h+='inline constexpr const char*full_bundle_parent='+json.dumps(TITLE)+';\ninline constexpr const char*full_bundle_directory='+json.dumps(directory)+';\ninline constexpr unsigned full_bundle_per_part=348,full_bundle_parts=71;\ninline constexpr uint64_t full_bundle_total_bytes=37849399296ULL;\n'
 arr=lambda xs:'{'+','.join(str(v)+'ULL'for v in xs)+'}'
 h+='struct FullBundleSource{const char*path;std::array<uint64_t,10>identity;};\ninline constexpr FullBundleSource full_bundle_sources[]={\n'+''.join('{'+json.dumps(x['path'])+','+arr(x['identity'])+'},\n'for x in sources)+'};\n';h+='struct FullBundleSpan{unsigned source;uint64_t role_offset,file_offset,bytes;};\ninline constexpr FullBundleSpan full_bundle_spans[]={\n'+''.join('{'+','.join(str(x[k])+'ULL'for k in('source','role_offset','file_offset','bytes'))+'},\n'for x in spans)+'};\n';h+='struct FullBundleRole{unsigned first_span,spans;uint64_t expert_bytes;};\ninline constexpr FullBundleRole full_bundle_roles[]={\n'+''.join('{'+','.join(str(x[k])for k in('first_span','spans','expert_bytes'))+'},\n'for x in roles)+'};\n'
 header=a.out/'full_bundle_plan.private.h';header.write_text(h,newline='\n')
 for name in('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((parent_path.parent/name).read_bytes())
 guard=a.out/'qualified_context_guard.c';text=guard.read_text();old='(k.ki_stat==SSLEEP||k.ki_stat==SRUN)';require(text.count(old)==1,'Exact original service-state predicate required');guard.write_text(text.replace(old,'(k.ki_stat==SSLEEP||k.ki_stat==SRUN||(k.ki_stat==SLOCK&&!strcmp(e->name,"SceShellCore")))'),newline='\n')
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n');commands=[parent['commands'][0].copy(),parent['commands'][1].copy(),parent['commands'][-1].copy()]
 for c in commands:
  for i,v in enumerate(c):c[i]=v.replace(str(parent_path.parent),str(a.out))
 commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q2_full_bundle_pack.cpp');commands[1]+=['-I',str(ROOT/'native/app')]
 for i,v in enumerate(commands[-1]):
  if v==str(a.out/'encoder.o'):commands[-1][i]=str(parent_path.parent/'encoder.o')
 for i,c in enumerate(commands):
  run=subprocess.run(c,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4500:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if x.split()};require(names<=parent['runtime_imports'].keys(),'New unaudited runtime import: '+repr(sorted(names-parent['runtime_imports'].keys())));require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'No GPU, title launch, deletion or kernel writes allowed')
 inputs=[record(x)for x in(Path(__file__),ROOT/'native/qwen_flash_next/expert_q2_full_bundle_pack.cpp',ROOT/'native/app/expert_q2_bundle_layout.h',a.receipt,mixed_path,seal_path,down_path,parent_path,header,a.out/'CPU-only-headroom.private.c',guard,a.out/'close_context.h',a.out/'source_split_context.h')]
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-full-expert-bundle-pack-v1',completed_build=True,artifact=record(artifact),inputs=inputs,commands=commands,nonce=nonce,remote_elf=remote+'.elf',remote_log=remote+'.log',new_directory=directory,new_output_bytes=37849399296,parts=71,per_part=348,active_Experts=24576,source_spans=spans,source_roles=roles,sources=sources,CPU_only=True,owned_Direct_bytes=8<<20,source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,runtime_imports={n:parent['runtime_imports'][n]for n in sorted(names)},whole_native_SHA256_after_immutable_seal=True,original_fallback_required=True,quantized_bits_unchanged=True))
 print(json.dumps(dict(CPU_pack_built=True,active_Experts=24576,parts=71,output_bytes=37849399296,GPU_calls=0)))
if __name__=='__main__':main()

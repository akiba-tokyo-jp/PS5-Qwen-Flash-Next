#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded CPU-only actual-Q2 bundle and request-count comparison."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
TITLE='/data/ai/native-moss-image-sft/PPSA99190'
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('cache','receipt','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();model=json.loads(a.receipt.read_text());require(model['completed']and model['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE','Actual sealed all-Q2 model required')
 finish=json.loads(Path(model['complete_conversion']['path']).read_text());mixed_path=Path(model['retained_mixed_model_receipt']['path']);mixed=json.loads(mixed_path.read_text());seal_path=Path(model['retained_mixed_source_seal']['path']);seal=json.loads(seal_path.read_text())
 down_path=Path(model['Down_conversion']['path']);down=json.loads(down_path.read_text());parent_path=Path(down['native_build']['path']);parent=json.loads(parent_path.read_text())
 for row in (model['complete_conversion'],model['retained_mixed_model_receipt'],model['retained_mixed_source_seal'],model['Down_conversion'],down['native_build']):require(record(row['path'])==row,'Exact sealed source ancestry changed')
 tensors={t['name']:t for t in mixed['tensors']};files={f['path']:f for f in mixed['files']};logical={f['path']:f for f in seal['logical_files']}
 sources=[];spans=[];experts=[]
 def source_index(path,identity):
  path=TITLE+path[5:]if path.startswith('/app0/')else path
  row=dict(path=path,identity=identity);require(path.startswith(TITLE+'/expert-q2-')and identity[2]==0o100644 and identity[3]==identity[4]==0,'Only sealed immutable Q2 physical sources allowed')
  if row not in sources:sources.append(row)
  return sources.index(row)
 for layer in (0,23,47):
  for expert in (0,1,511):
   first=len(spans)
   for role,size,destination in [('gate',537600,0),('up',537600,537600),('down',460800,1075200)]:
    if role=='down':
     part=next(q for q in finish['physical_parts']if q['path'].endswith(f'/down-{layer}.q2_0'))
     spans.append(dict(source=source_index(part['path'],part['identity']),offset=expert*size,bytes=size,destination=destination));continue
    tensor=tensors[f'blk.{layer}.ffn_{role}_exps.weight'];file=files[tensor['file']];start=tensor['offset']+expert*size
    region=next(q for q in file['regions']if q['logical_offset']<=start and start+size<=q['logical_offset']+q['bytes'])
    require(region['storage']=='new','Gate/Up must use actual retained Q2_K bytes')
    at=region['storage_offset']+start-region['logical_offset'];left=size
    for part in logical[tensor['file']]['parts']:
     if not left:break
     if not part['offset']<=at<part['offset']+part['bytes']:continue
     take=min(left,part['offset']+part['bytes']-at)
     spans.append(dict(source=source_index(part['path'],part['identity']),offset=at-part['offset'],bytes=take,destination=destination+size-left));at+=take;left-=take
    require(left==0,'Complete original quantized role coverage required')
   require(sum(s['bytes']for s in spans[first:])==1536000,'All three complete Expert roles required')
   experts.append(dict(layer=layer,expert=expert,first_span=first,spans=len(spans)-first))
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-Q2-bundle-'+nonce;target=TITLE+'/qwen-Q2-bundle-probe-'+nonce+'.bin';file_bytes=(9*1540096+65535)//65536*65536
 arr=lambda values:'{'+','.join(str(v)+'ULL'for v in values)+'}'
 h='#pragma once\n#include <array>\n#include <cstdint>\n#define BUNDLE_PROBE_NONCE '+json.dumps(nonce)+'\n'
 for name,value in [('bundle_probe_parent',TITLE),('bundle_probe_path',target)]:h+='inline constexpr const char*'+name+'='+json.dumps(value)+';\n'
 h+='inline constexpr uint64_t bundle_probe_file_bytes='+str(file_bytes)+'ULL;\n'
 h+='struct BundleProbeSource{const char*path;std::array<uint64_t,10>identity;};\ninline constexpr BundleProbeSource bundle_probe_sources[]={\n'+''.join('{'+json.dumps(s['path'])+','+arr(s['identity'])+'},\n'for s in sources)+'};\n'
 h+='struct BundleProbeSpan{unsigned source;uint64_t offset,bytes,destination;};\ninline constexpr BundleProbeSpan bundle_probe_spans[]={\n'+''.join('{'+str(s['source'])+','+str(s['offset'])+'ULL,'+str(s['bytes'])+'ULL,'+str(s['destination'])+'ULL},\n'for s in spans)+'};\n'
 h+='struct BundleProbeExpert{unsigned layer,expert,first_span,spans;};\ninline constexpr BundleProbeExpert bundle_probe_experts[]={\n'+''.join('{'+','.join(str(s[k])for k in ('layer','expert','first_span','spans'))+'},\n'for s in experts)+'};\n'
 header=a.out/'expert_q2_bundle_probe_plan.h';header.write_text(h,newline='\n')
 for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((parent_path.parent/name).read_bytes())
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 commands=[parent['commands'][0].copy(),parent['commands'][1].copy(),parent['commands'][-1].copy()]
 for command in commands:
  for i,value in enumerate(command):command[i]=value.replace(str(parent_path.parent),str(a.out))
 commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q2_bundle_probe.cpp');commands[1]+=['-I',str(ROOT/'native/app')]
 # Keep the exact closed helper's auxiliary encoder object; no encoder call is
 # made by this source and all actual runtime imports are audited below.
 for i,value in enumerate(commands[-1]):
  if value==str(a.out/'encoder.o'):commands[-1][i]=str(parent_path.parent/'encoder.o')
 for i,command in enumerate(commands):
  run=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe'
 names={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if x.split()}
 require(names<=parent['runtime_imports'].keys(),'New unaudited CPU runtime import: '+repr(sorted(names-parent['runtime_imports'].keys())))
 require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'CPU helper may not launch titles, issue GPU work or delete files')
 inputs=[record(q)for q in [Path(__file__),ROOT/'native/qwen_flash_next/expert_q2_bundle_probe.cpp',ROOT/'native/app/expert_q2_bundle_layout.h',a.receipt,mixed_path,seal_path,down_path,parent_path,header,a.out/'CPU-only-headroom.private.c',a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h']]
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-Q2-bundle-probe-v1',completed_build=True,artifact=record(artifact),inputs=inputs,commands=commands,nonce=nonce,remote_elf=remote+'.elf',remote_log=remote+'.log',argument='',new_output=target,new_output_bytes=file_bytes,Expert_samples=experts,source_spans=spans,sources=sources,CPU_only=True,owned_Direct_bytes=8<<20,source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,runtime_imports={n:parent['runtime_imports'][n]for n in sorted(names)},same_byte_ABBA=True,quantized_bits_unchanged=True,original_context_and_memory_guards_retained=True))
 print(json.dumps(dict(CPU_Q2_bundle_probe_built=True,Experts=9,new_output_bytes=file_bytes,PS5_operations=0,CI_runs=0)))
if __name__=='__main__':main()

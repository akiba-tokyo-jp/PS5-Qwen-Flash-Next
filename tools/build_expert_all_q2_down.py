#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the isolated PS5 CPU Down converter from original BF16 source seals."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('cache','original-plan','original-down-proof','encoder-proof','samples','component-terminal','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 original=json.loads(a.original_plan.read_text());proof=json.loads(a.original_down_proof.read_text());encoder=json.loads(a.encoder_proof.read_text());samples=json.loads(a.samples.read_text());component=json.loads(a.component_terminal.read_text())
 require(original['completed_build']and original['GPU_calls']==0 and original['source_writes']==0,'Sealed BF16 CPU source plan required')
 require(proof['completed']and proof['conversion_location']=='PS5_CPU'and not proof['original_BF16_files_modified'],'Completed native per-tensor BF16 hashes required')
 require(encoder['completed']and encoder['matrices']==9,'Completed native MSE encoder qualification required')
 require(samples['completed']and samples['encoding']=='signed_FP16_scale_MSE_fit'and samples['all_decoded_values_match_pinned_Q2_0'],'Independent fitted-scale sample qualification required')
 require(component['completed']and component['all_outputs_reference_valid']and component['all_backends_positively_retired'],'Actual fitted-scale GPU component qualification required')
 parent_path=Path(encoder['manifest']['path']);require(record(parent_path)==encoder['manifest'],'Exact native MSE build required');parent=json.loads(parent_path.read_text())
 require(record(ROOT/'tools/expert_q2_mse_quantize.c')==samples['source'],'Qualified MSE encoder source changed')
 sealed=json.loads(original['original_integrity']['raw']);require(sealed['original_receipt_sha256']==original['original_receipt']['sha256']==proof['original_receipt']['sha256'],'Original BF16 receipt identities differ')
 old={t['name']:t for t in proof['tensors']};parts=[];tensors=[]
 for f in original['files']:
  for t in original['tensors'][f['first_tensor']:f['first_tensor']+f['tensor_count']]:
   match=re.fullmatch(r'blk\.(\d+)\.ffn_down_exps\.weight',t['name'])
   if not match:continue
   before=old[t['name']];require(before['source_offset']==t['source_offset']and before['source_bytes']==t['source_bytes']==1677721600,'Original Down payload geometry differs')
   first=len(parts);parts.extend(original['original_parts'][f['first_part']:f['first_part']+f['part_count']])
   tensors.append(dict(layer=int(match[1]),name=t['name'],file=f['name'],source_offset=t['source_offset'],source_bytes=t['source_bytes'],first_part=first,part_count=f['part_count'],original_payload_sha256=before['original_payload_sha256'],output_name='down-'+match[1]+'.q2_0',output_bytes=235929600))
 tensors.sort(key=lambda t:t['layer']);require([t['layer']for t in tensors]==list(range(49)),'All 49 Down tensors including MTP required')
 roots={p['path'].split('/qwen-runtime/model/')[0]+'/qwen-runtime/model'for p in parts};require(len(roots)==1,'Exact original BF16 model root required');root=roots.pop();partroot=root+('/'+sealed['part_directory']if sealed['part_directory']else'')
 nonce=secrets.token_hex(16);destination='/data/ai/native-moss-image-sft/PPSA99190/expert-q2-'+nonce;remote='/data/ai/moss-qwen-all-q2-down-'+nonce
 arr=lambda k:'{'+','.join(str(v)+'ULL'for v in k)+'}'
 h='#pragma once\n#include <array>\n#include <cstdint>\n#define DOWN_NONCE '+json.dumps(nonce)+'\n'
 for name,value in [('down_original_root',root),('down_original_parts_root',partroot),('down_destination_parent','/data/ai/native-moss-image-sft/PPSA99190'),('down_destination',destination)]:h+='inline constexpr const char*'+name+'='+json.dumps(value)+';\n'
 for name,value in [('down_original_root_identity',sealed['directory_identity']),('down_original_parts_identity',sealed['part_directory_identity'])]:h+='inline constexpr std::array<uint64_t,10>'+name+'='+arr(value)+';\n'
 h+='struct OriginalPart{const char*path;std::array<uint64_t,10>identity;};\ninline constexpr OriginalPart down_original_parts[]={\n'+''.join('{'+json.dumps(v['path'])+','+arr(v['identity'])+'},\n'for v in parts)+'};\n'
 h+='struct DownTensor{unsigned layer;uint64_t source_offset,source_bytes;unsigned first_part,part_count;const char*original_payload_sha256,*output_name;};\ninline constexpr DownTensor down_tensors[]={\n'
 h+=''.join('{'+str(t['layer'])+','+str(t['source_offset'])+'ULL,'+str(t['source_bytes'])+'ULL,'+str(t['first_part'])+','+str(t['part_count'])+','+json.dumps(t['original_payload_sha256'])+','+json.dumps(t['output_name'])+'},\n'for t in tensors)+'};\n'
 chosen=[x for x in samples['matrices']if x['role']=='down'];require(len(chosen)==9,'Nine independent original Down sample hashes required')
 h+='struct DownSample{unsigned layer,expert;const char*sha256;};\ninline constexpr DownSample down_samples[]={\n'+''.join('{'+str(x['layer'])+','+str(x['expert'])+','+json.dumps(x['q2_payload_sha256'])+'},\n'for x in chosen)+'};\n'
 header=a.out/'expert_all_q2_down_plan.h';header.write_text(h,newline='\n')
 for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((parent_path.parent/name).read_bytes())
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 commands=[parent['commands'][0].copy(),parent['commands'][1].copy(),parent['commands'][-1].copy()]
 for cmd in commands:
  for i,v in enumerate(cmd):cmd[i]=v.replace(str(parent_path.parent),str(a.out))
 commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_all_q2_down_convert.cpp')
 for i,v in enumerate(commands[-1]):
  if v==str(a.out/'actual-SHA256.o'):commands[-1][i]=str(a.cache/'build/expert-q4-encode-native-7602/actual-SHA256.o')
  if v==str(a.out/'encoder.o'):commands[-1][i]=str(parent_path.parent/'encoder.o')
 for i,cmd in enumerate(commands):
  run=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if x.split()}
 require(not any(re.search(r'(unlink|sceAgc|KillApp|LaunchApp|ptrace|setuid|kernel_set_)',n)for n in names),'Only isolated CPU file creation/publication is allowed')
 exports=parent['runtime_imports'].copy();runtime=json.loads((a.cache/'build/model-identity-snapshot-147/manifest.private.json').read_text())
 for row in runtime['sources']:
  path=Path(row['path'])
  if path.suffix!='.so'or path.name.endswith('_stub_weak.so'):continue
  require(record(path)==row,'Qualified runtime export source changed')
  for line in subprocess.check_output([str(nm),'-D','--defined-only','--format=posix',str(path)],text=True).splitlines():
   if line.split():exports.setdefault(line.split()[0],path.name)
 require(names<=exports.keys(),'Down converter contains unresolved runtime imports: '+repr(sorted(names-exports.keys())))
 inputs=[record(path)for path in (Path(__file__),ROOT/'native/qwen_flash_next/expert_all_q2_down_convert.cpp',ROOT/'tools/expert_q2_mse_quantize.c',a.original_plan,a.original_down_proof,a.encoder_proof,a.samples,a.component_terminal,header,a.out/'CPU-only-headroom.private.c',a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h',parent_path.parent/'encoder.o',a.cache/'build/expert-q4-encode-native-7602/actual-SHA256.o')]
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-expert-all-q2-down-converter-v1',completed_build=True,artifact=record(artifact),inputs=inputs,commands=commands,nonce=nonce,remote_elf=remote+'.elf',remote_log=remote+'.log',new_directory=destination,original_receipt=original['original_receipt'],original_integrity=original['original_integrity'],original_down_proof=record(a.original_down_proof),tensors=tensors,original_parts=parts,new_file_bytes=11560550400,encoding='signed_FP16_scale_MSE_fit',Down_format='Q2_0',Gate_Up_format='retained_Q2_K',all_Experts_and_MTP_preserved=True,non_Expert_payloads_untouched=True,CPU_only=True,CPU_workers=4,owned_Direct_bytes=32<<20,native_process_limit_seconds=7200,minimum_disk_margin_bytes=2<<30,metadata_reserve_bytes=64<<20,source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,runtime_imports={n:exports[n]for n in sorted(names)}))
 print(json.dumps(dict(Down_only_CPU_converter_built=True,matrices=25088,original_BF16_payload_bytes=82208358400,new_bytes=11560550400,console_operations=0)),flush=True)
if __name__=='__main__':main()

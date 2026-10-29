#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one CPU-only Q8 tail conversion from sealed original console BF16."""
import argparse,json,os,secrets,subprocess,re,hashlib
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
TITLE='/data/ai/native-moss-image-sft/PPSA99190'
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('publication','seal','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--resume-result',type=Path)
 a=p.parse_args();publication=json.loads(a.publication.read_text());seal=json.loads(a.seal.read_text());base_path=Path(publication['inputs'][4]['path']);base=json.loads(base_path.read_text())
 require(publication['completed_build']and publication['CPU_only']and seal['all_new_parts_complete_Direct_SHA256_readback']and seal['all_parts_unchanged_since_readback']and seal['CPU_owners_positively_closed'],'Bound completed CPU publisher and source seal required')
 source=seal['logical_files'][-1];require(source['bytes']==1271398560 and source['reused_original']and len(source['parts'])==3,'Original BF16 output geometry required')
 target=publication['files'][1];require(target['local']['bytes']==138559648 and re.fullmatch(r'/data/ai/moss-qwen-layout-[0-9a-f]{32}-512-1.bin',target['source']),'Only missing new Q8 part allowed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-Q8-tail-'+nonce
 h='#pragma once\n#include <cstdint>\n#include <array>\n#define OUTPUT_Q8_TAIL_NONCE '+json.dumps(nonce)+'\n'
 h+='inline constexpr const char*tail_target='+json.dumps(target['source'])+';\ninline constexpr const char*tail_SHA256='+json.dumps(target['local']['sha256'])+';\n'
 existing=0;prefix_SHA=''
 if a.resume_result:
  previous=json.loads(a.resume_result.read_text());require(previous['completed']and previous['known_CPU_completion']and not previous['conversion_passed'],'Only a positively closed own partial may resume')
  raw=Path(previous['raw']['path']).read_bytes();require(record(previous['raw']['path'])==previous['raw']and b'REFUSED reason=Q8 tail CPU owner changed'in raw and b'DIRECT known_completion_cleanup_returned=1 fully_released=1'in raw,'Exact known-returned source-scope refusal required')
  written=[int(x)for x in re.findall(rb'RETURN own_Q8_tail_write bytes=([0-9]+) errno=0',raw)];existing=sum(written);require(existing>0 and existing%16384==0,'Complete aligned own prefix required')
  with Path(target['local']['path']).open('rb')as f:prefix_SHA=hashlib.sha256(f.read(existing)).hexdigest()
 at=(512<<20)+existing-160
 h+='inline constexpr uint64_t tail_bytes=138559648,tail_first_block='+str(at//34)+',tail_initial_skip='+str(at%34)+',tail_existing_bytes='+str(existing)+';\ninline constexpr const char*tail_existing_SHA256='+json.dumps(prefix_SHA)+';\nstruct TailSource{const char*path;uint64_t offset;std::array<uint64_t,10>identity;};\ninline constexpr TailSource tail_sources[]={\n'
 for s in source['parts']:
  require(s['path'].startswith('/app0/qwen-runtime/model/')and s['identity'][2]==0o100644 and s['bytes']==s['identity'][5],'Read-only original source identity required')
  h+='{'+json.dumps(TITLE+s['path'][5:])+','+str(s['offset'])+'ULL,{'+','.join(str(x)+'ULL'for x in s['identity'])+'}},\n'
 h+='};\n';header=a.out/'resident_output_Q8_tail_plan.h';header.write_text(h,newline='\n')
 for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/n).write_bytes((base_path.parent/n).read_bytes())
 if a.resume_result:
  # SLOCK is a transient, unsuspended lock wait. Admit it only for the exact
  # ShellCore owner in this CPU-only helper; every identity/tracer check stays.
  guard=a.out/'qualified_context_guard.c';text=guard.read_text();old='(k.ki_stat==SSLEEP||k.ki_stat==SRUN)';require(text.count(old)==1,'Exact CPU owner predicate required')
  guard.write_text(text.replace(old,'(k.ki_stat==SSLEEP||k.ki_stat==SRUN||(k.ki_stat==SLOCK&&!strcmp(e->name,"SceShellCore")))'),newline='\n')
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 commands=[base['commands'][0].copy(),base['commands'][1].copy(),base['commands'][0].copy(),base['commands'][-1].copy()]
 for cmd in commands:
  for i,v in enumerate(cmd):cmd[i]=v.replace(str(base_path.parent),str(a.out))
 commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/resident_output_q8_tail.cpp')
 commands[2][commands[2].index('-c')+1]=str(ROOT/'tools/resident_output_q8_quantize.c');commands[2][commands[2].index('-o')+1]=str(a.out/'encoder.o');commands[2]+=['-ffp-contract=off']
 for i,v in enumerate(commands[-1]):
  if Path(v).name=='encoder.o':commands[-1][i]=str(a.out/'encoder.o')
 for i,cmd in enumerate(commands):
  r=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-6000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={r.split()[0]for r in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if r.split()}
 require(names<=base['runtime_imports'].keys(),'Unaudited CPU import: '+repr(sorted(names-base['runtime_imports'].keys())))
 require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'CPU tail may not issue GPU, deletion or title operations')
 inputs=[record(x)for x in (Path(__file__),ROOT/'native/qwen_flash_next/resident_output_q8_tail.cpp',ROOT/'tools/resident_output_q8_quantize.c',a.publication,a.seal,base_path,header,a.out/'qualified_context_guard.c')]
 if a.resume_result:inputs.append(record(a.resume_result))
 write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),inputs=inputs,commands=commands,nonce=nonce,target=target,existing_prefix_bytes=existing,existing_prefix_SHA256=prefix_SHA,remote_elf=remote+'.elf',remote_log=remote+'.log',owned_Direct_bytes=8<<20,original_source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,runtime_imports={n:base['runtime_imports'][n]for n in sorted(names)}))
 print(json.dumps(dict(CPU_Q8_tail_built=True,new_bytes=138559648,original_BF16_bytes_read=260818176,PS5_operations=0)))
if __name__=='__main__':main()

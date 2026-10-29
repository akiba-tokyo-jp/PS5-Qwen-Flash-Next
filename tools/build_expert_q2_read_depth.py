#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a CPU-only depth 1/2/4 equal-byte probe on real routed Expert demands."""
import argparse,json,os,secrets,subprocess,re
from pathlib import Path
from expert_q4 import require,record,write_json
from q2_physical_spans import Q2PhysicalSpans
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('cache','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--qualified-ShellCore-lock',action='store_true',help='Retain exact ShellCore identity and allow its already observed SLOCK state in this CPU-only helper')
 a=p.parse_args();model=Q2PhysicalSpans(a.cache/'Expert-all-Q2-receipt-8652.json');fill_path=ROOT/'.local/Q2-IO-distribution-9332/fills.private.json';fills=json.loads(fill_path.read_text())[1]['fill_records']
 groups=[];sources=[]
 for row in fills[8*48:9*48]:
  reads=[]
  for expert,slot in row['fills']:
   spans=model.role(row['layer'],expert,'gate')
   if len(spans)!=1:continue
   s=spans[0];offset=s['offset']//16384*16384;size=(s['offset']-offset+s['bytes']+16383)//16384*16384
   if offset+size>s['identity'][5]:continue
   source={k:s[k]for k in ('path','identity')}
   if source not in sources:sources.append(source)
   reads.append(dict(source=sources.index(source),offset=offset,bytes=size,expert=expert))
   if len(reads)==4:break
  if len(reads)==4:groups.append(dict(layer=row['layer'],reads=reads))
 require(16<=len(groups)<=48,'Representative simultaneous four-demand rows required')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);prefix='/data/ai/moss-qwen-Q2-depth-'+nonce
 h='#pragma once\n#include <array>\n#include <cstdint>\n#define DEPTH_PROBE_NONCE '+json.dumps(nonce)+'\n'
 h+='inline constexpr unsigned depth_source_count='+str(len(sources))+';\ninline constexpr unsigned depth_group_count='+str(len(groups))+';\n'
 h+='struct DepthSource{const char*path;std::array<std::uint64_t,10>identity;};\ninline constexpr DepthSource depth_sources[]={'+','.join('{'+json.dumps(s['path'])+',{'+','.join(str(x)+'ULL'for x in s['identity'])+'}}'for s in sources)+'};\n'
 h+='struct DepthRead{unsigned source;std::uint64_t offset;unsigned bytes;};\nstruct DepthGroup{unsigned layer;DepthRead reads[4];};\ninline constexpr DepthGroup depth_groups[]={'+','.join('{'+str(g['layer'])+',{'+','.join('{'+str(r['source'])+','+str(r['offset'])+'ULL,'+str(r['bytes'])+'}'for r in g['reads'])+'}}'for g in groups)+'};\n'
 header=a.out/'depth_probe_plan.h';header.write_text(h,newline='\n')
 old=a.cache/'build/Expert-all-Q2-bundle-pack-9072';parent=json.loads((old/'manifest.private.json').read_text())
 for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((old/name).read_bytes())
 if a.qualified_ShellCore_lock:
  guard=a.out/'qualified_context_guard.c';text=guard.read_text();before='(k.ki_stat==SSLEEP||k.ki_stat==SRUN)'
  require(text.count(before)==1,'Exact CPU-only process state guard required')
  text=text.replace(before,'(k.ki_stat==SSLEEP||k.ki_stat==SRUN||(k.ki_stat==SLOCK&&!strcmp(e->name,"SceShellCore")))');guard.write_text(text,newline='\n')
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(prefix+'.log')+'\n',newline='\n')
 commands=[[x.replace(str(old),str(a.out))for x in cmd]for cmd in parent['commands']]
 commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q2_read_depth.cpp')
 for cmd in commands:
  run=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/(str(commands.index(cmd))+'.private.log')).write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if x.split()}
 providers=dict(parent['runtime_imports']);lib=a.workspace/'toolchain/ps5-payload-sdk/target/lib'
 for filename,provider in [('libkernel_web.so','libkernel.so'),('libSceLibcInternal.so','libSceLibcInternal.so')]:
  exported={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--defined-only','--format=posix',str(lib/filename)],text=True).splitlines()if x.split()}
  for name in names&exported:providers[name]=provider
 require(names<=providers.keys(),'Unaudited CPU imports: '+repr(names-providers.keys()))
 require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'CPU depth helper may not change source files, GPU or titles')
 inputs=model.inputs+[record(x)for x in (Path(__file__),ROOT/'tools/q2_physical_spans.py',ROOT/'native/qwen_flash_next/expert_q2_read_depth.cpp',ROOT/'native/app/bounded_read_pool.h',fill_path,header,a.out/'CPU-only-headroom.private.c',a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h')]
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-Q2-read-depth-v1',completed_build=True,artifact=record(artifact),inputs=inputs,commands=commands,nonce=nonce,remote_elf=prefix+'.elf',remote_log=prefix+'.log',sources=sources,groups=groups,CPU_only=True,owned_Direct_bytes=8<<20,source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,runtime_imports={n:providers[n]for n in names},timed_order=[1,2,4,4,2,1],component_not_model_tok_s=True,original_context_and_memory_guards_retained=True))
 print(json.dumps(dict(completed_build=True,groups=len(groups),sources=len(sources),PS5_operations=0)))
if __name__=='__main__':main()

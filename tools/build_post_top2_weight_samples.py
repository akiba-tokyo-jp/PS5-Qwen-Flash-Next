#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded CPU-only copy of three same-layer native-sealed triplets."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('pack','producer','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();pack=json.loads(a.pack.read_text());producer=json.loads(a.producer.read_text());require(pack['completed']and pack['CPU_Direct_positively_retired']and producer['completed_build']and producer['CPU_only'],'Existing complete CPU seals required')
 sel=json.loads(Path(pack['selection']['path']).read_text())['Experts'];by_layer={}
 for i,k in enumerate(sel):by_layer.setdefault(k['layer'],[]).append((i,k))
 layer=next(l for l in sorted(by_layer)if len(by_layer[l])>=3);chosen=by_layer[layer][:3];a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 nonce=secrets.token_hex(16);title='/data/ai/native-moss-image-sft/PPSA99190';remote='/data/ai/moss-qwen-weight-samples-'+nonce;target=title+'/qwen-Q2-bundle-probe-'+nonce+'.bin';size=(3*1540096+65535)//65536*65536
 old=Path(producer['artifact']['path']).parent
 for name in('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((old/name).read_bytes())
 for source in old.glob('*.h'):
  if source.name!='expert_q2_bundle_probe_plan.h':(a.out/source.name).write_bytes(source.read_bytes())
 context=a.out/'source_split_context.h';body=context.read_text();body,count=re.subn(r'(#define\s+SPLIT_LOG\s+)"[^"\n]+"',lambda m:m[1]+json.dumps(remote+'.log'),body)
 require(count==1,'Exactly one own immutable journal path must be rebound before execution');context.write_text(body,newline='\n')
 row=pack['output'];header=a.out/'expert_q2_bundle_probe_plan.h'
 h='#pragma once\n#include <array>\n#include <cstdint>\n#define BUNDLE_PROBE_COUNT 3\n#define BUNDLE_PROBE_NONCE '+json.dumps(nonce)+'\n'
 h+='inline constexpr const char*bundle_probe_parent='+json.dumps(title)+';\ninline constexpr const char*bundle_probe_path='+json.dumps(target)+';\ninline constexpr uint64_t bundle_probe_file_bytes='+str(size)+'ULL;\n'
 h+='struct BundleProbeSource{const char*path;std::array<uint64_t,10>identity;};\ninline constexpr BundleProbeSource bundle_probe_sources[]={{'+json.dumps(row['path'])+',{'+','.join(str(v)+'ULL'for v in row['identity'])+'}}};\n'
 h+='struct BundleProbeSpan{unsigned source;uint64_t offset,bytes,destination;};\ninline constexpr BundleProbeSpan bundle_probe_spans[]={'+','.join('{0,'+str(i*1540096+offset)+'ULL,'+str(n)+'ULL,'+str(offset)+'ULL}'for i,k in chosen for offset,n in((0,537600),(537600,537600),(1075200,460800)))+'};\n'
 h+='struct BundleProbeExpert{unsigned layer,expert,first_span,spans;};\ninline constexpr BundleProbeExpert bundle_probe_experts[]={'+','.join('{'+f'{k["layer"]},{k["expert"]},{j*3},3'+'}'for j,(i,k)in enumerate(chosen))+'};\n';header.write_text(h,newline='\n')
 commands=[]
 for index,oldcmd in enumerate(producer['commands']):
  if '-c'in oldcmd:
   source=Path(oldcmd[oldcmd.index('-c')+1])
   if source.parent==old:
    text=source.read_text()
    if source.suffix=='.cpp':text=text.replace('pread(input,readback,16384,payload)==ssize_t(tail)','pread(input,readback,tail,payload)==ssize_t(tail)')
    (a.out/source.name).write_text(text,newline='\n')
  cmd=[s.replace(str(old),str(a.out))for s in oldcmd];commands.append(cmd)
  r=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{index}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-2500:])
 artifact=a.out/Path(producer['artifact']['path']).name;require(artifact.is_file(),'Recompiled actual CPU artifact required')
 require((remote+'.log').encode()in artifact.read_bytes()and producer['remote_log'].encode()not in artifact.read_bytes(),'Actual ELF must bind the new unique journal, never the template journal')
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-three-same-layer-weight-samples-v1',completed_build=True,artifact=record(artifact),commands=commands,
  inputs=[record(__file__),record(a.pack),record(a.producer),record(header),*[record(x)for x in sorted(a.out.iterdir())if x.suffix in('.h','.c','.cpp')]],
  nonce=nonce,remote_elf=remote+'.elf',remote_log=remote+'.log',argument='',new_output=target,new_output_bytes=size,
  source_pack=record(a.pack),selected_source_triplets=[dict(physical_index=i,layer=k['layer'],expert=k['expert'])for i,k in chosen],
  Expert_samples=3,source_spans=9,CPU_only=True,owned_Direct_bytes=8<<20,source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,
  whole_native_SHA256_after_immutable_seal=True,original_context_and_memory_guards_retained=True,learned_inference=False,weight_preparation_only=True))
 print(json.dumps(dict(completed_build=True,same_layer=layer,triplets=3,new_output_bytes=size,GPU_calls=0,PS5_operations=0)))
if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind actual Down outputs and retained source ranges to a complete native hash pass."""
import argparse,hashlib,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
TITLE='/data/ai/native-moss-image-sft/PPSA99190'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('cache','layout','topology-control','native-down','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--down-conversion',type=Path);p.add_argument('--syntax-control',action='store_true');a=p.parse_args()
 require(a.syntax_control==(a.down_conversion is None),'Actual conversion required unless building an explicitly non-deployable syntax control')
 layout=json.loads(a.layout.read_text());control=json.loads(a.topology_control.read_text());parent=json.loads(a.native_down.read_text())
 require(control['completed']and control['metadata_only']and control['not_for_deployment']and control['plan']==record(a.layout),'Exact validated metadata topology required')
 topology_path=Path(control['topology']['path']);require(record(topology_path)==control['topology'],'Topology changed');topology=json.loads(topology_path.read_text());require(topology['metadata_only']and topology['not_for_deployment'],'Topology must not masquerade as actual weight evidence')
 root=layout['new_directory'];app0='/app0/'+Path(root).name;require(root==parent['new_directory']and record(parent['original_receipt']['path'])==parent['original_receipt'],'Exact original-source Down build required')
 mixed=json.loads(Path(layout['mixed_receipt']['path']).read_text());mixedseal=json.loads(Path(layout['mixed_seal']['path']).read_text())
 for r in (layout['mixed_receipt'],layout['mixed_seal'],layout['headers'],layout['down_plan']):require(record(r['path'])==r,'Qualified layout source changed')
 if a.syntax_control:
  synthetic=json.loads(Path(control['model']['path']).read_text());synthetic_gate=json.loads(Path(control['gate']['path']).read_text());synthetic_seal=json.loads(synthetic_gate['Expert_all_Q2_source_integrity']['raw'])
  down={t['name']:dict(t,identity=synthetic_seal['Down_files'][t['layer']]['identity'])for t in synthetic['Down_files']};root_identity=synthetic_seal['directory_identity']
 else:
  actual=json.loads(a.down_conversion.read_text());require(actual['schema']=='ps5-qwen-expert-all-q2-down-conversion-v1'and actual['completed']and actual['encoding']=='signed_FP16_scale_MSE_fit'and actual['matrices']==25088 and actual['new_directory']==root and actual['original_receipt']==parent['original_receipt']and not actual['original_BF16_files_modified'],'Complete original-BF16 Down conversion required')
  require(actual['all_physical_parts_full_Direct_SHA256_readback_passed']and actual['CPU_workers_positively_joined']and actual['Direct_window_positively_retired'],'Actual Down whole readback and positive retirement required')
  down={t['name']:t for t in actual['files']};root_identity=actual['directory_identity']
 require(len(down)==49,'Every Down tensor required')
 original=json.loads(parent['original_integrity']['raw']);known={}
 for f in original['logical_files']:
  for part in f['parts']:known[TITLE+'/qwen-runtime/model/'+part['path']]=part['identity']
 q4seal_path=a.cache/'build/Expert-Q4-relocation-7670/source-integrity.private.json';q4seal=json.loads(q4seal_path.read_text())
 for seal in (q4seal,mixedseal):
  for f in seal['logical_files']:
   for part in f['parts']:known[part['path'].replace('/app0/',TITLE+'/',1)]=part['identity']
 headers=[];byheader={};pack=Path(layout['headers']['path'])
 with pack.open('rb')as stream:
  for f in layout['files']:
   if f['reused_original']:continue
   stream.seek(f['header_pack_offset']);raw=stream.read(f['header_bytes']);require(len(raw)==f['header_bytes'],'Complete header source required');row=dict(file=f['index'],name=f['path'],bytes=f['header_bytes'],pack_offset=f['header_pack_offset'],sha256=hashlib.sha256(raw).hexdigest());byheader[f['path']]=len(headers);headers.append(row)
 require(len(headers)==74,'Every replacement header required');parts=[]
 bydown={'down-'+str(i)+'.q2_0':down['blk.'+str(i)+'.ffn_down_exps.weight']for i in range(49)}
 for part in topology['physical']:
  path=part['path'].replace('/app0/',TITLE+'/',1);name=Path(path).name
  if path.startswith(root+'/'):
   if name in byheader:
    index=byheader[name];require(part['bytes']==headers[index]['bytes'],'Header physical size differs');parts.append(dict(path=path,identity=[0]*10,header=index));continue
   require(name in bydown,'Unexpected new physical source');d=bydown[name];require(d.get('output_bytes',d.get('bytes'))==part['bytes']==235929600,'Every new Down file must retain all 512 Experts');k=d['identity'];require(k[2]==0o100644 and k[3]==k[4]==0 and k[5]==235929600,'Actual Down identity differs');parts.append(dict(path=path,identity=k,header=-1));continue
  require(path in known and known[path]==part['identity']and part['bytes']==part['identity'][5],'Every retained source identity must match actual native BF16/Q4/mixed seals');parts.append(dict(path=path,identity=part['identity'],header=-1))
 ranges=[];hashes=[];files=[]
 for i,(f,source)in enumerate(zip(layout['files'],topology['logical'])):
  require(Path(source['path']).name==f['path']and source['path']==(app0+'/'+f['path']if not f['reused_original']else source['path'])and source['bytes']==f['bytes'],'Exact logical file topology required');first_range=len(ranges);cursor=0
  for r in source['ranges']:
   require(r['logical_offset']==cursor and r['bytes']and r['physical']<len(parts),'Complete ordered source partition required');k=parts[r['physical']];limit=headers[k['header']]['bytes']if k['header']>=0 else k['identity'][5];require(r['physical_offset']<limit and r['bytes']<=limit-r['physical_offset'],'Every source range must fit actual immutable bytes');ranges.append(r);cursor+=r['bytes']
  require(cursor==f['bytes'],'Logical source coverage differs');first_hash=len(hashes)
  if f['reused_original']:hashes.append(dict(bytes=f['bytes'],sha256=f['sha256']))
  else:
   hashes.append(dict(bytes=f['header_bytes'],sha256=headers[byheader[f['path']]]['sha256']))
   for t in layout['tensors']:
    if t['file']!=f['path']:continue
    sha=down[t['name']]['sha256']if t['type']=='Q2_0'else t['payload_sha256'];require(re.fullmatch('[0-9a-f]{64}',sha)is not None,'Complete real payload hash required');hashes.append(dict(bytes=t['bytes'],sha256=sha))
  require(sum(h['bytes']for h in hashes[first_hash:])==f['bytes'],'Every complete payload hash span required')
  files.append(dict(index=i,name=f['path'],bytes=f['bytes'],first_range=first_range,ranges=len(ranges)-first_range,first_hash=first_hash,hashes=len(hashes)-first_hash,original_whole=f['sha256']if f['reused_original']else''))
 require(len(files)==76 and sum(f['bytes']for f in files)==151157049472 and len(ranges)<=8192,'Complete all-Q2 logical model required')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-all-q2-finish-'+nonce;remote_pack='/data/ai/moss-qwen-all-q2-headers-'+nonce+'.bin';arr=lambda k:'{'+','.join(str(v)+'ULL'for v in k)+'}'
 h='#pragma once\n#include <array>\n#include <cstdint>\n#define FINISH_NONCE '+json.dumps(nonce)+'\ninline constexpr bool finish_deployable='+str(not a.syntax_control).lower()+';\n'
 for name,value in [('finish_directory',root),('finish_pack',remote_pack),('finish_pack_sha256',layout['headers']['sha256'])]:h+='inline constexpr const char*'+name+'='+json.dumps(value)+';\n'
 h+='inline constexpr uint64_t finish_pack_bytes='+str(layout['headers']['bytes'])+'ULL;\ninline constexpr std::array<uint64_t,10>finish_root_identity='+arr(root_identity)+';\n'
 h+='struct FinishPart{const char*path;std::array<uint64_t,10>identity;int header;};\ninline constexpr FinishPart finish_parts[]={\n'+''.join('{'+json.dumps(v['path'])+','+arr(v['identity'])+','+str(v['header'])+'},\n'for v in parts)+'};\n'
 h+='struct FinishHeader{unsigned file;const char*name;uint64_t bytes,pack_offset;const char*sha256;};\ninline constexpr FinishHeader finish_headers[]={\n'+''.join('{'+str(v['file'])+','+json.dumps(v['name'])+','+str(v['bytes'])+'ULL,'+str(v['pack_offset'])+'ULL,'+json.dumps(v['sha256'])+'},\n'for v in headers)+'};\n'
 h+='struct FinishRange{uint64_t logical,bytes;unsigned physical;uint64_t offset;};\ninline constexpr FinishRange finish_ranges[]={\n'+''.join('{'+str(v['logical_offset'])+'ULL,'+str(v['bytes'])+'ULL,'+str(v['physical'])+','+str(v['physical_offset'])+'ULL},\n'for v in ranges)+'};\n'
 h+='struct FinishHash{uint64_t bytes;const char*sha256;};\ninline constexpr FinishHash finish_hashes[]={\n'+''.join('{'+str(v['bytes'])+'ULL,'+json.dumps(v['sha256'])+'},\n'for v in hashes)+'};\n'
 h+='struct FinishFile{unsigned index;uint64_t bytes;unsigned first_range,ranges,first_hash,hashes;const char*original_whole;};\ninline constexpr FinishFile finish_files[]={\n'+''.join('{'+str(v['index'])+','+str(v['bytes'])+'ULL,'+','.join(str(v[k])for k in ('first_range','ranges','first_hash','hashes'))+','+json.dumps(v['original_whole'])+'},\n'for v in files)+'};\n'
 header=a.out/'expert_all_q2_finish_plan.h';header.write_text(h,newline='\n')
 for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((a.native_down.parent/name).read_bytes())
 (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
 commands=[v.copy()for v in parent['commands']]
 for cmd in commands:
  for i,v in enumerate(cmd):cmd[i]=v.replace(str(a.native_down.parent),str(a.out))
 commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_all_q2_finish.cpp')
 for i,v in enumerate(commands[-1]):
  if v==str(a.out/'encoder.o'):commands[-1][i]=str(a.native_down.parent/'encoder.o')
 for i,cmd in enumerate(commands):
  run=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:])
 artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if x.split()}
 original_imports=json.loads((a.cache/'build/expert-q2-local-8210/manifest.private.json').read_text())['imports'];exports=dict(original_imports,**parent['runtime_imports']);require(names<=exports.keys(),'Unqualified finish runtime imports: '+repr(sorted(names-exports.keys())))
 require(not any(re.search('(unlink|chown|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'Only own header publication and read-only payload verification allowed')
 inputs=[record(x)for x in (Path(__file__),ROOT/'native/qwen_flash_next/expert_all_q2_finish.cpp',a.layout,a.topology_control,topology_path,a.native_down,q4seal_path,header,a.out/'CPU-only-headroom.private.c',a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h')]+([record(a.down_conversion)]if a.down_conversion else[])
 write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-expert-all-q2-finish-build-v1',completed_build=True,deployable=not a.syntax_control,metadata_only_syntax_control=a.syntax_control,artifact=record(artifact),inputs=inputs,commands=commands,remote_elf=remote+'.elf',remote_log=remote+'.log',headers=layout['headers'],remote_header_pack=remote_pack,new_directory=root,files=files,header_files=headers,physical_parts=parts,hash_spans=len(hashes),mapped_file_bytes=151157049472,layout=record(a.layout),down_conversion=record(a.down_conversion)if a.down_conversion else None,native_down=record(a.native_down),CPU_window_bytes=8<<20,native_process_limit_seconds=1800,source_writes=0,GPU_calls=0,title_launches=0,maximum_executions=1,automatic_retries=0,runtime_imports={n:exports[n]for n in sorted(names)}))
 print(json.dumps(dict(all_Q2_logical_finisher_built=True,deployable=not a.syntax_control,logical_files=76,hash_spans=len(hashes),physical_sources=len(parts),PS5_operations=0)),flush=True)
if __name__=='__main__':main()

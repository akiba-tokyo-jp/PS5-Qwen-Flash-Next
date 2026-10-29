#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an isolated candidate metadata publisher/sealer; never execute it."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q2 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('conversion','receipt','native-conversion','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();conversion=json.loads(a.conversion.read_text());parent=json.loads(a.native_conversion.read_text())
    receipt=json.loads(a.receipt.read_text());root=conversion['new_directory']
    require(re.fullmatch('/data/ai/native-moss-image-sft/PPSA99190/expert-q2-[0-9a-f]{32}',root)and root==parent['new_directory'], 'Exact isolated completed copy required')
    require(conversion['completed']and conversion['all_physical_parts_full_Direct_SHA256_readback_passed']and
        conversion['Direct_window_positively_retired']and receipt['complete_conversion']==record(a.conversion), 'All new parts must finish complete readback and positive retirement')
    original=parent['original_integrity'];old=json.loads(original['raw']);files=[];parts=[]
    for i,row in enumerate(conversion['files']):
        file=dict(row);file.pop('regions',None);file['parts']=[]
        source=old['logical_files'][i]if row['reused_original']else row
        require(source['path']==row['path']and source['bytes']==row['bytes']and source['sha256']==row['sha256'],'Exact old/new logical source binding required')
        for part in source['parts']:
            item=dict(part);item['path']=('/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/model/'if row['reused_original']else root+'/')+part['path']
            require(item['identity'][2]==0o100644 and item['identity'][3]==item['identity'][4]==0,'Only root-owned sealed model parts are allowed')
            parts.append(item);file['parts'].append(item)
        files.append(file)
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);prefix='/data/ai/moss-qwen-q2-seal-'+nonce
    h='#pragma once\n#include <array>\n#include <cstdint>\n#define Q2_SEAL_NONCE '+json.dumps(nonce)+'\n'
    for key,value in (('q2_seal_directory',root),('q2_seal_receipt',root+'/model-receipt.json'),('q2_seal_receipt_sha256',record(a.receipt)['sha256'])):
        h+='inline constexpr const char*'+key+'='+json.dumps(value)+';\n'
    h+='inline constexpr std::uint64_t q2_seal_receipt_bytes='+str(a.receipt.stat().st_size)+'ULL;\n'
    h+='inline constexpr std::array<std::uint64_t,10>q2_seal_root_identity={'+','.join(str(x)+'ULL'for x in conversion['directory_identity'])+'};\n'
    sidecars=[dict(remote=root+'/retained-Q4-proof.json',local=conversion['retained_Q4_source_seal']),
        dict(remote=root+'/retained-Q4-layout.json',local=conversion['retained_Q4_conversion'])]
    for item in sidecars:require(record(item['local']['path'])==item['local'],'Exact retained backing metadata required')
    metadata=[dict(remote=root+'/model-receipt.json',local=record(a.receipt)),*sidecars]
    for i,item in enumerate(metadata):item['staging']=prefix+'-metadata-'+str(i)+'.json'
    h+='struct SealMetadata{const char*path;const char*destination;std::uint64_t bytes;const char*sha256;};\ninline constexpr SealMetadata q2_seal_metadata[]={\n'
    h+=''.join('{'+json.dumps(item['staging'])+','+json.dumps(item['remote'])+','+str(item['local']['bytes'])+'ULL,'+json.dumps(item['local']['sha256'])+'},\n'for item in metadata)+'};\n'
    h+='struct SealPart{const char*path;std::array<std::uint64_t,10>identity;};\ninline constexpr SealPart q2_seal_parts[]={\n'
    h+=''.join('{'+json.dumps(part['path'])+',{'+','.join(str(x)+'ULL'for x in part['identity'])+'}},\n'for part in parts)+'};\n'
    header=a.out/'expert_q2_seal_context.h';header.write_text(h,newline='\n')
    source=a.native_conversion.parent
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((source/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(prefix+'.log')+'\n',newline='\n')
    commands=[]
    for previous in parent['commands'][:2]:
        command=[v.replace(str(source),str(a.out))for v in previous]
        if command[command.index('-c')+1].endswith('expert_q2_local_convert.cpp'):
            command[command.index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q2_seal.cpp')
        commands.append(command)
    link=parent['commands'][-1].copy()
    for previous,current in zip(parent['commands'][:2],commands):
        old=previous[previous.index('-o')+1];require(link.count(old)==1,'Exact qualified CPU object replacement required');link[link.index(old)]=current[current.index('-o')+1]
    image=a.out/'candidate-seal.elf';link[link.index('-o')+1]=str(image);commands.append(link)
    inputs=[record(x)for x in (Path(__file__),ROOT/'native/qwen_flash_next/expert_q2_seal.cpp',a.conversion,a.receipt,a.native_conversion,header,
        a.out/'CPU-only-headroom.private.c',a.out/'source_split_context.h',a.out/'qualified_context_guard.c',a.out/'close_context.h')]
    inputs +=[item['local']for item in sidecars]
    for command in link:
        path=Path(command)
        if path.is_file()and path.suffix in ('.o','.a','.so')and not str(path).startswith(str(a.out)):inputs.append(record(path))
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    for row in inputs:require(record(row['path'])==row,'Sealer build dependency changed')
    nm=Path(commands[1][0]).parent/'llvm-nm.exe';symbols=subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(image)],text=True)
    names={line.split()[0]for line in symbols.splitlines()if line.split()}
    require(names<=parent['imports'].keys(),'New CPU sealer runtime import is not qualified')
    require(not any(re.search(r'(sceAgc|KillApp|ptrace|chown|ftruncate|pwrite|kernel_set_|kernel_copy|setuid|unlink)',name)for name in names),'Candidate sealer import boundary failed')
    write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-expert-q2-seal-build-v1',completed=True,artifact=record(image),inputs=inputs,commands=commands,
        nonce=nonce,backing_metadata=sidecars,metadata_publication=metadata,remote_elf=prefix+'.elf',remote_log=prefix+'.log',source_directory=root,model_receipt=record(a.receipt),conversion=record(a.conversion),
        original_split_integrity=original,logical_files=files,physical_files=len(parts),CPU_only=True,source_writes=0,GPU_calls=0,title_launches=0,
        production_permission_changes=0,only_permission_change='three own newly published candidate metadata files to 0644',
        publication='native rename of exactly three verified staged metadata files into the owned candidate directory; no existing target overwrite',automatic_retries=0))
    print(json.dumps(dict(candidate_sealer_built=True,physical_files=len(parts),PS5_operations=0)),flush=True)

if __name__=='__main__':main()

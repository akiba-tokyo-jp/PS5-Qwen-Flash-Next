#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an isolated candidate receipt sealer; never execute or alter production."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('conversion','receipt','native-conversion','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();conversion=json.loads(a.conversion.read_text());parent=json.loads(a.native_conversion.read_text())
    receipt=json.loads(a.receipt.read_text());root=conversion['new_directory']
    require(re.fullmatch('/data/ai/moss-qwen-expert-q4-[0-9a-f]{32}',root)and root==parent['new_directory'], 'Exact isolated completed copy required')
    require(conversion['completed']and conversion['all_physical_parts_full_Direct_SHA256_readback_passed']and
        conversion['Direct_window_positively_retired']and receipt['complete_conversion']==record(a.conversion), 'All new parts must finish complete readback and positive retirement')
    original=parent['original_integrity'];old=json.loads(original['raw']);files=[];parts=[]
    for i,row in enumerate(conversion['files']):
        file=dict(row);file['parts']=[]
        source=old['logical_files'][i]if row['reused_original']else row
        require(source['path']==row['path']and source['bytes']==row['bytes']and source['sha256']==row['sha256'],'Exact old/new logical source binding required')
        for part in source['parts']:
            item=dict(part);item['path']=('/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/model/'if row['reused_original']else root+'/')+part['path']
            require(item['identity'][2]==0o100644 and item['identity'][3]==item['identity'][4]==0,'Only root-owned sealed model parts are allowed')
            parts.append(item);file['parts'].append(item)
        files.append(file)
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);prefix='/data/ai/moss-qwen-q4-seal-'+nonce
    h='#pragma once\n#include <array>\n#include <cstdint>\n#define Q4_SEAL_NONCE '+json.dumps(nonce)+'\n'
    for key,value in (('q4_seal_directory',root),('q4_seal_receipt',root+'/model-receipt.json'),('q4_seal_receipt_sha256',record(a.receipt)['sha256'])):
        h+='inline constexpr const char*'+key+'='+json.dumps(value)+';\n'
    h+='inline constexpr std::uint64_t q4_seal_receipt_bytes='+str(a.receipt.stat().st_size)+'ULL;\n'
    h+='inline constexpr std::array<std::uint64_t,10>q4_seal_root_identity={'+','.join(str(x)+'ULL'for x in conversion['directory_identity'])+'};\n'
    h+='struct SealPart{const char*path;std::array<std::uint64_t,10>identity;};\ninline constexpr SealPart q4_seal_parts[]={\n'
    h+=''.join('{'+json.dumps(part['path'])+',{'+','.join(str(x)+'ULL'for x in part['identity'])+'}},\n'for part in parts)+'};\n'
    header=a.out/'expert_q4_seal_context.h';header.write_text(h,newline='\n')
    source=a.native_conversion.parent
    for name in ('qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((source/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(prefix+'.log')+'\n',newline='\n')
    commands=[]
    for previous in parent['commands'][:2]:
        command=[v.replace(str(source),str(a.out))for v in previous]
        if command[command.index('-c')+1].endswith('expert_q4_local_convert.cpp'):
            command[command.index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q4_seal.cpp')
        commands.append(command)
    link=parent['commands'][-1].copy()
    for previous,current in zip(parent['commands'][:2],commands):
        old=previous[previous.index('-o')+1];require(link.count(old)==1,'Exact qualified CPU object replacement required');link[link.index(old)]=current[current.index('-o')+1]
    image=a.out/'candidate-seal.elf';link[link.index('-o')+1]=str(image);commands.append(link)
    inputs=[record(x)for x in (Path(__file__),ROOT/'native/qwen_flash_next/expert_q4_seal.cpp',a.conversion,a.receipt,a.native_conversion,header,
        a.out/'source_split_context.h',a.out/'qualified_context_guard.c',a.out/'close_context.h')]
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
    require(not any(re.search(r'(sceAgc|KillApp|ptrace|chown|ftruncate|rename|pwrite|kernel_set_|kernel_copy|setuid|unlink)',name)for name in names),'Candidate sealer import boundary failed')
    write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-expert-q4-seal-build-v1',completed=True,artifact=record(image),inputs=inputs,commands=commands,
        nonce=nonce,remote_elf=prefix+'.elf',remote_log=prefix+'.log',source_directory=root,model_receipt=record(a.receipt),conversion=record(a.conversion),
        original_split_integrity=original,logical_files=files,physical_files=len(parts),CPU_only=True,source_writes=0,GPU_calls=0,title_launches=0,
        production_permission_changes=0,only_permission_change='own newly published candidate receipt to 0644',automatic_retries=0))
    print(json.dumps(dict(candidate_sealer_built=True,physical_files=len(parts),PS5_operations=0)),flush=True)

if __name__=='__main__':main()

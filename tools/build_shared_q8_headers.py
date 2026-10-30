#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extract new GGUF prefixes into the already-owned shared-Q8 directory."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('publication','model','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();publication=json.loads(a.publication.read_text());seal=json.loads(Path(publication['source_integrity']['path']).read_text());r=json.loads(Path(publication['candidate']['path']).read_text())
    require(publication['completed']and publication['native_whole_SHA256_EOF_identities_passed']and r['resident_Q8_overlay']['tensor_offsets_compacted'],'Published compact pack required')
    for row in (publication['source_integrity'],publication['candidate']):require(record(row['path'])==row,'Published shared asset changed')
    base_path=Path(publication['base_build']['path']);base=json.loads(base_path.read_text());model=json.loads(a.model.read_text());down=json.loads(Path(model['Down_conversion']['path']).read_text());abi_path=Path(down['native_build']['path']);abi=json.loads(abi_path.read_text())
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-shared-headers-'+nonce;root=seal['canonical_source_directory']
    require(re.fullmatch(r'/data/ai/native-moss-image-sft/PPSA99190/expert-q2-[0-9a-f]{32}',root),'Only the owned new publication directory allowed')
    arr=lambda v:'{'+','.join(str(x)+'ULL'for x in v)+'}'
    h='#pragma once\n#include <array>\n#include <cstdint>\n#define SHARED_Q8_HEADERS_NONCE '+json.dumps(nonce)+'\n'
    for name,path,key in (('directory',root,seal['directory_identity']),('pack',root+'/resident-shared-Q8.bin',seal['pack']['identity']),('receipt',root+'/model-receipt.json',seal['receipt_identity'])):
        h+='inline constexpr const char*shared_header_'+name+'='+json.dumps(path)+';\ninline constexpr std::array<std::uint64_t,10>shared_header_'+name+'_key='+arr(key)+';\n'
    headers=r['resident_Q8_overlay']['headers'];require(0<len(headers)<=76,'Bounded new header set required');rows=[]
    for v in headers:
        require(re.fullmatch(r'qwen-flash-next-bf16-\d{5}-of-00076\.gguf',v['file'])and 0<v['bytes']<=64<<20 and v['pack_offset']%16384==0 and v['pack_offset']+((v['bytes']+16383)//16384*16384)<=seal['pack']['bytes'],'Exact bounded source header required')
        rows.append(dict(file=v['file'],path=root+'/'+v['file'],offset=v['pack_offset'],bytes=v['bytes'],sha256=v['sha256']))
    h+='struct SharedHeader{const char*path;std::uint64_t offset,bytes;const char*sha256;};\ninline constexpr SharedHeader shared_headers[]={'+','.join('{'+json.dumps(v['path'])+','+str(v['offset'])+'ULL,'+str(v['bytes'])+'ULL,'+json.dumps(v['sha256'])+'}'for v in rows)+'};\n'
    header=a.out/'shared_Q8_headers_plan.h';header.write_text(h,newline='\n')
    for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/n).write_bytes((base_path.parent/n).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[x.replace(str(base_path.parent),str(a.out))for x in c]for c in base['commands']];commands[1][commands[1].index('-c')+1]=str(ROOT/'native/qwen_flash_next/resident_shared_q8_headers.cpp')
    for i,c in enumerate(commands):
        run=subprocess.run(c,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode()[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={x.split()[0]for x in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines()if x.split()}
    require(names<=abi['runtime_imports'].keys(),'New unaudited CPU import: '+str(names-abi['runtime_imports'].keys()))
    require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n)for n in names),'Owned header extraction cannot delete originals, launch a title or use GPU')
    write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,nonce=nonce,headers=rows,
        publication=record(a.publication),source_integrity=publication['source_integrity'],candidate=publication['candidate'],owned_Direct_bytes=8<<20,
        remote_elf=remote+'.elf',remote_log=remote+'.log',maximum_executions=1,automatic_retries=0,GPU_calls=0,title_launches=0,original_source_writes=0,
        runtime_imports={n:abi['runtime_imports'][n]for n in sorted(names)},inputs=[record(x)for x in (Path(__file__),ROOT/'native/qwen_flash_next/resident_shared_q8_headers.cpp',a.publication,a.model,base_path,abi_path,header,*[a.out/n for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h','source_split_context.h')])]))
    print('Bounded new-header extraction built; existing pack, receipt and original weights remain readonly.')
if __name__=='__main__':main()

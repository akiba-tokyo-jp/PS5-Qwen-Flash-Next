#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an owned-Q4-directory relocation helper; never execute it."""
import argparse,json,os,re,secrets,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('seal-build','source-integrity','native-conversion','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.seal_build.read_text());proof=json.loads(a.source_integrity.read_text());prior=json.loads(a.native_conversion.read_text())
    require(m['completed']and m['production_permission_changes']==0 and
        proof['all_new_parts_complete_Direct_SHA256_readback']and proof['all_parts_unchanged_since_readback']and
        proof['CPU_owners_positively_closed']and proof['model_receipt_sha256']==m['model_receipt']['sha256'],
        'Complete CPU-only readback and receipt sealing are required before relocation')
    source=proof['source_directory'];match=re.fullmatch('/data/ai/moss-qwen-expert-q4-([0-9a-f]{32})',source)
    require(match and source==m['source_directory']==prior['new_directory'],'Only this completed new Q4 copy may move')
    require(prior['CPU_only']and prior['GPU_calls']==prior['title_launches']==prior['source_writes']==0,'Qualified CPU-only import ancestry required')
    for row in m['inputs']+[m['artifact']]:require(record(row['path'])==row,'A qualified sealing input changed')
    original_proof=proof['original_split_integrity'];import hashlib
    require(hashlib.sha256(original_proof['raw'].encode()).hexdigest()==original_proof['sha256'],'Original BF16 split proof changed')
    oldproof=json.loads(original_proof['raw']);title='/data/ai/native-moss-image-sft/PPSA99190'
    target=title+'/expert-q4-'+match[1];app='/app0/expert-q4-'+match[1];original=title+'/qwen-runtime/model'
    require(target.startswith(title+'/expert-q4-')and target!=source,'Exact title-owned destination required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);prefix='/data/ai/moss-qwen-q4-relocation-'+nonce
    base=a.seal_build.parent;header=(base/'expert_q4_seal_context.h').read_text()
    pattern=r'inline constexpr std::array<std::uint64_t,10>q4_seal_root_identity=\{[^;]+;'
    rows=re.findall(pattern,header);require(len(rows)==1,'Exact qualified source root initializer required')
    def arr(key):return '{'+','.join(str(x)+'ULL'for x in key)+'}'
    header=header.replace(rows[0],'inline constexpr std::array<std::uint64_t,10>q4_seal_root_identity='+arr(proof['directory_identity'])+';')
    header+='\n#define Q4_RELOCATION_NONCE '+json.dumps(nonce)+'\n'
    for key,value in (('q4_relocation_parent',title),('q4_relocation_target',target),('q4_original_directory',original),
        ('q4_original_part_directory',original+('/'+oldproof['part_directory']if oldproof['part_directory']else''))):
        header+='inline constexpr const char*'+key+'='+json.dumps(value)+';\n'
    for key,value in (('q4_relocation_receipt_identity',proof['receipt_identity']),('q4_original_directory_identity',oldproof['directory_identity']),
        ('q4_original_part_directory_identity',oldproof['part_directory_identity'])):
        header+='inline constexpr std::array<std::uint64_t,10>'+key+'='+arr(value)+';\n'
    h=a.out/'expert_q4_relocation_context.h';h.write_text(header,newline='\n')
    for name in ('qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((base/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(prefix+'.log')+'\n',newline='\n')
    commands=[]
    for previous in m['commands'][:2]:
        command=[x.replace(str(base),str(a.out))for x in previous]
        if command[command.index('-c')+1].endswith('expert_q4_seal.cpp'):
            command[command.index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q4_relocate.cpp')
        commands.append(command)
    link=m['commands'][-1].copy()
    for previous,current in zip(m['commands'][:2],commands):
        old=previous[previous.index('-o')+1];require(link.count(old)==1,'Exact CPU object replacement required');link[link.index(old)]=current[current.index('-o')+1]
    image=a.out/'relocate-Q4.elf';link[link.index('-o')+1]=str(image);commands.append(link)
    inputs=[record(path)for path in (Path(__file__),ROOT/'native/qwen_flash_next/expert_q4_relocate.cpp',a.seal_build,a.source_integrity,a.native_conversion,
        h,a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h')]
    for argument in link:
        path=Path(argument)
        if path.is_file()and path.suffix in ('.o','.a','.so')and not str(path).startswith(str(a.out)):inputs.append(record(path))
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    for row in inputs:require(record(row['path'])==row,'A relocation build input changed')
    nm=Path(commands[1][0]).parent/'llvm-nm.exe';symbols=subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(image)],text=True)
    names={line.split()[0]for line in symbols.splitlines()if line.split()}
    require(names<=prior['imports'].keys()and not any(re.search(r'(sceAgc|KillApp|ptrace|chown|chmod|ftruncate|pwrite|kernel_set_|kernel_copy|setuid|unlink|mount)',name)for name in names),
        'Relocation may only rename its owned new directory; no original writes, permission changes, links, mounts or GPU APIs')
    write_json(a.out/'manifest.private.json',dict(schema='ps5-qwen-expert-q4-relocation-build-v1',completed=True,console_executed=False,
        artifact=record(image),inputs=inputs,commands=commands,source=source,target=target,app_visible_root=app,source_integrity=record(a.source_integrity),
        remote_elf=prefix+'.elf',remote_log=prefix+'.log',original_source_writes=0,permission_changes=0,mount_changes=0,maximum_renames=1,
        automatic_retries=0,imports={name:prior['imports'][name]for name in sorted(names)}))
    print(json.dumps(dict(owned_Q4_relocation_helper_built=True,console_operations=0,original_source_writes=0,permission_changes=0,mount_changes=0)),flush=True)
if __name__=='__main__':main()

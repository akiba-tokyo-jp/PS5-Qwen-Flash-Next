#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded PS5 CPU converter from sealed originals to new Q2 parts."""
import argparse,json,os,secrets,struct,subprocess
from pathlib import Path
from expert_q4 import EXPERT,record,require,write_json,pinned_gguf
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','original','inventory','policy','encoder-probe','host-partial','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--destination-parent',default='/data/ai')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    require(a.destination_parent=='/data/ai/native-moss-image-sft/PPSA99190','Use the existing writable task data area without production permission changes')
    inventory=json.loads(a.inventory.read_text());policy=json.loads(a.policy.read_text());probe=json.loads(a.encoder_probe.read_text())
    require(probe['completed'] and probe['all_native_Q2_bytes_match_pinned_SHA256'] and probe['matrices']==27,'Exact read-only PS5 encoder qualification required')
    parent_path=Path(probe['manifest']['path']);require(record(parent_path)==probe['manifest'],'Native encoder manifest changed')
    parent=json.loads(parent_path.read_text());require(record(a.original/'model-receipt.json')==inventory['original_receipt'],'Original BF16 receipt changed')
    integrity=policy['native_first_generation_validation']['split_native_integrity'];sealed=json.loads(integrity['raw'])
    import hashlib
    require(hashlib.sha256(integrity['raw'].encode()).hexdigest()==integrity['sha256'] and sealed['original_receipt_sha256']==inventory['original_receipt']['sha256'],
            'Complete original split integrity binding required')
    original_root='/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/model';gguf,_=pinned_gguf(a.cache)
    nonce=secrets.token_hex(16);destination=a.destination_parent+'/expert-q2-'+nonce
    prefix='/data/ai/moss-qwen-q2-local-'+nonce;pack_name='expert-q2-headers-'+nonce+'.bin';pack=a.out/pack_name
    known=json.loads(a.host_partial.read_text());require(known['original_receipt']==inventory['original_receipt'],'Independent host conversion source differs')
    known_files={}  # Q4 outputs cannot attest new Q2 bytes; independent samples attest the encoder.
    files=[];tensors=[];parts=[];aliases=[]
    retained_path=a.cache/'expert-q4-local-conversion-7605/model-receipt.private.json'
    retained=json.loads(retained_path.read_text());retained_rows={t['name']:t for t in retained['tensors']}
    retained_seal=a.cache/'build/Expert-Q4-relocation-7670/source-integrity.private.json'
    require(json.loads(retained_seal.read_text())['model_receipt_sha256']=='c88b821d6187fa2ca448c71ff8cbcc8db650ba720a0e698684338018fb71349b','Exact retained Q4 seal required')
    with pack.open('xb')as output:
        for index,item in enumerate(inventory['files']):
            if not item['replacement_required']:continue
            old=item['original'];source=a.original/old['path'];before=source.stat()
            require(before.st_size==old['bytes'],'Original logical source size changed')
            reader=gguf.GGUFReader(source,'r');require(reader.alignment==32,'The exact original 32-byte GGUF alignment is required')
            header=bytearray(reader.data[:reader.data_offset]);cursor=int(reader.data_offset);packed_cursor=cursor;regions=[dict(logical_offset=0,bytes=cursor,storage="new",storage_offset=0)];start=len(tensors)
            for tensor in reader.tensors:
                match=EXPERT.fullmatch(tensor.name);bits=(4 if match[2]=='down' else 2)if match else 0
                quantize=bool(bits);count=int(tensor.n_elements)*(84 if bits==2 else 18)//(256 if bits==2 else 32)if bits else int(tensor.n_bytes)
                field=tensor.field.offset+sum(x.nbytes for x in tensor.field.parts[:5])
                if quantize:struct.pack_into('<I',header,field-4,int(gguf.GGMLQuantizationType.Q2_K if bits==2 else gguf.GGMLQuantizationType.Q4_0))
                struct.pack_into('<Q',header,field,cursor-reader.data_offset)
                tensors.append(dict(name=tensor.name,source_offset=int(tensor.data_offset),source_bytes=int(tensor.n_bytes),
                    output_offset=cursor,output_bytes=count,bits=bits,quantize=quantize))
                if bits==2:
                    regions.append(dict(logical_offset=cursor,bytes=count,storage="new",storage_offset=packed_cursor));packed_cursor+=count
                if bits!=2:
                    previous=retained_rows[tensor.name]
                    require(previous['output_bytes']==count,'Only byte-identical retained Q4/non-Expert payloads may be aliased')
                    aliases.append(dict(name=tensor.name,file=old['path'],logical_offset=cursor,bytes=count,
                        retained_file=old['path'],retained_offset=previous['output_offset'],payload_sha256=previous['output_payload_sha256']))
                    regions.append(dict(logical_offset=cursor,bytes=count,storage='retained_Q4',storage_offset=previous['output_offset'],retained_file=old['path'],tensor=tensor.name,payload_sha256=previous['output_payload_sha256']))
                end=cursor+count;cursor=(end+31)&~31
                if cursor>end:
                    regions.append(dict(logical_offset=end,bytes=cursor-end,storage="new",storage_offset=packed_cursor));packed_cursor+=cursor-end
            del reader
            after=source.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),
                'Original GGUF identity changed during metadata preparation')
            header_offset=output.tell();output.write(header);output.write(bytes((-output.tell())%16384))
            sealed_file=sealed['logical_files'][index];require(sealed_file['path']==old['path'] and sealed_file['sha256']==old['sha256'] and sealed_file['bytes']==old['bytes'],
                'Original native logical SHA/identity proof differs')
            first_part=len(parts)
            for part in sealed_file['parts']:parts.append(dict(path=original_root+'/'+part['path'],identity=part['identity']))
            host=known_files.get(old['path']);require(not host or host['original_sha256']==old['sha256'] and host['bytes']==cursor,'Independent whole-file host output differs')
            files.append(dict(index=index,name=old['path'],original_bytes=old['bytes'],output_bytes=cursor,packed_bytes=packed_cursor,regions=regions,original_sha256=old['sha256'],
                known_output_sha256=host['sha256']if host else '',header_offset=header_offset,header_bytes=len(header),
                first_tensor=start,tensor_count=len(tensors)-start,first_part=first_part,part_count=len(parts)-first_part))
    require(len(files)==74 and sum(t['quantize']for t in tensors)==147,'Complete 74-file / 147-Expert-tensor copy plan required')
    pack_record=record(pack);total=sum(f['output_bytes']for f in files)
    part_root=original_root+('/'+sealed['part_directory']if sealed['part_directory']else'')
    def arr(values):return '{'+','.join(str(x)+'ULL'for x in values)+'}'
    h='#pragma once\n#include <array>\n#include <cstdint>\n#define Q2_LOCAL_NONCE '+json.dumps(nonce)+'\n'
    remote_header_pack='/data/ai/moss-qwen-q2-headers-'+nonce+'.bin'
    for name,value in (('q2_original_root',original_root),('q2_original_parts_root',part_root),('q2_destination_parent',a.destination_parent),
                       ('q2_destination',destination),('q2_header_pack',remote_header_pack),('q2_header_pack_sha256',pack_record['sha256'])):
        h+='inline constexpr const char*'+name+'='+json.dumps(value)+';\n'
    physical_bound=sum(t['output_bytes']for t in tensors if t['bits']==2)+(128<<20)
    h+='inline constexpr std::uint64_t q2_maximum_physical_new_bytes='+str(physical_bound)+'ULL;\n'
    h+='inline constexpr std::uint64_t q2_total_new_bytes='+str(total)+'ULL,q2_header_pack_bytes='+str(pack_record['bytes'])+'ULL;\n'
    for name,key in (('q2_original_root_identity',sealed['directory_identity']),('q2_original_parts_identity',sealed['part_directory_identity'])):
        h+='inline constexpr std::array<std::uint64_t,10>'+name+'='+arr(key)+';\n'
    h+='struct OriginalPart{const char*path;std::array<std::uint64_t,10>identity;};\ninline constexpr OriginalPart q2_original_parts[]={\n'
    h+=''.join('{'+json.dumps(p['path'])+','+arr(p['identity'])+'},\n'for p in parts)+'};\n'
    h+='struct Q2LocalTensor{std::uint64_t source_offset,source_bytes,output_offset,output_bytes;unsigned bits;};\ninline constexpr Q2LocalTensor q2_local_tensors[]={\n'
    h+=''.join('{'+','.join(str(t[k])+'ULL'for k in('source_offset','source_bytes','output_offset','output_bytes'))+','+str(t['bits'])+'},\n'for t in tensors)+'};\n'
    h+='struct Q2LocalFile{unsigned index;const char*name;std::uint64_t original_bytes,output_bytes,packed_bytes;const char*original_sha256,*known_output_sha256;std::uint64_t header_offset,header_bytes;unsigned first_tensor,tensor_count,first_part,part_count;};\ninline constexpr Q2LocalFile q2_local_files[]={\n'
    for f in files:
        h+='{'+str(f['index'])+','+json.dumps(f['name'])+','+str(f['original_bytes'])+'ULL,'+str(f['output_bytes'])+'ULL,'+str(f['packed_bytes'])+'ULL,'+json.dumps(f['original_sha256'])+','+json.dumps(f['known_output_sha256'])+','
        h+=str(f['header_offset'])+'ULL,'+str(f['header_bytes'])+'ULL,'+','.join(str(f[k])for k in('first_tensor','tensor_count','first_part','part_count'))+'},\n'
    h+='};\n';header=a.out/'expert_q2_local_plan.h';header.write_text(h,newline='\n')
    for name in('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((parent_path.parent/name).read_bytes())
    guard=a.out/'CPU-only-headroom.private.c'
    guard.write_text(guard.read_text().replace('    (void)report("HEADROOM admitted=%u','    if(!ok)(void)report("HEADROOM admitted=%u'),newline='\n')
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(prefix+'.log')+'\n',newline='\n')
    old=parent_path.parent;c=parent['commands'][0].copy();cpp=parent['commands'][1].copy();link=parent['commands'][-1].copy()
    original_hash=a.cache/'build/expert-q4-encode-native-7602/actual-SHA256.o';original_encoder=old/'encoder.o';q4_encoder=a.cache/'build/expert-q4-encode-native-7547/encoder.o'
    for command in (c,cpp,link):
        for i,value in enumerate(command):command[i]=value.replace(str(old),str(a.out))
    cpp[cpp.index('-c')+1]=str(ROOT/'native/qwen_flash_next/expert_q2_local_convert.cpp')
    for i,value in enumerate(link):
        if value==str(a.out/'actual-SHA256.o'):link[i]=str(original_hash)
        if value==str(a.out/'encoder.o'):link[i]=str(original_encoder)
    link.insert(link.index('--start-group'),str(q4_encoder))
    cpp+=['-DQ2_LOCAL_ACCELERATED_HASH=1']
    inputs=[record(q4_encoder)]+[record(x)for x in(Path(__file__),ROOT/'native/qwen_flash_next/expert_q2_local_convert.cpp',ROOT/'native/qwen_flash_next/source_split_guard.c',
        ROOT/'tools/expert_q2k_quantize.c',ROOT/'tools/expert_q4_quantize.c',retained_path,retained_seal,header,original_hash,original_encoder,a.inventory,a.policy,a.encoder_probe,a.host_partial,
        a.out/'CPU-only-headroom.private.c',a.out/'qualified_context_guard.c',a.out/'close_context.h',a.out/'source_split_context.h')]
    for i,command in enumerate((c,cpp,link)):
        r=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-5000:])
    artifact=a.out/'source-contention.elf';nm=Path(cpp[0]).parent/'llvm-nm.exe'
    symbols=subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True)
    names={line.split()[0]for line in symbols.splitlines()if line.split()};exports=parent['runtime_imports'].copy()
    # The only new filesystem mutations are the isolated copy's own creation,
    # part truncation/publication and permission finalization. No source writes.
    require(not any(any(word in n for word in('sceAgc','KillApp','ptrace','kernel_set_','kernel_copy','unlink','setuid'))for n in names),
        'CPU-only local conversion import boundary failed')
    runtime=json.loads((a.cache/'build/model-identity-snapshot-147/manifest.private.json').read_text())
    for row in runtime['sources']:
        path=Path(row['path'])
        if path.suffix!='.so' or path.name.endswith('_stub_weak.so'):continue
        require(record(path)==row,'Qualified native runtime export source changed')
        for line in subprocess.check_output([str(nm),'-D','--defined-only','--format=posix',str(path)],text=True).splitlines():
            if line.split():exports.setdefault(line.split()[0],path.name)
    require(names<=exports.keys(),'Local CPU converter has unresolved real runtime imports')
    manifest=dict(schema='ps5-qwen-expert-q2-local-conversion-build-v1',completed_build=True,nonce=nonce,
        artifact=record(artifact),inputs=inputs,commands=[c,cpp,link],headers=pack_record,
        remote_elf=prefix+'.elf',remote_log=prefix+'.log',remote_header_pack=remote_header_pack,
        original_receipt=inventory['original_receipt'],inventory=record(a.inventory),original_integrity=integrity,
        independent_host_partial=record(a.host_partial),files=files,tensors=tensors,original_parts=parts,
        new_directory=destination,total_new_bytes=total,total_physical_bytes=sum(f['packed_bytes']for f in files),independently_host_bound_new_files=0,Gate_Up_bits=2,Down_bits=4,packed_composite_sources=True,maximum_physical_new_bytes=physical_bound,aliased_tensors=aliases,retained_Q4_conversion=record(retained_path),retained_Q4_source_seal=record(retained_seal),
        imports={n:exports[n]for n in sorted(names)},CPU_only=True,CPU_workers=4,owned_Direct_bytes=32<<20,Gate_Up_format="Q2_K",Down_format="Q4_0",GPU_calls=0,title_launches=0,source_writes=0,
        native_process_limit_seconds=7200,maximum_executions=1,automatic_retries=0,console_operations=0)
    write_json(a.out/'manifest.private.json',manifest)
    print(json.dumps(dict(PS5_local_Q2_converter_built=True,files=74,Expert_tensors=147,new_bytes=total,headers_bytes=pack_record['bytes'],console_operations=0)),flush=True)

if __name__=='__main__':main()

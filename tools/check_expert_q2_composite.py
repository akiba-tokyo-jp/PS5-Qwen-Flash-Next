#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check complete composite metadata and malformed plans without console work."""
import argparse,copy,hashlib,json,os,subprocess
from pathlib import Path
from expert_q4 import EXPERT,LOCK,record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','cache','plan','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    old_path=a.cache/'Expert-Q4-receipt-7629.json';proof_path=a.cache/'build/Expert-Q4-relocation-7670/source-integrity.private.json'
    layout_path=a.cache/'expert-q4-local-conversion-7605/model-receipt.private.json'
    old=json.loads(old_path.read_text());previous=json.loads(proof_path.read_text());plan=json.loads(a.plan.read_text())
    model=copy.deepcopy(old);model.update(schema='ps5-qwen-expert-q2-model-v1',Expert_format='Gate_Up_Q2_K_Down_Q4_0',
        packed_composite_sources=True,retained_Q4_source_seal=record(proof_path),retained_Q4_conversion=record(layout_path))
    actual={t['name']:t for t in plan['tensors']};files={f['name']:f for f in plan['files']}
    root='/app0/expert-q2-'+plan['nonce'];dev=previous['directory_identity'][0];inode=1000000
    def key(size,mode=0o100644):
        nonlocal inode
        inode+=1;return [dev,inode,mode,0,0,size,1793240000,0,1793240000,0]
    sealed_files=[]
    for f in model['files']:
        if f['reused_original']:
            sealed_files.append(copy.deepcopy(next(x for x in previous['logical_files']if x['path']==f['path'])));continue
        selected=files[f['path']];f.update(bytes=selected['output_bytes'],packed_bytes=selected['packed_bytes'],
            header_bytes=selected['header_bytes'],regions=selected['regions'],sha256=hashlib.sha256(('metadata-only:'+f['path']).encode()).hexdigest())
        parts=[]
        for offset in range(0,f['packed_bytes'],512<<20):
            index=offset//(512<<20);count=min(512<<20,f['packed_bytes']-offset)
            parts.append(dict(path=f['path']+('.part-'+str(index)if index else''),offset=offset,bytes=count,
                sha256=hashlib.sha256((f['path']+str(index)).encode()).hexdigest(),identity=key(count)))
        f['parts']=copy.deepcopy(parts);s=copy.deepcopy(f);s.pop('regions');
        for part in s['parts']:part['path']=root+'/'+part['path']
        sealed_files.append(s)
    for t in model['tensors']:
        if t['name']not in actual:continue
        row=actual[t['name']];t['offset']=row['output_offset']
        if row['bits']==2:t.update(type='Q2_K',bytes=row['output_bytes'],payload_sha256=hashlib.sha256(('Q2-control:'+t['name']).encode()).hexdigest())
    model['mapped_file_bytes']=sum(f['bytes']for f in model['files'])
    model_path=a.out/'metadata-control-not-for-deployment.private.json';write_json(model_path,model);bound=record(model_path)
    sealed=dict(schema='ps5-qwen-expert-q2-packed-source-integrity-v1',model_receipt_sha256=bound['sha256'],
        source_directory=root,canonical_source_directory='/data/ai/native-moss-image-sft/PPSA99190'+root[5:],
        same_existing_title_nullfs_namespace=True,CPU_owners_positively_closed=True,
        all_new_parts_complete_Direct_SHA256_readback=True,all_parts_unchanged_since_readback=True,
        original_BF16_directories_and_parts_unchanged=True,source_writes=0,GPU_calls=0,model_loaded=False,automatic_retries=0,
        permission_changes=0,mount_changes=0,logical_bytes=model['mapped_file_bytes'],verification_elapsed_ms=1,
        directory_identity=key(65536,0o40755),receipt_identity=key(bound['bytes']),logical_files=sealed_files,
        backing_metadata=[dict(identity=key(record(path)['bytes']))for path in(proof_path,layout_path)])
    raw=json.dumps(sealed,indent=2)+'\n';gate=dict(model_receipt_sha256=bound['sha256'],model_receipt_bytes=bound['bytes'],
        Expert_Q2_source_integrity=dict(schema='ps5-qwen-expert-q2-source-policy-v1',raw=raw,sha256=hashlib.sha256(raw.encode()).hexdigest()))
    gate_path=a.out/'metadata-control-gate.private.json';write_json(gate_path,gate)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';upstream=a.cache/'upstream'/('llama.cpp-'+LOCK['llama_cpp']['revision'])
    sha=a.out/'SHA256.o';exe=a.out/'Q2-composite.exe'
    commands=[[host/'clang.exe','-std=c11','-O2','-I',upstream/'vendor','-I',upstream/'vendor/hash','-c',upstream/'vendor/hash/sha256/sha256.c','-o',sha],
        [host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app','-I',upstream/'vendor',
            ROOT/'tests/expert_q2_composite.cpp',ROOT/'native/app/model_integrity.cpp',sha,'-o',exe],
        [exe,model_path,gate_path,old_path,proof_path,layout_path]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,command in enumerate(commands):
        result=subprocess.run(list(map(str,command)),capture_output=True,timeout=120,env=env)
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-5000:])
    write_json(a.out/'receipt.private.json',dict(completed=True,metadata_only=True,not_for_deployment=True,PS5_operations=0,
        native_result=json.loads(result.stdout),model=record(model_path),gate=record(gate_path),plan=record(a.plan),
        inputs=[record(p)for p in(Path(__file__),ROOT/'tests/expert_q2_composite.cpp',ROOT/'native/app/expert_q2_composite_source.h')]))
    print(result.stdout.decode(),end='')
if __name__=='__main__':main()

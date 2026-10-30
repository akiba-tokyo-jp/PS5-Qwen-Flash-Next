#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded CPU-only publisher for new Q8 parts, receipt and prefixes."""
import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
from pathlib import Path
from expert_q4 import record, require, write_json
from build_speculative_batch_probe import once

ROOT=Path(__file__).resolve().parents[1]
TITLE='/data/ai/native-moss-image-sft/PPSA99190'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','audit','base-build','parent-publication','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prep=json.loads(a.preparation.read_text());audit=json.loads(a.audit.read_text());base=json.loads(a.base_build.read_text())
    require(prep['completed'] and prep['selected_tensors']==544 and audit['completed'] and audit['resident_BF16_tensors_remaining']==1,'Complete resident-Q8 conversion and independent audit with the BF16 PLE convolution required')
    require(audit['preparation']==record(a.preparation),'Audit refers to another preparation')
    for row in [prep['parent'],prep['candidate'],base['artifact']]:require(record(row['path'])==row,'Publication input changed')
    historical_generator=ROOT/'tools/build_resident_shared_q8_publication.py';historical=[]
    for row in base['inputs']:
        if Path(row['path']).resolve()==historical_generator.resolve():
            # This old Python generator is not executed or compiled here.
            # Retain its recorded provenance; require exact current bytes for
            # every actual source/header/ABI input reused from that CPU build.
            historical.append(dict(recorded=row,current=record(historical_generator),reexecuted=False))
        else:require(record(row['path'])==row,'Actual parent CPU source/ABI input changed: '+row['path'])
    require(base['CPU_only'] and base['owned_Direct_bytes']==8<<20,'Qualified bounded CPU publication ABI required')
    parent_pub=json.loads(a.parent_publication.read_text());parent_seal=json.loads(Path(parent_pub['source_integrity']['path']).read_text())
    require(parent_pub['completed'] and parent_pub['candidate']==prep['parent'] and record(parent_pub['source_integrity']['path'])==parent_pub['source_integrity'],'Exact installed parent publication required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);root=TITLE+'/expert-q2-'+nonce;remote='/data/ai/moss-qwen-resident-Q8-publish-'+nonce
    receipt=json.loads(Path(prep['candidate']['path']).read_text());headers=receipt['resident_all_Q8_overlay']['headers'];local_headers=[]
    for h in headers:
        source=Path(prep['parts'][h['part']]['path'])
        with source.open('rb') as f:f.seek(h['pack_offset']);raw=f.read(h['bytes'])
        require(hashlib.sha256(raw).hexdigest()==h['sha256'],'Serialized header differs')
        path=a.out/h['file'];path.write_bytes(raw);local_headers.append(record(path))
    local=[*prep['parts'],prep['candidate'],*local_headers];files=[]
    for i,row in enumerate(local):
        name=Path(row['path']).name
        require(re.fullmatch(r'(resident-all-Q8\.part[0-9]+\.bin|model-receipt\.json|qwen-flash-next-bf16-\d{5}-of-00076\.gguf)',name),'Only explicit new Q8 assets may be published')
        # Reuse the qualified transport's two-slot namespace without widening
        # its path policy: each independent new file owns a fresh nonce/slot0.
        files.append(dict(local=row,source='/data/ai/moss-qwen-layout-'+secrets.token_hex(16)+'-512-0.bin',destination=root+'/'+name))
    require(0<len(files)<=128 and all(0<f['local']['bytes']<=512<<20 for f in files),'Bounded publication file set required')
    h=a.out/'resident_output_Q8_publish_plan.h'
    previous=[dict(path=parent_seal['pack']['path'],identity=parent_seal['pack']['identity']),dict(path=parent_seal['source_directory']+'/model-receipt.json',identity=parent_seal['receipt_identity']),*parent_seal['headers']]
    prior_rows=[]
    for row in previous:
        require(row['path'].startswith('/app0/') and len(row['identity'])==10,'Exact parent identity required')
        prior_rows.append('{'+json.dumps(TITLE+'/'+row['path'][6:])+',{'+','.join(str(v)+'ULL' for v in row['identity'])+'}}')
    h.write_text('#pragma once\n#include <cstdint>\n#include <array>\n#define OUTPUT_Q8_PUBLISH_NONCE '+json.dumps(nonce)+'\ninline constexpr const char*output_Q8_directory='+json.dumps(root)+';\nstruct OutputQ8PublicationFile{const char*source;const char*destination;std::uint64_t bytes;const char*sha256;};\ninline constexpr OutputQ8PublicationFile output_Q8_files[]={'+','.join('{'+json.dumps(f['source'])+','+json.dumps(f['destination'])+','+str(f['local']['bytes'])+'ULL,'+json.dumps(f['local']['sha256'])+'}' for f in files)+'};\nstruct PreviousQ8File{const char*path;std::array<std::uint64_t,10>identity;};\ninline constexpr PreviousQ8File previous_Q8_files[]={'+','.join(prior_rows)+'};\n',newline='\n')
    source=(ROOT/'native/qwen_flash_next/resident_output_q8_publish.cpp').read_text()
    source=once(source,'for(unsigned i=0;i<3;++i)',f'for(unsigned i=0;i<{len(files)};++i)')
    source=once(source,'if(i<2)sha256_update(&whole,static_cast<unsigned char*>(window),n);','')
    source=once(source,'    struct statfs capacity{};','    for(const auto&p:previous_Q8_files)need(named(p.path)==p.identity,"Installed parent identity changed before publication");\n    struct statfs capacity{};')
    source=once(source,'    need(digest(whole)==output_Q8_GGUF_SHA256,"Q8 complete concatenated GGUF SHA256 differs");\n    line("WHOLE_Q8_GGUF SHA256="+std::string(output_Q8_GGUF_SHA256)+" bytes=675430560");',
        '    for(const auto&p:previous_Q8_files)need(named(p.path)==p.identity,"Installed parent identity changed during publication");\n    line("RESIDENT_Q8_COMPLETE immutable_files='+str(len(files))+' whole_file_SHA256_and_EOF=1 original_sources_unchanged=1 parent_identities_verified=1");')
    actual=a.out/'publication.private.cpp';actual.write_text(source,newline='\n')
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((a.base_build.parent/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[v.replace(str(a.base_build.parent),str(a.out)) for v in c] for c in base['commands']]
    commands[1][commands[1].index('-c')+1]=str(actual)
    for i,c in enumerate(commands):
        result=subprocess.run(c,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe'
    names={r.split()[0] for r in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines() if r.split()}
    require(names<=base['runtime_imports'].keys(),'New unaudited CPU import')
    require(not any(re.search('(unlink|sceAgc|KillApp|LaunchApp|ptrace|kernel_set_)',n) for n in names),'Publisher may not delete originals, launch titles or use GPU')
    write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,nonce=nonce,files=files,
        new_directory=root,app0_directory='/app0/'+root.rsplit('/',1)[1],candidate_receipt=prep['candidate'],parent_receipt=prep['parent'],part_count=len(prep['parts']),header_count=len(headers),
        remote_elf=remote+'.elf',remote_log=remote+'.log',owned_Direct_bytes=8<<20,maximum_executions=1,automatic_retries=0,original_source_writes=0,GPU_calls=0,title_launches=0,
        runtime_imports={n:base['runtime_imports'][n] for n in sorted(names)},
        parent_publication=record(a.parent_publication),parent_identity_files=len(previous),historical_generator_provenance=historical,
        payloads_verified_by_independent_audit_and_again_during_transport=True,
        inputs=[record(x) for x in (Path(__file__),a.preparation,a.audit,a.base_build,a.parent_publication,Path(parent_pub['source_integrity']['path']),h,actual,*[a.out/n for n in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h','source_split_context.h')])]))
    print('New-only resident-Q8 publication built; no console operations.')


if __name__=='__main__':main()
